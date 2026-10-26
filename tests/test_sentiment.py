import json
from pathlib import Path

import pytest

from azul_crm.application.sentiment import analyze_csv, analyze_reviews, analyze_text


@pytest.mark.parametrize(
    "text,label",
    [
        ("Atendimento excelente e pontual.", "positivo"),
        ("Péssimo, voo cancelado.", "negativo"),
        ("Não foi bom", "negativo"),
        ("Sem atraso", "positivo"),
        ("Não foi ruim", "positivo"),
        ("Não recomendo. Atendimento bom mas voo cancelado", "misto"),
        ("Voo de Recife para Campinas", "inconclusivo"),
    ],
)
def test_lexical_sentiment_explains_negation_and_abstains(text, label):
    result = analyze_text(text)
    assert result["label"] == label
    assert (result["score"] is None) == (label == "inconclusivo")


def test_csv_marks_synthetic_and_requires_public_provenance():
    sample = Path(__file__).resolve().parents[1] / "data/fixtures/reviews.csv"
    result = analyze_csv(sample.read_bytes())
    assert result["total"] == result["synthetic"] == 5
    assert result["validated_on_real_labels"] is False
    row = {"review_id": "r1", "text": "bom", "is_synthetic": False, "source_url": ""}
    with pytest.raises(ValueError, match="HTTPS"):
        analyze_reviews([row])
    row["source_url"] = "https://example.org/review/1"
    assert analyze_reviews([row])["synthetic"] == 0
    with pytest.raises(ValueError, match="duplicado"):
        analyze_reviews([row, row])


@pytest.mark.parametrize(
    "content",
    [
        b"text\nbom",
        b"review_id,text,source_url,is_synthetic\nr1,bom,,talvez",
        b"x" * (2 * 1024 * 1024 + 1),
    ],
    ids=["missing-columns", "invalid-flag", "oversized"],
)
def test_csv_rejects_invalid_or_oversized_inputs(content):
    with pytest.raises(ValueError):
        analyze_csv(content)


def test_sentiment_api_validates_and_returns_explanation(client):
    row = {"review_id": "r1", "text": "Não foi bom", "source_url": "", "is_synthetic": True}
    response = client.post("/api/v1/sentiment/analyze", json={"reviews": [row]})
    assert response.status_code == 200
    result = response.json()
    assert result["reviews"][0]["evidence"][0]["negated"] is True
    assert result["counts"] == {"negativo": 1}
    row["is_synthetic"] = False
    assert client.post("/api/v1/sentiment/analyze", json={"reviews": [row]}).status_code == 422
    assert client.post("/api/v1/sentiment/analyze", json={"reviews": []}).status_code == 422


def test_sentiment_cli_writes_report(tmp_path, monkeypatch, capsys):
    from azul_crm.cli import main

    source = Path(__file__).resolve().parents[1] / "data/fixtures/reviews.csv"
    output = tmp_path / "report.json"
    monkeypatch.setattr(
        "sys.argv", ["azul-crm", "sentiment", "--file", str(source), "--out", str(output)]
    )
    main()
    assert json.loads(output.read_text(encoding="utf-8"))["total"] == 5
