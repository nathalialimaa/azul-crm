import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from azul_crm.api.main import create_app
from azul_crm.bootstrap import build_container
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.bias_audit import (
    ATTRIBUTES,
    FOUR_FIFTHS,
    build_records,
    load_report,
    region_of,
    run_audit,
    select_top,
    write_report,
)
from azul_crm.pipeline.extended import generate
from azul_crm.pipeline.personas import train_personas


def rec(i, persona, priority, airport="REC", channel="app", tier="T1", risk=0.5, churn=False):
    return {
        "customer_id": f"C{i:04d}",
        "persona": persona,
        "priority_score": priority,
        "churn_risk": risk,
        "churn_observed": churn,
        "home_airport": airport,
        "region": region_of(airport),
        "preferred_channel": channel,
        "tier": tier,
    }


def population(channel_penalty=0.0):
    """100 'Alto' (50 app / 50 email) e 100 'Baixo'. Penalidade reduz a prioridade do email."""
    rows = []
    for i in range(100):
        channel = "app" if i % 2 == 0 else "email"
        score = 90 - i * 0.1 - (channel_penalty if channel == "email" else 0)
        rows.append(rec(i, "Alto", score, channel=channel))
    for i in range(100, 200):
        rows.append(rec(i, "Baixo", 10 - (i - 100) * 0.01, channel="app" if i % 2 else "email"))
    return rows


def test_select_top_is_exact_and_deterministic():
    rows = [rec(i, "P", 50) for i in range(103)]  # empate total
    chosen = select_top(rows, 0.2)
    assert len(chosen) == 21  # ceil(0,2 * 103)
    assert chosen == select_top(list(reversed(rows)), 0.2)
    assert chosen == {f"C{i:04d}" for i in range(21)}  # desempate estável por id


def test_equal_treatment_is_ok():
    report = run_audit(population())
    channel = report["attributes"]["preferred_channel"]
    assert channel["verdict"] == "ok"
    assert channel["selection_ratio"] >= FOUR_FIFTHS
    assert report["synthetic_only"] is True
    assert set(report["attributes"]) == set(ATTRIBUTES)


def test_unequal_treatment_inside_same_persona_is_an_alert():
    report = run_audit(population(channel_penalty=30))
    channel = report["attributes"]["preferred_channel"]
    assert channel["verdict"] == "alerta"
    alto = next(w for w in channel["within_persona"] if w["persona"] == "Alto")
    assert alto["flag"] and alto["selection_ratio"] < FOUR_FIFTHS
    assert report["summary"]["alerts"] >= 1


def test_attribute_that_determines_persona_is_confounded_not_excused():
    rows = [rec(i, "Alto", 90 - i * 0.1, airport="VCP") for i in range(100)]
    rows += [rec(i, "Baixo", 10 - i * 0.01, airport="CNF") for i in range(100, 200)]
    airport = run_audit(rows)["attributes"]["home_airport"]
    assert airport["selection_flag"] is True
    assert airport["within_persona"] == []  # nenhum grupo divide persona
    assert airport["verdict"] == "confundido"
    assert airport["persona_association"]["relevant"] is True


def test_small_groups_are_skipped_not_compared():
    rows = population()
    for r in rows[:5]:
        r["tier"] = "RARO"
    tier = run_audit(rows)["attributes"]["tier"]
    assert [g["group"] for g in tier["groups"]] == ["T1"]
    assert tier["skipped_small_groups"] == [{"group": "RARO", "customers": 5}]
    assert tier["verdict"] == "amostra_insuficiente"


def test_calibration_and_recall_are_reported_per_group():
    rows = population()
    for r in rows:
        if r["preferred_channel"] == "email":
            r["churn_risk"], r["churn_observed"] = 0.9, False  # superestima o risco
        else:
            r["churn_risk"], r["churn_observed"] = 0.4, True
    channel = run_audit(rows)["attributes"]["preferred_channel"]
    gaps = {g["group"]: g["calibration_gap"] for g in channel["groups"]}
    assert gaps["email"] == pytest.approx(0.9) and gaps["app"] == pytest.approx(-0.6)
    assert channel["calibration_flag"] is True
    assert any(g["recall_among_churners"] is not None for g in channel["groups"])


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError):
        run_audit([])
    broken = population()
    broken[0].pop("region")
    with pytest.raises(ValueError, match="region"):
        run_audit(broken)


def test_region_mapping():
    assert region_of("REC") == "Nordeste"
    assert region_of("GRU") == "Sudeste"
    assert region_of("POA") == "Sul"
    assert region_of("BSB") == "Centro-Oeste"
    assert region_of("XXX") == "Outra"


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


def test_end_to_end_report_and_staleness(base):
    root, store = base
    assert load_report(root, store) == {"available": False}
    report = write_report(root, build_container(Settings(root)), store)
    assert report["segmenter"] == "kmeans_personas_v1"
    assert report["settings"]["customers"] == 300
    assert report["settings"]["selected_customers"] == 60
    loaded = load_report(root, store)
    assert loaded["available"] and loaded["stale"] is False
    stored = json.loads((root / "artifacts/bias_report.json").read_text(encoding="utf-8"))
    stored["gold_fingerprint"] = "0" * 64
    (root / "artifacts/bias_report.json").write_text(json.dumps(stored), encoding="utf-8")
    assert load_report(root, store)["stale"] is True


def test_regenerating_gold_discards_report(base):
    root, store = base
    write_report(root, build_container(Settings(root)), store)
    assert (root / "artifacts/bias_report.json").exists()
    generate(Settings(root), 300, 7)
    assert not (root / "artifacts/bias_report.json").exists()


def test_missing_outcomes_fail_clearly(base):
    root, store = base
    store.publish({"outcomes": []})
    with pytest.raises(ValueError, match="Desfechos ausentes"):
        build_records(build_container(Settings(root)), store)


def test_bias_endpoint(base):
    root, store = base
    with TestClient(create_app(build_container(Settings(root)))) as api:
        assert api.get("/api/v1/bias").json() == {"available": False}
        write_report(root, build_container(Settings(root)), store)
        body = api.get("/api/v1/bias").json()
        assert body["available"] and body["stale"] is False
        assert set(body["attributes"]) == set(ATTRIBUTES)


def test_small_samples_per_persona_are_not_called_confounded():
    # Dois aeroportos com a MESMA mistura de personas, mas só 10 clientes de cada persona por
    # aeroporto (abaixo do mínimo de 20): não há como comparar dentro da persona.
    rows, i = [], 0
    for persona in ["P1", "P2", "P3", "P4"]:
        for airport in ["AAA", "BBB"]:
            for _ in range(10):
                score = 90 - i * 0.01 if airport == "AAA" else 10 - i * 0.01  # AAA é favorecido
                rows.append(rec(i, persona, score, airport=airport))
                i += 1
    airport = run_audit(rows)["attributes"]["home_airport"]
    assert airport["selection_flag"] is True and airport["within_persona"] == []
    assert airport["persona_association"]["relevant"] is False  # a mistura é igual nos dois
    assert airport["verdict"] == "amostra_insuficiente"


def _random_attribute_run(seed, penalty=0.0):
    """Estrutura de personas realista; o canal é sorteado, só a penalidade cria viés."""
    import random

    rng = random.Random(seed)
    rows, i = [], 0
    for persona, n, mean, spread in [
        ("Baixo Volume", 173, 20, 6),
        ("Esfriando", 103, 60, 14),
        ("Atrasos", 26, 18, 6),
        ("Fiéis", 98, 70, 13),
    ]:
        for _ in range(n):
            channel = rng.choice(["app", "email"])
            score = rng.gauss(mean, spread) - (penalty if channel == "email" else 0)
            rows.append(
                rec(i, persona, score, channel=channel, tier=rng.choice(["T1", "T2", "T3"]))
            )
            i += 1
    return run_audit(rows)["attributes"]


def test_random_attributes_rarely_raise_alerts():
    trials = [_random_attribute_run(seed) for seed in range(150)]
    for attribute in ("preferred_channel", "tier"):
        false_alarms = sum(t[attribute]["verdict"] == "alerta" for t in trials)
        assert false_alarms / len(trials) <= 0.12, (attribute, false_alarms)  # nível nominal: 5%


def test_real_bias_is_still_detected():
    hits = sum(
        _random_attribute_run(seed, penalty=15)["preferred_channel"]["verdict"] == "alerta"
        for seed in range(30)
    )
    assert hits >= 28


def test_low_ratio_that_could_be_chance_is_inconclusive_not_an_alert():
    # Persona P: 25 app + 25 email; 14 de app e 20 de email entram no top 20% (razão 0,7).
    # Base de 170 clientes: 20% = 34 selecionados, todos de P.
    rows = []
    for i in range(50):
        channel = "app" if i < 25 else "email"
        picked = (i < 14) if channel == "app" else (i - 25 < 20)
        rows.append(rec(i, "P", 90 - i * 0.01 if picked else 10, channel=channel))
    rows += [
        rec(i, "Q", 5 - i * 0.001, channel="app" if i % 2 else "email") for i in range(50, 170)
    ]
    within = run_audit(rows)["attributes"]["preferred_channel"]["within_persona"]
    entry = next(w for w in within if w["persona"] == "P")
    assert entry["selection_ratio"] == pytest.approx(0.7) and entry["selected"] == 34
    assert entry["p_value"] > 0.01 and entry["flag"] is False and entry["inconclusive"] is True


def test_too_few_selected_in_a_persona_are_not_compared():
    # Base de 400 (80 selecionados): só 6 deles são da persona P, que tem 60 clientes.
    rows = [
        rec(i, "P", 99 if i < 6 else 10, channel="app" if i % 2 else "email") for i in range(60)
    ]
    rows += [
        rec(i, "Q", 60 if i < 134 else 5, channel="app" if i % 2 else "email")
        for i in range(60, 400)
    ]
    attribute = run_audit(rows)["attributes"]["preferred_channel"]
    entry = next(w for w in attribute["within_persona"] if w["persona"] == "P")
    assert entry["selected"] == 6 and entry["selection_ratio"] is None and entry["p_value"] is None
