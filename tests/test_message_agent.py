import json

import httpx
import pytest

from azul_crm.domain.models import Action, Evidence
from azul_crm.infrastructure.message_agent import BoundedMessageGenerator


class Template:
    def draft(self, *args):
        return "Obrigado por voar conosco. Queremos ouvir você. [Rascunho para revisão humana; nenhuma mensagem foi enviada.]"


def generate(monkeypatch, payload):
    def post(url, **kwargs):
        assert "sentences" in json.loads(kwargs["json"]["prompt"])
        return httpx.Response(
            200, json={"response": json.dumps(payload)}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", post)
    return BoundedMessageGenerator(Template()).draft(
        None,
        None,
        Action("CONTACT", "Contato", "Revisão"),
        (Evidence("method#0", "Método", "Contato", "internal://method", "v1", True),),
    )


def test_agent_composes_only_verified_phrases(monkeypatch):
    text = generate(
        monkeypatch,
        {
            "sentence_ids": ["0", "1"],
            "opening": "cordial",
            "closing": "escuta",
            "citations": ["method#0"],
        },
    )
    assert text.startswith("Olá! Obrigado por voar conosco.")
    assert "Composição assistida por LLM" in text and "fallback" not in text


@pytest.mark.parametrize(
    "payload",
    [
        {"sentence_ids": ["0"], "citations": ["method#0"]},
        {"sentence_ids": ["0", "1"], "citations": ["inventado"]},
        {
            "sentence_ids": ["0", "1"],
            "citations": ["method#0"],
            "opening": "Ganhe bônus",
            "closing": "escuta",
        },
    ],
)
def test_agent_rejects_unsupported_content_and_citations(monkeypatch, payload):
    assert "fallback para template" in generate(monkeypatch, payload)


def test_agent_falls_back_if_service_is_offline(monkeypatch):
    def offline(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "post", offline)
    text = BoundedMessageGenerator(Template()).draft(
        None,
        None,
        Action("CONTACT", "Contato", "Revisão"),
        (Evidence("x", "Método", "Contato", "internal://method", "v1", True),),
    )
    assert "fallback" in text
