from datetime import date

from azul_crm.application.features import FeatureBuilder
from azul_crm.domain.decisions import EligibilityPolicy
from azul_crm.domain.models import Trip
from azul_crm.pipeline.stages import DemoSyntheticGenerator


def test_api_flow_and_contract(client):
    assert client.get("/health").status_code == 200
    rows = client.get("/api/v1/retention/priorities").json()
    assert len(rows) == 12
    assert rows == sorted(rows, key=lambda s: (-s["priority_score"], s["customer_id"]))
    customer_id = rows[0]["customer_id"]
    detail = client.get(f"/api/v1/customers/{customer_id}").json()
    assert detail["customer"]["is_synthetic"]
    assert 0 <= detail["scores"]["churn_risk"] <= 1
    result = client.post("/api/v1/agent/recommend", json={"customer_id": customer_id}).json()
    assert result["status"] == "DRAFT_REQUIRES_REVIEW"
    assert result["mode"] == "demo_template"
    assert result["evidence"][0]["is_demo"]
    assert result["action"]["code"] in {"CONTACT_SUPPORT", "RELATIONSHIP"}


def test_missing_and_invalid_requests(client):
    assert client.get("/api/v1/customers/missing").status_code == 404
    assert (
        client.post("/api/v1/agent/recommend", json={"customer_id": "missing"}).status_code == 404
    )
    assert client.post("/api/v1/agent/recommend", json={"customer_id": ""}).status_code == 422
    assert client.get("/api/v1/customers?limit=-1").status_code == 422
    assert client.get("/api/v1/customers?limit=3&offset=2").json()["total"] == 12
    assert client.get("/api/v1/retention/priorities?segment=missing").json() == []


def test_temporal_leakage_is_blocked():
    observed = Trip("t1", "c1", "REC", "GRU", date(2026, 9, 1), 500, 0)
    future = Trip("t2", "c1", "REC", "GRU", date(2026, 10, 1), 99999, 180)
    builder = FeatureBuilder()
    start, end = date(2025, 10, 1), date(2026, 9, 30)
    assert builder.build("c1", [observed], start, end) == builder.build(
        "c1", [observed, future], start, end
    )


def test_reproducible_generator():
    args = (
        [{"origin": "REC", "destination": "GRU", "mean_fare": 950}],
        12,
        42,
        date(2025, 10, 1),
        date(2026, 9, 30),
    )
    assert DemoSyntheticGenerator().generate(*args) == DemoSyntheticGenerator().generate(*args)


def test_missing_evidence_blocks_action(client):
    scores = client.app.state.container.crm.scores("SYN-0001")
    assert EligibilityPolicy().select(scores, False).code == "NO_ACTION"
