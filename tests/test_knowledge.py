import json
import tomllib
from pathlib import Path

from azul_crm.infrastructure.rag import DocumentIndex

REPO = Path(__file__).resolve().parents[1]


def methodology():
    path = REPO / "data/knowledge/method.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_methodology_document_matches_the_current_definition_and_config():
    text = methodology()["text"]
    with (REPO / "config/settings.toml").open("rb") as file:
        clv = tomllib.load(file)["clv"]
    assert f"{clv['top_share']:.0%}" in text  # o corte do alto valor
    assert f"{clv['margin']:.0%}" in text and f"{clv['discount_rate']:.0%}" in text
    assert "CLV" in text
    assert "pelo menos 70" not in text and "proxy de receita" not in text  # definição antiga


def test_methodology_stays_in_a_single_retrieval_chunk():
    assert len(methodology()["text"].split()) <= 150  # acima disso o documento vira dois trechos


def test_assistant_explains_value_and_risk_with_the_current_method():
    answer = DocumentIndex(REPO).answer("Como o valor e o risco são calculados?")
    assert (
        answer["evidence"][0]["document_id"] == "metodo-mvp-v2#0"
    )  # o primeiro, mesmo com mais documentos
    assert "20%" in answer["answer"] and "CLV" in answer["answer"]
