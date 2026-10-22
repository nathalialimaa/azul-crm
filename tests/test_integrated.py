import shutil
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from azul_crm.api.main import create_app
from azul_crm.bootstrap import build_container
from azul_crm.infrastructure.rag import DocumentIndex
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.infrastructure.validation import validate_store
from azul_crm.pipeline.extended import generate
from azul_crm.pipeline.modeling import train
from azul_crm.pipeline.public_data import AirportDimension, ingest_fares


@pytest.fixture
def integrated(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1]
    for name in ["config", "data/fixtures", "data/knowledge"]:
        shutil.copytree(source / name, tmp_path / name)
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    generate(Settings(tmp_path), 120, 42)
    return tmp_path, Store(tmp_path)


def test_atomic_store_and_reproducible_gold(integrated):
    root, store = integrated
    original = store.read("trips")
    assert validate_store(store)["customers"] == 120
    generate(Settings(root), 120, 42)
    assert store.read("trips") == original
    with pytest.raises(ValueError):
        store.publish({"customers": [("dup", {}), ("dup", {})]})
    assert len(store.read("customers")) == 120


def test_pipeline_and_api(integrated):
    root, store = integrated
    c = build_container(Settings(root))
    with TestClient(create_app(c)) as api:
        d = api.get("/api/v1/dashboard").json()
        assert len(d["rows"]) == 120
        assert d["kpis"]["clv_12m_proxy"] == round(sum(r["clv_12m_proxy"] for r in d["rows"]), 2)
        assert api.get("/api/v1/dashboard?route=ZZZ-XXX").json()["rows"] == []
        assert api.get("/api/v1/dashboard?months=0").status_code == 422
        cid = d["rows"][0]["customer_id"]
        rec = api.post("/api/v1/agent/recommend", json={"customer_id": cid}).json()
        assert rec["evidence"] and rec["status"] == "DRAFT_REQUIRES_REVIEW"
        answer = api.post(
            "/api/v1/agent/ask", json={"question": "Por que o risco?", "customer_id": cid}
        ).json()
        assert answer["mode"] == "structured_customer_facts"
        response = api.post("/api/v1/decisions", json={"customer_id": cid, "status": "APPROVED"})
        assert response.status_code == 200 and response.json()["sent"] is False
        assert len(store.read("decisions")) == 1
        result = api.post(
            "/api/v1/simulations", json={"cost_per_customer": 10, "assumed_retention": 0}
        ).json()
        assert result["net_scenario"] == -1200 and result["causal_claim"] is False
        assert (
            api.get("/api/v1/customers/" + cid + "/loyalty").json()["official_eligibility"] is False
        )


def test_rag_sources_and_abstention(integrated):
    root, _ = integrated
    rag = DocumentIndex(root)
    assert rag.answer("Como o score combina gasto frequência e recência?")["evidence"]
    result = rag.answer("xyzzy zqxw plasma")
    assert not result["evidence"]
    assert "evidência suficiente" in result["answer"]
    assert rag.build()["chunks"] == 2


def test_airport_missing_ambiguous():
    d = AirportDimension(
        [
            {"ident": "SBRF", "iata_code": "REC"},
            {"ident": "XXXX", "iata_code": ""},
            {"ident": "DUPL", "iata_code": "AAA"},
            {"ident": "DUPL", "iata_code": "BBB"},
        ]
    )
    assert d.lookup(" sbrf ") == ("REC", "matched")
    assert d.lookup("XXXX") == (None, "without_iata")
    assert d.lookup("DUPL") == (None, "ambiguous")
    assert d.lookup("ZZZZ") == (None, "unknown")


def test_ingestion_idempotent_period_and_unmatched(integrated):
    root, store = integrated
    store.publish(
        {
            "airports": [
                ("1", {"ident": "SBRF", "iata_code": "REC"}),
                ("2", {"ident": "SBGR", "iata_code": "GRU"}),
            ]
        }
    )
    path = root / "test.csv"
    path.write_text(
        "nr_ano_referencia;nr_mes_referencia;sg_empresa_icao;sg_icao_origem;sg_icao_destino;nr_tarifa;nr_assentos\n2026;6;AZU;SBRF;SBGR;400,00;2\n2026;6;AZU;SBRF;ZZZZ;300,00;1\n"
    )
    result = ingest_fares(path, root, "2026-06")
    assert result["unmatched"] == 1 and len(store.read("fares")) == 2
    assert ingest_fares(path, root, "2026-06")["already_ingested"]
    assert len(store.read("fares")) == 2
    with pytest.raises(ValueError):
        ingest_fares(path, root, "2026-07")
    bad = root / "bad.csv"
    bad.write_text(path.read_text().replace("400,00", "NaN"))
    with pytest.raises(ValueError):
        ingest_fares(bad, root, "2026-06")
    assert len(store.read("fares")) == 2


def test_training_and_future_leakage(integrated):
    root, store = integrated
    report = train(root, store)
    assert sum(report["split"].values()) == 120
    assert 0 <= report["test_model"]["roc_auc"] <= 1
    assert report["synthetic_only"]
    feats = store.read("features")
    assert all("churn" not in r and "future_trip_count" not in r for r in feats)
    build_container(Settings(root))
    feats[0]["spend"] += 10
    store.publish({"features": [(r["customer_id"], r) for r in feats]})
    with pytest.raises(ValueError, match="Modelo incompatível"):
        build_container(Settings(root))


def test_vra_missing_time_is_not_zero_delay(integrated):
    from azul_crm.pipeline.public_data import ingest_vra

    root, store = integrated
    p = root / "vra.csv"
    p.write_text(
        "Sigla ICAO Empresa Aérea;Número Voo;Sigla ICAO Aeroporto Origem;Sigla ICAO Aeroporto Destino;Partida Prevista;Partida Real;Situação Voo\nAZU;1234;SBRF;SBGR;01/06/2026 10:00;;CANCELADO\nAZU;1235;SBRF;SBGR;02/06/2026 10:00;02/06/2026 11:15;REALIZADO\n"
    )
    assert ingest_vra(p, root, "2026-06", "fixture")["silver_rows"] == 2
    rows = store.read("operations")
    cancelled = next(r for r in rows if r["cancelled"])
    flown = next(r for r in rows if r["cancelled"] is False)
    assert cancelled["delay_minutes"] is None
    assert flown["delay_minutes"] == 75
    assert ingest_vra(p, root, "2026-06", "fixture")["already_ingested"]


def test_download_retries_and_cached_hash(tmp_path, monkeypatch):
    from contextlib import contextmanager

    from azul_crm.pipeline.public_data import download

    calls = []

    @contextmanager
    def stream(*args, **kwargs):
        calls.append(1)
        response = httpx.Response(
            200, content=b"a;b\n1;2\n", request=httpx.Request("GET", "https://example.org/data.csv")
        )
        yield response

    monkeypatch.setattr(httpx, "stream", stream)
    first, meta = download("https://example.org/data.csv", tmp_path)
    second, _ = download("https://example.org/data.csv", tmp_path)
    assert first == second and len(calls) == 1
    first.write_bytes(b"corrupt")
    download("https://example.org/data.csv", tmp_path)
    assert len(calls) == 2


def test_document_import_and_index_refresh(integrated):
    from azul_crm.pipeline.documents import import_document

    root, _ = integrated
    file = root / "rule.txt"
    file.write_text(
        "Documento fictício: abacaxizeiro é uma palavra exclusiva para testar recuperação documental com procedência e hash.",
        encoding="utf-8",
    )
    result = import_document(file, root, "test-doc", "Teste de ingestão", "internal://test", True)
    assert result["characters"] > 50
    assert any(
        e.document_id.startswith("test-doc#") for e in DocumentIndex(root).retrieve("abacaxizeiro")
    )
    with pytest.raises(ValueError):
        import_document(file, root, "../../escape", "Teste", "internal://test", True)
