import json
from dataclasses import dataclass
from datetime import date

import httpx
import pytest

from azul_crm.domain.models import Action, Evidence
from azul_crm.infrastructure.gemini import (
    GeminiClient,
    GeminiMessageGenerator,
    GeminiUnavailable,
    schema_for,
)

EVIDENCE = (
    Evidence(
        "source#1", "Governança", "Contato exige revisão humana.", "internal://method", "v1", True
    ),
)


def response(payload, status=200):
    return httpx.Response(
        status,
        request=httpx.Request(
            "POST", "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent"
        ),
        json={
            "candidates": [
                {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(payload)}]}}
            ]
        },
    )


def test_client_uses_secret_header_and_structured_schema(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")

    def post(url, **kwargs):
        assert "unit-test-key" not in url
        assert kwargs["headers"]["x-goog-api-key"] == "unit-test-key"
        assert kwargs["json"]["generationConfig"]["responseMimeType"] == "application/json"
        return response({"answer": "Resposta", "citations": ["source#1"]})

    monkeypatch.setattr(httpx, "post", post)
    assert (
        GeminiClient().generate("system", {}, schema_for("answer", "citations"))["answer"]
        == "Resposta"
    )


def test_missing_key_does_not_attempt_network(monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: pytest.fail("Sem chave não deve chamar rede")
    )
    with pytest.raises(GeminiUnavailable, match="GEMINI_API_KEY"):
        GeminiClient().generate("", {}, {})


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500])
def test_provider_errors_are_sanitized(monkeypatch, status):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: response({"secret": "unit-test-key"}, status)
    )
    with pytest.raises(GeminiUnavailable) as error:
        GeminiClient().generate("", {}, {})
    assert "unit-test-key" not in str(error.value)


class Fallback:
    def draft(self, *args):
        return "Texto local para revisão."


@dataclass
class Scores:
    churn_risk: float = 0.7
    evaluated_at: date = date(2026, 9, 30)


@dataclass
class Customer:
    preferred_channel: str = "email"
    is_synthetic: bool = True


def draft(monkeypatch, payload):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: response(payload))
    return GeminiMessageGenerator(Fallback()).draft(
        Customer(), Scores(), Action("CONTACT", "Contato", "Escuta"), EVIDENCE
    )


def test_real_text_generation_is_not_limited_to_template_sentences(monkeypatch):
    text = draft(
        monkeypatch,
        {
            "draft": "Olá! Sua experiência é importante para nós. Podemos ouvir como foi sua última viagem?",
            "action_code": "CONTACT",
            "citations": ["source#1"],
        },
    )
    assert "Sua experiência" in text and "Gerado por Gemini" in text
    assert "contingência" not in text


@pytest.mark.parametrize(
    "payload",
    [
        {"draft": "Ganhe um upgrade", "action_code": "CONTACT", "citations": ["source#1"]},
        {"draft": "Olá!", "action_code": "OTHER", "citations": ["source#1"]},
        {"draft": "Olá!", "action_code": "CONTACT", "citations": ["inventada"]},
        {"draft": "Olá!", "action_code": "CONTACT", "citations": []},
        {"draft": "Você receberá 100 reais", "action_code": "CONTACT", "citations": ["source#1"]},
    ],
)
def test_unsafe_drafts_fail_closed_with_visible_fallback(monkeypatch, payload):
    text = draft(monkeypatch, payload)
    assert text.startswith("Texto local") and "contingência" in text


def test_review_uses_same_snapshot_without_regenerating(client):
    service = client.app.state.container.recommendations
    cid = service.crm.customers()[0].customer_id
    rec = service.recommend(cid)
    service.generator = None
    assert service.for_review(cid) is rec


def test_preview_does_not_cache_a_generated_draft(client):
    service = client.app.state.container.recommendations
    cid = service.crm.customers()[0].customer_id
    result = client.post("/api/v1/agent/recommend", json={"customer_id": cid, "generate": False})
    assert result.status_code == 200 and cid not in service._drafts


def test_model_name_cannot_change_endpoint(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "../../unsafe?key=secret")
    with pytest.raises(GeminiUnavailable):
        GeminiClient()


def test_temporary_overload_retries_then_returns_real_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setattr("azul_crm.infrastructure.gemini.time.sleep", lambda delay: None)
    replies = iter(
        [response({}, 503), response({"answer": "Recuperado", "citations": ["source#1"]})]
    )
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        return next(replies)

    monkeypatch.setattr(httpx, "post", post)
    result = GeminiClient().generate("", {}, schema_for("answer", "citations"))
    assert len(calls) == 2 and result["answer"] == "Recuperado"


def test_retry_respects_overall_deadline(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    times = iter([0, 0, 46])
    monkeypatch.setattr("azul_crm.infrastructure.gemini.time.monotonic", lambda: next(times))
    monkeypatch.setattr("azul_crm.infrastructure.gemini.time.sleep", lambda delay: None)
    calls = []

    def post(*args, **kwargs):
        calls.append(args)
        return response({}, 503)

    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(GeminiUnavailable, match="tempo de resposta"):
        GeminiClient().generate("", {}, {})
    assert len(calls) == 1


def test_two_reviewers_of_same_customer_keep_distinct_snapshots(client):
    service = client.app.state.container.recommendations
    cid = service.crm.customers()[0].customer_id
    first = service.recommend(cid)
    second = service.recommend(cid)
    assert first.draft_id != second.draft_id
    assert service.for_review(cid, first.draft_id) is first
    assert service.for_review(cid, second.draft_id) is second
    with pytest.raises(ValueError, match="expirado"):
        service.for_review(cid, "invalid")


def test_api_rejects_unknown_review_snapshot(client):
    cid = client.get("/api/v1/customers").json()["items"][0]["customer_id"]
    response = client.post(
        "/api/v1/decisions", json={"customer_id": cid, "status": "REJECTED", "draft_id": "unknown"}
    )
    assert response.status_code == 409
