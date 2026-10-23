import json
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from azul_crm.api.main import create_app
from azul_crm.bootstrap import build_container
from azul_crm.infrastructure.lake import (
    BY_NAME,
    LAYERS,
    SNOWFLAKE_TYPES,
    TABLES,
    convert_rows,
    export_lake,
    load_dictionary,
    snowflake_ddl,
)
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.demo import prepare_demo
from azul_crm.pipeline.public_data import import_airports, ingest_fares

REPO = Path(__file__).resolve().parents[1]
FARES = (
    "nr_ano_referencia;nr_mes_referencia;sg_empresa_icao;sg_icao_origem;sg_icao_destino;"
    "nr_tarifa;nr_assentos\n2026;6;AZU;SBRF;SBGR;400,00;2\n2026;6;AZU;SBRF;ZZZZ;300,00;1\n"
)


@pytest.fixture
def root(tmp_path, monkeypatch):
    for name in ["config", "data/fixtures", "data/knowledge"]:
        shutil.copytree(REPO / name, tmp_path / name)
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    prepare_demo(Settings(tmp_path), customers=120)
    return tmp_path


def parquet(out, qualified):
    return pq.read_table(out / BY_NAME[qualified].layer / f"{BY_NAME[qualified].name}.parquet")


def test_schema_registry_is_consistent():
    names = [t.qualified for t in TABLES]
    assert len(names) == len(set(names))
    for t in TABLES:
        assert t.layer in LAYERS and t.description and t.origin
        columns = [c.name for c in t.columns]
        assert len(columns) == len(set(columns)) and all(c.description for c in t.columns)
        assert set(t.primary_key) <= set(columns)
        assert all(c.dtype in SNOWFLAKE_TYPES for c in t.columns)


def test_export_writes_typed_parquet_that_matches_the_store(root):
    store = Store(root)
    summary = export_lake(root, store, root / "lake")
    out = root / "lake"
    assert summary["rows"]["gold.customers"] == 120
    for qualified, rows in summary["rows"].items():
        assert parquet(out, qualified).num_rows == rows

    trips = parquet(out, "gold.trips")
    assert trips.schema.field("flight_date").type == pa.date32()
    assert trips.schema.field("fare_amount").type == pa.float64()
    assert trips.schema.field("delay_minutes").type == pa.int64()
    assert parquet(out, "gold.outcomes").schema.field("future_trip_dates").type == pa.list_(
        pa.date32()
    )
    scores = parquet(out, "gold.scores")
    assert scores.schema.field("drivers").type == pa.list_(pa.string())
    assert scores.schema.field("customer_id").metadata[b"description"]  # descrição vai no arquivo

    first = store.read("trips")[0]
    row = trips.slice(0, 1).to_pylist()[0]
    assert row["trip_id"] == first["trip_id"] and row["fare_amount"] == first["fare_amount"]
    assert row["flight_date"] == date.fromisoformat(first["flight_date"])

    loyalty = store.read("loyalty")
    assert summary["rows"]["gold.loyalty_transactions"] == sum(
        len(r["transactions"]) for r in loyalty
    )
    assert {"gold.personas", "gold.bias_audit_groups", "gold.manifest"} <= set(summary["rows"])


def test_dictionary_describes_every_table_and_column(root):
    export_lake(root, Store(root), root / "lake")
    out = root / "lake"
    dictionary = json.loads((out / "data_dictionary.json").read_text(encoding="utf-8"))
    assert dictionary["customers_are_synthetic"] is True
    assert dictionary["snapshot"]["customer_count"] == 120
    assert set(dictionary["tables"]) == {t.qualified for t in TABLES}
    markdown = (out / "DATA_DICTIONARY.md").read_text(encoding="utf-8")
    for key, table in dictionary["tables"].items():
        assert f"### {key}" in markdown
        assert all(c["description"] and c["snowflake_type"] for c in table["columns"])
        if table["exported"]:
            assert (out / table["path"]).exists() and table["content_sha256"]
            assert pq.read_metadata(out / table["path"]).num_rows == table["rows"]
        else:
            assert table["rows"] == 0 and not (out / table["path"]).exists()
    assert dictionary["tables"]["gold.decisions"]["exported"] is False


def test_export_is_deterministic_and_reflects_the_data(root):
    first = export_lake(root, Store(root), root / "a")
    dictionary_a = json.loads((root / "a/data_dictionary.json").read_text(encoding="utf-8"))
    export_lake(root, Store(root), root / "b")
    dictionary_b = json.loads((root / "b/data_dictionary.json").read_text(encoding="utf-8"))
    assert dictionary_a == dictionary_b and first["tables_exported"] > 0

    prepare_demo(Settings(root), customers=120, seed=7, force=True)
    export_lake(root, Store(root), root / "c")
    dictionary_c = json.loads((root / "c/data_dictionary.json").read_text(encoding="utf-8"))
    assert (
        dictionary_c["tables"]["gold.trips"]["content_sha256"]
        != dictionary_a["tables"]["gold.trips"]["content_sha256"]
    )


def test_snowflake_ddl_is_typed_and_explicit_about_being_untested():
    ddl = snowflake_ddl()
    assert "NÃO TESTADO" in ddl and "LAKE_GOLD" in ddl
    for t in TABLES:
        assert f"CREATE TABLE IF NOT EXISTS AZUL_CRM.LAKE_{t.layer.upper()}.{t.name.upper()}" in ddl
    assert "CUSTOMER_ID VARCHAR NOT NULL" in ddl and "IS_SYNTHETIC BOOLEAN NOT NULL" in ddl
    assert "DRIVERS ARRAY NOT NULL" in ddl and "RECOMMENDATION VARIANT NOT NULL" in ddl
    assert "PRIMARY KEY (CUSTOMER_ID)" in ddl


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda r: r.update(canal_novo="x"), "fora do esquema"),
        (lambda r: r.pop("home_airport"), "obrigatório ausente"),
        (lambda r: r.update(is_synthetic="talvez"), "valor inválido"),
        (lambda r: r.update(home_airport=None), "obrigatório ausente"),
    ],
)
def test_data_outside_the_schema_fails_and_writes_nothing(root, mutate, message):
    store = Store(root)
    rows = store.read("customers")
    mutate(rows[0])
    store.publish({"customers": [(r["customer_id"], r) for r in rows]})
    out = root / "lake"
    with pytest.raises(ValueError, match=message):
        export_lake(root, store, out)
    assert not out.exists()


def test_duplicate_primary_key_fails_and_writes_nothing(root):
    store = Store(root)
    duplicate = store.read("customers")[0]
    store.publish({"customers": [("duplicate-storage-id", duplicate)]}, replace=False)
    out = root / "lake"

    with pytest.raises(ValueError, match="gold.customers.*chave primária duplicada"):
        export_lake(root, store, out, batch_size=7)

    assert not out.exists()


def test_type_conversion_rules():
    trips = BY_NAME["gold.trips"]
    ok = {
        "trip_id": "T1",
        "customer_id": "C1",
        "origin": "REC",
        "destination": "GRU",
        "flight_date": "2026-01-02",
        "fare_amount": "10.5",
        "delay_minutes": 3,
    }
    assert convert_rows(trips, [ok])[0][4:] == [date(2026, 1, 2), 10.5, 3]
    with pytest.raises(ValueError, match="flight_date"):
        convert_rows(trips, [{**ok, "flight_date": "02/01/2026"}])
    with pytest.raises(ValueError, match="delay_minutes"):
        convert_rows(trips, [{**ok, "delay_minutes": True}])  # booleano não é inteiro
    with pytest.raises(ValueError, match="fare_amount"):
        convert_rows(trips, [{**ok, "fare_amount": ""}])  # vazio em coluna obrigatória
    decisions = BY_NAME["gold.decisions"]
    base = {
        "id": "1",
        "customer_id": "C1",
        "status": "APPROVED",
        "note": "",
        "recommendation": {"a": 1},
        "sent": False,
    }
    with pytest.raises(ValueError, match="created_at"):
        convert_rows(decisions, [{**base, "created_at": "2026-01-01T10:00:00"}])  # sem fuso
    row = convert_rows(decisions, [{**base, "created_at": "2026-01-01T10:00:00-03:00"}])[0]
    assert row[5] == datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc)
    assert json.loads(row[4]) == {"a": 1}


def test_open_source_columns_are_ignored_only_where_declared():
    airports = BY_NAME["silver.airports"]
    record = {
        "ident": "SBRF",
        "iata_code": "REC",
        "latitude_deg": "",
        "type": "large_airport",  # coluna extra da fonte aberta
        "mapping_sha256": "abc",
        "source": "https://exemplo",
    }
    row = convert_rows(airports, [record])[0]
    assert row[1] == "SBRF" and row[5] is None  # vazio vira nulo onde é permitido
    with pytest.raises(ValueError, match="mapping_sha256"):
        convert_rows(airports, [{k: v for k, v in record.items() if k != "mapping_sha256"}])


def test_public_data_layers_are_exported_when_ingested(root):
    store = Store(root)
    import_airports(REPO / "data/fixtures/airports_reference.csv", store)
    path = root / "fares.csv"
    path.write_text(FARES, encoding="utf-8")
    ingest_fares(path, root, "2026-06")
    summary = export_lake(root, store, root / "lake")
    out = root / "lake"
    assert summary["rows"]["bronze.sources"] == 1 and summary["rows"]["bronze.raw_rows"] == 2
    assert summary["rows"]["silver.airports"] == 10 and summary["rows"]["silver.fares"] == 2
    fares = parquet(out, "silver.fares")
    assert fares.schema.field("fare").type == pa.float64()
    assert fares.schema.field("seats").type == pa.int64()
    assert sorted(fares.column("fare").to_pylist()) == [300.0, 400.0]
    raw = parquet(out, "bronze.raw_rows").to_pylist()
    assert json.loads(raw[0]["row_json"])["nr_tarifa"] in {"400,00", "300,00"}
    assert parquet(out, "silver.airports").schema.field("latitude_deg").type == pa.float64()


def test_decisions_and_missing_artifacts(root):
    store = Store(root)
    with TestClient(create_app(build_container(Settings(root)))) as api:
        cid = api.get("/api/v1/customers?limit=1").json()["items"][0]["customer_id"]
        assert (
            api.post(
                "/api/v1/decisions", json={"customer_id": cid, "status": "APPROVED"}
            ).status_code
            == 200
        )
    (root / "artifacts/personas.json").unlink()
    (root / "artifacts/bias_report.json").unlink()
    summary = export_lake(root, store, root / "lake")
    assert summary["rows"]["gold.decisions"] == 1
    assert {"gold.personas", "gold.bias_audit_groups"} <= set(summary["tables_without_data"])
    decision = parquet(root / "lake", "gold.decisions").to_pylist()[0]
    assert json.loads(decision["recommendation"])["customer_id"] == cid
    assert decision["created_at"].tzinfo is not None and decision["sent"] is False


def test_stale_files_are_removed_when_a_table_becomes_empty(root):
    store = Store(root)
    out = root / "lake"
    export_lake(root, store, out)
    assert (out / "gold/personas.parquet").exists()
    (root / "artifacts/personas.json").unlink()
    export_lake(root, store, out)
    assert not (out / "gold/personas.parquet").exists()


def test_cli_and_api_expose_the_lake(root, monkeypatch, capsys):
    from azul_crm import cli

    assert load_dictionary(root) == {"available": False}
    with TestClient(create_app(build_container(Settings(root)))) as api:
        assert api.get("/api/v1/lake").json() == {"available": False}
        monkeypatch.setattr(sys, "argv", ["azul-crm", "export-lake"])
        cli.main()
        assert json.loads(capsys.readouterr().out)["tables_exported"] >= 10
        body = api.get("/api/v1/lake").json()
        assert body["available"] and "gold.customers" in body["tables"]
    assert (root / "data/lake/snowflake_typed.sql").exists()


def test_generated_lake_stays_out_of_git_and_docker():
    assert "data/lake/" in (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "data/lake" in (REPO / ".dockerignore").read_text(encoding="utf-8").split()


def test_batch_size_does_not_change_the_result(root):
    store = Store(root)
    export_lake(root, store, root / "a")  # lote padrão: uma leva só
    export_lake(root, store, root / "b", batch_size=7)  # muitos lotes pequenos
    dictionaries = [
        json.loads((root / d / "data_dictionary.json").read_text(encoding="utf-8")) for d in "ab"
    ]
    assert dictionaries[0] == dictionaries[1]  # mesmas linhas e mesmo hash de conteúdo
    assert pq.read_metadata(root / "b/gold/trips.parquet").num_row_groups > 1
    assert parquet(root / "a", "gold.trips").equals(parquet(root / "b", "gold.trips"))


def test_failed_export_keeps_previous_output_and_leaves_no_temp_files(root):
    store = Store(root)
    out = root / "lake"
    export_lake(root, store, out)

    def snapshot():
        return {
            p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob("*") if p.is_file()
        }

    before = snapshot()
    trips = store.read("trips")
    trips[-1]["fare_amount"] = "abc"  # falha numa tabela que vem depois de customers
    store.publish({"trips": [(t["trip_id"], t) for t in trips]})
    with pytest.raises(ValueError, match="fare_amount"):
        export_lake(root, store, out, batch_size=50)
    assert snapshot() == before
    assert list(root.glob(".lake-*")) == []


def test_store_iter_batches_matches_read(root):
    store = Store(root)
    batches = list(store.iter_batches("trips", 500))
    assert len(batches) > 1 and all(len(b) <= 500 for b in batches)
    assert [row for batch in batches for row in batch] == store.read("trips")
    assert list(store.iter_batches("decisions")) == []


def test_calibrated_routes_streams_in_batches(root, monkeypatch):
    from azul_crm.pipeline.public_data import calibrated_routes

    store = Store(root)
    import_airports(REPO / "data/fixtures/airports_reference.csv", store)
    path = root / "fares2.csv"
    header = FARES.splitlines()[0]
    rows = [
        "2026;6;AZU;SBRF;SBGR;400,00;2",
        "2026;6;AZU;SBRF;SBGR;700,00;1",
        "2026;6;AZU;SBRF;SBBR;300,00;4",
        "2026;6;GLO;SBRF;SBGR;999,00;9",  # outra empresa: fora da calibração
    ]
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    ingest_fares(path, root, "2026-06")
    original = Store.iter_batches
    monkeypatch.setattr(
        Store, "iter_batches", lambda self, name, batch_size=20000: original(self, name, 1)
    )
    routes = calibrated_routes(store)
    assert [(r["origin"], r["destination"], r["weight"]) for r in routes] == [
        ("REC", "BSB", 4),
        ("REC", "GRU", 3),
    ]
    assert routes[1]["mean_fare"] == pytest.approx((400 * 2 + 700 * 1) / 3)
