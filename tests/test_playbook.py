import copy
import json
import shutil
import tomllib
from itertools import product
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from azul_crm.api.main import create_app
from azul_crm.application.recommendations import RecommendationService
from azul_crm.bootstrap import build_container
from azul_crm.domain.decisions import EligibilityPolicy
from azul_crm.domain.playbook import STATUS_HYPOTHESIS, TRAIT_NAMES, Playbook, Traits
from azul_crm.domain.scoring import RuleSegmenter, ScoringPolicy
from azul_crm.infrastructure.playbook import PlaybookMessageGenerator, load_playbook
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.extended import generate
from azul_crm.pipeline.personas import train_personas

CONFIG = Path(__file__).resolve().parents[1] / "config" / "playbook.toml"
FORBIDDEN = [
    "bônus",
    "bonus",
    "upgrade",
    "desconto",
    "pontos",
    "milhas",
    "cortesia",
    "gratuit",
    "compensa",
    "oferta",
]


def raw():
    with CONFIG.open("rb") as file:
        return tomllib.load(file)


def test_repo_playbook_covers_every_combination_and_offers_are_hypotheses():
    playbook = load_playbook(CONFIG)
    for values in product([False, True], repeat=len(TRAIT_NAMES)):
        action, offer = playbook.decide(Traits(*values))
        assert action.code in playbook.actions
        assert offer is None or offer.status == STATUS_HYPOTHESIS
    assert all(o.status == STATUS_HYPOTHESIS for o in playbook.offers.values())


def test_first_matching_rule_wins():
    playbook = load_playbook(CONFIG)
    action, _ = playbook.decide(Traits(high_value=True, cooling=True, delays=True))
    assert action.code == "SERVICE_RECOVERY"
    action, _ = playbook.decide(Traits(high_value=True, cooling=True, delays=False))
    assert action.code == "WIN_BACK_PERSONAL"


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda d: d.update(rule=d["rule"][:1]), "não cobre"),
        (lambda d: d["rule"][0].update(action="NOPE"), "ação desconhecida"),
        (lambda d: d["rule"][0].update(offer="NOPE"), "oferta desconhecida"),
        (lambda d: d["rule"][0].update(when={"weather": True}), "condição desconhecida"),
        (lambda d: d["action"][0].update(assumed_retention=1.5), "Premissas inválidas"),
        (lambda d: d["action"][0].update(assumed_cost=-1), "Premissas inválidas"),
        (lambda d: d["action"][0].update(fallback=""), "sem texto"),
        (lambda d: d["offer"][0].update(status="verified"), "fonte oficial"),
        (lambda d: d["offer"][0].update(status="approved"), "Status inválido"),
        (lambda d: d["action"].append(copy.deepcopy(d["action"][0])), "duplicados"),
        (lambda d: d.pop("offer"), "malformado"),
    ],
)
def test_invalid_playbooks_are_rejected(mutate, message):
    data = copy.deepcopy(raw())
    mutate(data)
    with pytest.raises(ValueError, match=message):
        Playbook.from_dict(data)


def test_offer_can_be_verified_only_with_official_source():
    data = copy.deepcopy(raw())
    data["offer"][0].update(status="verified", source="https://exemplo.invalido/regulamento")
    assert Playbook.from_dict(data).offers[data["offer"][0]["code"]].status == "verified"


def test_rule_segmenter_exposes_traits():
    segmenter = RuleSegmenter(ScoringPolicy())
    assert segmenter.traits("Premium Leal") == Traits(True, False, False)
    assert segmenter.traits("Alto Valor em Risco") == Traits(True, True, False)
    assert segmenter.traits("não existe") is None


@pytest.fixture
def base(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1]
    for name in ["config", "data/fixtures", "data/knowledge"]:
        shutil.copytree(source / name, tmp_path / name)
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    generate(Settings(tmp_path), 300, 42)
    store = Store(tmp_path)
    train_personas(tmp_path, store, seed=42, k=4)
    return tmp_path, store


def all_recommendations(container):
    return [container.recommendations.recommend(s.customer_id) for s in container.crm.priorities()]


def test_each_persona_gets_its_own_action_and_evidence(base):
    root, _ = base
    container = build_container(Settings(root))
    assert container.metadata["playbook"] == "playbook_v1"
    recs = all_recommendations(container)
    by_persona = {}
    for r in recs:
        by_persona.setdefault(r.persona, set()).add(r.action.code)
        assert r.mode == "playbook_template" and r.status == "DRAFT_REQUIRES_REVIEW"
        assert r.channel in {"app", "email"}
        ids = [e.document_id for e in r.evidence]
        assert "playbook-" + r.action.code in ids and len(ids) == len(set(ids))
        assert r.offer is not None and r.offer.status == STATUS_HYPOTHESIS
    assert all(len(codes) == 1 for codes in by_persona.values())  # ação depende só da persona
    assert len({next(iter(c)) for c in by_persona.values()}) >= 3


def test_drafts_never_promise_benefits(base):
    root, _ = base
    for r in all_recommendations(build_container(Settings(root))):
        text = r.draft.lower()
        assert not any(word in text for word in FORBIDDEN), (r.action.code, r.draft)
        assert r.offer.title.lower() not in text
        assert "nenhuma mensagem foi enviada" in text


def test_draft_uses_real_customer_facts(base):
    root, _ = base
    container = build_container(Settings(root))
    crm = container.crm
    checked = set()
    for score in crm.priorities():
        rec = container.recommendations.recommend(score.customer_id)
        trips = crm.trips(score.customer_id)
        features = crm.features.build(score.customer_id, trips, crm.start, crm.end)
        if rec.action.code == "WIN_BACK_PERSONAL":
            assert f"{features.recency_days} dias" in rec.draft
        elif rec.action.code == "SERVICE_RECOVERY":
            delayed = sum(t.delay_minutes >= 60 for t in trips)
            if delayed:
                assert f"{delayed} de {features.frequency} viagens" in rec.draft
        elif rec.action.code == "RECOGNITION":
            assert f"{features.frequency} vezes" in rec.draft
        checked.add(rec.action.code)
    assert {"WIN_BACK_PERSONAL", "SERVICE_RECOVERY", "RECOGNITION"} <= checked


def test_missing_facts_fall_back_to_generic_text():
    playbook = load_playbook(CONFIG)
    generator = PlaybookMessageGenerator(playbook)
    action = playbook.actions["SERVICE_RECOVERY"]
    from azul_crm.domain.models import Action

    plain = Action(action.code, action.title, action.reason)
    text = generator.draft(None, None, plain, (), {"delayed_trips": 0, "trips": 8})
    assert text.startswith(action.fallback) and " 0 de " not in text
    full = generator.draft(None, None, plain, (), {"delayed_trips": 3, "trips": 8})
    assert "3 de 8 viagens" in full


def test_no_governance_evidence_blocks_every_action(base):
    root, _ = base
    container = build_container(Settings(root))

    class NoEvidence:
        def retrieve(self, query):
            return ()

    service = RecommendationService(
        container.crm,
        NoEvidence(),
        EligibilityPolicy(),
        PlaybookMessageGenerator(container.recommendations.playbook),
        container.recommendations.playbook,
    )
    rec = service.recommend(container.crm.customers()[0].customer_id)
    assert rec.action.code == "NO_ACTION" and rec.offer is None
    assert "revisão humana" in rec.draft.lower()


def test_personas_without_traits_fall_back_to_legacy_actions(base):
    root, _ = base
    path = root / "artifacts/personas.json"
    artifact = json.loads(path.read_text(encoding="utf-8"))
    for persona in artifact["personas"]:
        persona.pop("traits")
    path.write_text(json.dumps(artifact), encoding="utf-8")
    container = build_container(Settings(root))
    rec = container.recommendations.recommend(container.crm.customers()[0].customer_id)
    assert rec.mode == "demo_template" and rec.offer is None
    assert rec.action.code in {"CONTACT_SUPPORT", "RELATIONSHIP"}


def test_api_recommendation_playbook_and_decision(base):
    root, store = base
    with TestClient(create_app(build_container(Settings(root)))) as api:
        cid = api.get("/api/v1/customers?limit=1").json()["items"][0]["customer_id"]
        rec = api.post("/api/v1/agent/recommend", json={"customer_id": cid}).json()
        assert rec["mode"] == "playbook_template" and rec["persona"] and rec["channel"]
        assert rec["offer"]["status"] == "hypothesis_unverified"

        plan = api.get("/api/v1/playbook").json()
        assert plan["available"] and plan["causal_claim"] is False and plan["rows"]
        for row in plan["rows"]:
            assert row["cost"] == pytest.approx(row["customers"] * row["assumed_cost_per_customer"])
            assert row["net"] == pytest.approx(row["protected_value"] - row["cost"])
        assert plan["totals"]["customers"] == sum(r["customers"] for r in plan["rows"])
        assert api.get("/api/v1/playbook?months=0").status_code == 422

        saved = api.post("/api/v1/decisions", json={"customer_id": cid, "status": "APPROVED"})
        assert saved.status_code == 200 and saved.json()["sent"] is False
        stored = store.read("decisions")[0]["recommendation"]
        assert stored["offer"]["status"] == "hypothesis_unverified"


def test_playbook_endpoint_is_unavailable_without_playbook(client):
    # `client` usa o container legado, sem personas e sem playbook.
    assert client.get("/api/v1/playbook").json() == {"available": False}
