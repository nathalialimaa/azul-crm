"""A base de conhecimento pode crescer (por exemplo, com o regulamento do programa de fidelidade).

Estes testes usam um documento sintético grande e garantem que a recomendação continua achando o
trecho de governança, que o assistente acha cláusulas novas e que a abstenção continua valendo.
"""

import json
import random
import shutil
from pathlib import Path

import pytest

from azul_crm.bootstrap import build_container
from azul_crm.infrastructure.rag import DocumentIndex
from azul_crm.infrastructure.settings import Settings
from azul_crm.pipeline.demo import prepare_demo

REPO = Path(__file__).resolve().parents[1]
QUERY = "relacionamento contato sem benefício"
MARKER = "Cláusula especial zeta: os Pontos Azul de teste expiram em vinte e quatro meses."


def repeated_clauses():
    clause = (
        "Cláusula {n}. O Participante mantém contato e relacionamento com a Azul, e o benefício "
        "do Programa depende das regras de acúmulo, resgate e validade dos Pontos Azul."
    )
    return "\n\n".join(clause.format(n=i) for i in range(1, 200))


def rare_mentions():
    rng = random.Random(1)
    vocabulary = [f"termo{i}" for i in range(600)]
    paragraphs = []
    for i in range(1, 41):
        words = " ".join(rng.choice(vocabulary) for _ in range(150))
        if i in (7, 19, 33):
            words += " relacionamento contato benefício"
        paragraphs.append(f"Cláusula {i}. {words}")
    return "\n\n".join(paragraphs)


@pytest.fixture(params=["repetidas", "mencoes_raras"])
def big_base(request, tmp_path, monkeypatch):
    for name in ["config", "data/fixtures", "data/knowledge"]:
        shutil.copytree(REPO / name, tmp_path / name)
    body = repeated_clauses() if request.param == "repetidas" else rare_mentions()
    document = {
        "document_id": "regulamento-teste",
        "title": "Regulamento de teste",
        "text": body + "\n\n" + MARKER,
        "source": "https://exemplo.invalido/regulamento",
        "version": "teste",
        "is_demo": False,
    }
    (tmp_path / "data/knowledge/regulamento-teste.json").write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    prepare_demo(Settings(tmp_path), customers=120)
    return tmp_path


def test_governance_evidence_is_still_the_catalog_chunk(big_base):
    index = DocumentIndex(big_base)
    assert len(index.chunks) > 20  # a base realmente cresceu
    found = index.retrieve(QUERY)
    assert found and found[0].source == "internal://catalogo-acoes-mvp"


def test_every_recommendation_still_has_an_action(big_base):
    container = build_container(Settings(big_base))
    for customer in container.crm.customers()[:25]:
        rec = container.recommendations.recommend(customer.customer_id)
        ids = [e.document_id for e in rec.evidence]
        assert rec.action.code != "NO_ACTION", customer.customer_id
        assert "catalogo-mvp-v2#0" in ids and "playbook-" + rec.action.code in ids


def test_assistant_finds_a_new_clause_and_still_abstains(big_base):
    index = DocumentIndex(big_base)
    found = index.answer("Quando expiram os Pontos Azul de teste da cláusula zeta?")
    assert any(e["document_id"].startswith("regulamento-teste#") for e in found["evidence"])
    assert "vinte e quatro meses" in found["answer"]
    empty = index.answer("xyzzy zqxw plasma")
    assert not empty["evidence"] and "evidência suficiente" in empty["answer"]


def test_build_reports_every_chunk(big_base):
    index = DocumentIndex(big_base)
    assert index.build()["chunks"] == len(index.chunks) > 20
