"""Checklist de revisão: nenhum rascunho é aprovado sem o revisor confirmar o consentimento."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from azul_crm.api.main import create_app
from azul_crm.application.recommendations import RecommendationService
from azul_crm.bootstrap import build_container
from azul_crm.infrastructure.lake import BY_NAME, convert_rows
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.demo import prepare_demo

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def base(tmp_path, monkeypatch):
    for name in ["config", "data/fixtures", "data/knowledge", "frontend"]:
        shutil.copytree(REPO / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(REPO / "streamlit_app.py", tmp_path / "streamlit_app.py")
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    prepare_demo(Settings(tmp_path), customers=120)
    return tmp_path, Store(tmp_path)


def test_every_contact_recommendation_carries_the_consent_item(base):
    root, _ = base
    container = build_container(Settings(root))
    for customer in container.crm.customers()[:25]:
        rec = container.recommendations.recommend(customer.customer_id)
        codes = [item.code for item in rec.review_checklist]
        assert {"CONSENT", "HUMAN_REVIEW"} <= set(codes), customer.customer_id
        consent = next(i for i in rec.review_checklist if i.code == "CONSENT")
        assert "item 3.6" in consent.source and "revogada" in consent.text
        assert ("OFFER_NOT_IN_MESSAGE" in codes) is (rec.offer is not None)


def test_no_action_has_no_checklist(base):
    root, _ = base
    container = build_container(Settings(root))
    service = container.recommendations

    class NoEvidence:
        def retrieve(self, query):
            return ()

    silent = RecommendationService(
        service.crm, NoEvidence(), service.eligibility, service.generator, service.playbook
    )
    rec = silent.recommend(container.crm.customers()[0].customer_id)
    assert rec.action.code == "NO_ACTION" and rec.review_checklist == ()


def test_api_refuses_approval_without_the_confirmed_checklist(base):
    root, store = base
    with TestClient(create_app(build_container(Settings(root)))) as api:
        cid = api.get("/api/v1/customers?limit=1").json()["items"][0]["customer_id"]
        rec = api.post("/api/v1/agent/recommend", json={"customer_id": cid}).json()
        codes = [item["code"] for item in rec["review_checklist"]]
        assert "CONSENT" in codes and all(
            {"code", "text", "source"} <= set(i) for i in rec["review_checklist"]
        )

        approve = {"customer_id": cid, "status": "APPROVED"}
        refused = api.post("/api/v1/decisions", json=approve)
        assert refused.status_code == 409 and "CONSENT" in refused.json()["detail"]
        partial = api.post("/api/v1/decisions", json={**approve, "confirmed_checklist": codes[:-1]})
        assert partial.status_code == 409 and codes[-1] in partial.json()["detail"]
        assert store.read("decisions") == []  # nada foi gravado

        ok = api.post("/api/v1/decisions", json={**approve, "confirmed_checklist": codes})
        assert ok.status_code == 200 and ok.json()["confirmed_checklist"] == codes
        assert len(store.read("decisions")) == 1

        reject = api.post("/api/v1/decisions", json={"customer_id": cid, "status": "REJECTED"})
        assert reject.status_code == 200  # rejeitar não exige checklist


def test_decision_rows_without_the_new_field_still_export(base):
    old = {
        "id": "1",
        "customer_id": "C1",
        "status": "APPROVED",
        "note": "",
        "recommendation": {"a": 1},
        "created_at": "2026-01-01T10:00:00-03:00",
        "sent": False,
    }
    row = convert_rows(BY_NAME["gold.decisions"], [old])[0]
    assert row[-1] is None  # decisões antigas, sem o campo, continuam exportáveis


def test_screen_blocks_approval_until_every_item_is_checked(base):
    import streamlit as st

    root, store = base
    st.cache_resource.clear()
    at = AppTest.from_file(str(root / "streamlit_app.py"), default_timeout=180).run()
    at.sidebar.radio[0].set_value("Ações de CRM").run()
    assert not at.exception, [e.value for e in at.exception]

    def approve_button():
        return next(b for b in at.button if b.label == "Aprovar rascunho")

    assert len(at.checkbox) >= 2 and approve_button().disabled
    at.checkbox[0].check().run()
    assert approve_button().disabled  # ainda faltam itens
    for box in at.checkbox:
        box.check()
    at.run()
    assert not approve_button().disabled
    approve_button().click().run()
    saved = store.read("decisions")
    assert len(saved) == 1 and "CONSENT" in saved[0]["confirmed_checklist"]
    assert json.dumps(saved[0]["recommendation"]["review_checklist"])


def test_local_gateway_enforces_the_same_rule_as_the_api(base):
    import sys

    sys.path.insert(0, str(REPO))  # a pasta frontend não é um pacote instalado
    from frontend.gateway import Gateway

    root, store = base
    gateway = Gateway()
    cid = gateway.c.crm.customers()[0].customer_id
    codes = [item["code"] for item in gateway.recommend(cid)["review_checklist"]]

    with pytest.raises(ValueError, match="CONSENT"):
        gateway.decide(cid, "APPROVED", "")
    with pytest.raises(ValueError):
        gateway.decide(cid, "APPROVED", "", codes[:1])
    assert store.read("decisions") == []

    saved = gateway.decide(cid, "APPROVED", "ok", codes)
    assert saved["confirmed_checklist"] == codes and len(store.read("decisions")) == 1
    assert gateway.decide(cid, "REJECTED", "")["status"] == "REJECTED"
