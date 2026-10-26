# ruff: noqa: E402
"""Valida a projeção Vercel com rede LLM simulada: nenhuma credencial real."""

import concurrent.futures
import importlib
import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))
web = importlib.import_module("web.api.index")
from crm_runtime.storage import Storage


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("CRM_APP_PASSWORD", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.setenv("CRM_WEB_STATE", str(tmp_path / "state.db"))
    monkeypatch.setenv("GEMINI_MAX_ATTEMPTS", "1")
    with TestClient(web.app) as c:
        assert c.post("/api/session", json={}).status_code == 200
        yield c


def test_private_data_requires_session(client):
    client.cookies.clear()
    assert client.get("/api/bootstrap").status_code == 401
    assert client.get("/api/customers/SYN-0077").status_code == 401
    assert client.get("/api/decisions").status_code == 401


def test_hosted_fails_closed_without_password(client, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    assert client.get("/api/bootstrap").status_code == 503
    assert client.post("/api/session", json={}).status_code == 503


def test_password_login_and_secure_cookie(client, monkeypatch):
    monkeypatch.setenv("CRM_APP_PASSWORD", "unit-private-password")
    client.cookies.clear()
    assert client.post("/api/session", json={"password": "wrong"}).status_code == 401
    r = client.post("/api/session", json={"password": "unit-private-password"})
    assert r.status_code == 200
    assert "HttpOnly" in r.headers["set-cookie"]
    assert "SameSite=strict" in r.headers["set-cookie"]
    assert client.get("/api/bootstrap").status_code == 200
    client.delete("/api/session")
    assert client.get("/api/bootstrap").status_code == 401


def test_cross_origin_and_invalid_content_type_rejected(client):
    assert (
        client.post(
            "/api/drafts",
            json={"customer_id": "SYN-0077"},
            headers={"Origin": "https://other.example"},
        ).status_code
        == 403
    )
    assert client.post("/api/session", content="x").status_code == 415
    assert (
        client.post(
            "/api/session",
            content='"' + "a" * 2_097_153 + '"',
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )


def test_snapshot_invariants_and_zero_implicit_llm(client, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Nenhuma chamada deve acontecer ao navegar")

    monkeypatch.setattr(web.GeminiClient, "generate", forbidden)
    r = client.get("/api/bootstrap")
    assert r.status_code == 200
    d = r.json()["dashboard"]
    assert d["kpis"]["customers"] == len(d["rows"]) == 400
    assert d["kpis"]["high_value"] == sum(v["is_high_value"] for v in d["rows"]) == 80
    assert d["kpis"]["clv_12m"] == round(sum(v["clv_12m"] for v in d["rows"]), 2)
    for cid in [v["customer_id"] for v in d["rows"][:5]]:
        assert client.get("/api/customers/" + cid).json()["customer"]["is_synthetic"] is True
    assert "no-store" in r.headers["cache-control"]
    assert client.get("/api/customers/nonexistent").status_code == 404


def test_filters_use_full_year_scores_but_restrict_trips(client):
    d = client.get("/api/dashboard?months=1").json()
    full = web.snapshot()["dashboard"]
    assert len(d["rows"]) < len(full["rows"])
    for row in d["rows"]:
        original = next(r for r in full["rows"] if r["customer_id"] == row["customer_id"])
        assert row["clv_12m"] == original["clv_12m"]
        assert row["churn_risk"] == original["churn_risk"]
        assert row["frequency"] <= original["frequency"]
    assert client.get("/api/dashboard?months=13").status_code == 422
    assert client.get("/api/dashboard?segment=nonexistent").json()["kpis"]["customers"] == 0


def test_review_preserves_snapshot_and_blocks_duplicate(client):
    rec = client.post("/api/drafts", json={"customer_id": "SYN-0077"}).json()
    assert (
        client.post(
            "/api/decisions", json={"draft_id": rec["draft_id"], "status": "APPROVED"}
        ).status_code
        == 409
    )
    body = {
        "draft_id": rec["draft_id"],
        "status": "APPROVED",
        "confirmed_checklist": [v["code"] for v in rec["review_checklist"]],
    }
    response = client.post("/api/decisions", json=body)
    assert response.status_code == 200
    assert response.json()["recommendation"] == rec
    assert response.json()["sent"] is False
    assert client.post("/api/decisions", json=body).status_code == 409
    assert client.get("/api/decisions").json()[0]["recommendation"]["draft_id"] == rec["draft_id"]


def test_other_session_cannot_review_draft(client):
    rec = client.post("/api/drafts", json={"customer_id": "SYN-0077"}).json()
    client.post("/api/session", json={})
    assert (
        client.post(
            "/api/decisions", json={"draft_id": rec["draft_id"], "status": "REJECTED"}
        ).status_code
        == 409
    )


def test_quota_atomic_under_concurrency(client):
    def reserve(_):
        return Storage().reserve("concurrent", 5, 0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        values = list(pool.map(reserve, range(15)))
    assert sorted(v for v in values if v > 0) == [1, 2, 3, 4, 5]
    assert values.count(-1) == 10


def test_interval_blocks_rapid_requests(client):
    s = Storage()
    assert s.reserve("interval", 5, 20) == 1
    assert s.reserve("interval", 5, 20) == -2


def test_missing_redis_prevents_hosted_generation(client, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    from crm_runtime.storage import StorageUnavailable

    with pytest.raises(StorageUnavailable):
        web.generate("", {}, {})


def test_gemini_single_attempt_and_cached_response(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("GEMINI_MAX_ATTEMPTS", "3")
    calls = []

    def reply(*args, **kwargs):
        calls.append(kwargs)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "answer": "Resposta com fontes",
                                            "citations": ["computed-snapshot"],
                                        }
                                    )
                                }
                            ]
                        },
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", reply)
    result = client.post(
        "/api/ask", json={"question": "Explique o risco", "customer_id": "SYN-0077"}
    ).json()
    again = client.post(
        "/api/ask", json={"question": "Explique o risco", "customer_id": "SYN-0077"}
    ).json()
    assert result["mode"] == again["mode"] == "gemini_grounded"
    assert len(calls) == 1
    assert "key" not in calls[0]["json"]


def test_provider_503_does_not_retry(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("GEMINI_MAX_ATTEMPTS", "3")
    calls = []

    def unavailable(*args, **kwargs):
        calls.append(1)
        return httpx.Response(503, json={"error": {"message": "secret-provider-text"}})

    monkeypatch.setattr(httpx, "post", unavailable)
    result = client.post("/api/ask", json={"question": "Explique o risco"}).json()
    assert result["mode"] == "structured_fallback"
    assert len(calls) == 1
    assert "secret-provider-text" not in str(result)


def test_no_key_fallback_is_explicit(client):
    r = client.post("/api/ask", json={"question": "Explique o risco"}).json()
    assert r["mode"] == "structured_fallback"
    assert "não foi gerada por LLM" in r["answer"]


def test_unsafe_generated_draft_is_blocked(client, monkeypatch):
    monkeypatch.setattr(
        web,
        "generate",
        lambda *a: {
            "draft": "Receba um upgrade garantido",
            "action_code": "WIN_BACK_PERSONAL",
            "citations": ["catalogo-mvp-v2#0"],
        },
    )
    result = client.post("/api/drafts", json={"customer_id": "SYN-0077", "generate": True}).json()
    assert result["mode"] == "playbook_template"
    assert "upgrade garantido" not in result["draft"]


def test_sentiment_without_gemini(client):
    body = {
        "reviews": [
            {
                "review_id": "test",
                "text": "Atendimento excelente, mas atraso no embarque.",
                "source_url": "",
                "is_synthetic": True,
            }
        ]
    }
    r = client.post("/api/sentiment", json=body)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    body["reviews"][0]["is_synthetic"] = False
    assert client.post("/api/sentiment", json=body).status_code == 422


def test_generated_runtime_matches_canonical_sources():
    for original, generated in [
        ("src/azul_crm/infrastructure/gemini.py", "gemini.py"),
        ("src/azul_crm/application/sentiment.py", "sentiment.py"),
    ]:
        assert (ROOT / original).read_text(encoding="utf-8") == (
            ROOT / "web/crm_runtime" / generated
        ).read_text(encoding="utf-8")


def test_filtered_observed_values_match_selected_trips(client):
    response = client.get("/api/dashboard?months=3").json()
    from datetime import date, timedelta

    end = date.fromisoformat(web.snapshot()["dashboard"]["rows"][0]["evaluated_at"])
    start = end - timedelta(days=round(3 * 365.25 / 12) - 1)
    for row in response["rows"]:
        trips = [
            t
            for t in web.snapshot()["customers"][row["customer_id"]]["trips"]
            if start.isoformat() <= t["flight_date"] <= end.isoformat()
        ]
        assert row["frequency"] == len(trips)
        assert (
            row["recency_days"]
            == (end - max(date.fromisoformat(t["flight_date"]) for t in trips)).days
        )
        assert row["observed_spend"] == round(sum(t["fare_amount"] for t in trips), 2)
        assert row["weighted_value_at_risk"] == round(row["clv_12m_proxy"] * row["churn_risk"], 2)
