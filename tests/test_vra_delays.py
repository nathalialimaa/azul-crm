import collections
import json
import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from azul_crm.infrastructure.lake import export_lake
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.delays import EmpiricalDelays
from azul_crm.pipeline.demand import PublicDemandGenerator
from azul_crm.pipeline.extended import generate
from azul_crm.pipeline.personas import _name_cluster
from azul_crm.pipeline.public_data import csv_payload, import_airports, ingest_fares, ingest_vra

REPO = Path(__file__).resolve().parents[1]
NOTICE = "\ufeffAtualizado em: 2026-10-07\r\n"
HEADER = (
    '"ICAO Empresa Aérea";"Número Voo";"Código Autorização (DI)";"Código Tipo Linha";'
    '"ICAO Aeródromo Origem";"ICAO Aeródromo Destino";"Partida Prevista";"Partida Real";'
    '"Chegada Prevista";"Chegada Real";"Situação Voo";"Código Justificativa"\r\n'
)
START = datetime(2026, 8, 3, 10, 0, 0)


def vra_row(airline, line, origin, dest, scheduled, delay, status="REALIZADO", real=None):
    prev = scheduled.strftime("%Y-%m-%d %H:%M:%S") if scheduled else "null"
    if status == "CANCELADO" or scheduled is None:
        real = "null"
    elif real is None:
        real = (scheduled + timedelta(minutes=delay)).strftime("%Y-%m-%d %H:%M:%S")
    fields = [airline, "1234", "0", line, origin, dest, prev, real, prev, real, status, "N/A"]
    return ";".join(f'"{f}"' for f in fields) + "\r\n"


def sample_vra(extra=()):
    """AZU doméstico: REC com 380 voos de 0 a 9 min + 20 com 90 min (5% >= 60); GRU sem atrasos."""
    lines = []
    for i in range(400):
        when = START + timedelta(hours=i)
        lines.append(vra_row("AZU", "N", "SBRF", "SBGR", when, 90 if i % 20 == 0 else i % 10))
    for i in range(300):
        lines.append(vra_row("AZU", "N", "SBGR", "SBBR", START + timedelta(hours=i), 0))
    for i in range(10):  # cancelamentos: sem partida real
        lines.append(
            vra_row("AZU", "N", "SBRF", "SBGR", START + timedelta(days=3, hours=i), 0, "CANCELADO")
        )
    for i in range(20):  # fora do universo: internacional e outra empresa
        lines.append(vra_row("AZU", "I", "SBGR", "SBBR", START + timedelta(hours=i), 300))
        lines.append(vra_row("GLO", "N", "SBRF", "SBGR", START + timedelta(hours=i), 200))
    lines.append(vra_row("AZU", "N", "SBRF", "SBGR", START, -30))  # antecipado: conta como 0
    lines.extend(extra)
    return NOTICE + HEADER + "".join(lines)


@pytest.fixture
def root(tmp_path, monkeypatch):
    for name in ["config", "data/fixtures", "data/knowledge"]:
        shutil.copytree(REPO / name, tmp_path / name)
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    import_airports(REPO / "data/fixtures/airports_reference.csv", Store(tmp_path))
    return tmp_path


def write(root, text, name="vra.csv"):
    path = root / name
    path.write_text(text, encoding="utf-8")
    return path


# ------------------------------------------------------------------ leitor do VRA real


def test_notice_line_before_the_header_is_skipped(root):
    reader = csv_payload(write(root, sample_vra()))
    assert reader.fieldnames[0] == "ICAO Empresa Aérea" and "Partida Real" in reader.fieldnames
    assert next(reader)["ICAO Empresa Aérea"] == "AZU"


def test_real_format_is_ingested_in_utc_with_rejections_reported(root):
    out_of_period = vra_row("AZU", "N", "SBRF", "SBGR", datetime(2026, 9, 1, 3, 0, 0), 0)
    no_date = vra_row("AZU", "N", "SBRF", "SBGR", None, 0, "CANCELADO")
    fractional = vra_row("AZU", "N", "SBRF", "SBGR", START, 0, real="2026-08-03 10:20:00.100000000")
    path = write(root, sample_vra([out_of_period, no_date, fractional]))
    meta = ingest_vra(path, root, "2026-08", "official_local_file")
    assert meta["rejected_reasons"] == {"fora_do_periodo": 1, "sem_data": 1}
    total = (
        sample_vra([out_of_period, no_date, fractional]).count("\r\n") - 2
    )  # sem aviso e cabeçalho
    assert meta["rejected_rows"] == 2 and meta["rows"] + meta["rejected_rows"] == total
    ops = Store(root).read("operations")
    azu_n = [o for o in ops if o["airline"] == "AZU" and o["line_type"] == "N"]
    assert {o["line_type"] for o in ops} == {"N", "I"}
    assert all(
        o["scheduled_departure"].endswith("+00:00") for o in azu_n if o["scheduled_departure"]
    )
    cancelled = [o for o in azu_n if o["cancelled"] is True]
    assert len(cancelled) == 10 and all(o["delay_minutes"] is None for o in cancelled)
    assert any(o["delay_minutes"] == 20.0 for o in azu_n)  # fração de segundo lida


def test_ingest_is_idempotent(root):
    path = write(root, sample_vra())
    first = ingest_vra(path, root, "2026-08", "official_local_file")
    assert ingest_vra(path, root, "2026-08", "official_local_file") == {
        "already_ingested": True,
        "sha256": first["sha256"],
    }


def test_wrong_period_or_too_many_bad_rows_is_refused(root):
    path = write(root, sample_vra())
    with pytest.raises(ValueError, match="VRA recusado"):
        ingest_vra(path, root, "2026-07", "official_local_file")  # período errado: tudo rejeitado
    assert Store(root).read("operations") == []  # nada foi gravado


def test_unsupported_schema_is_refused(root):
    bad = NOTICE + '"Empresa";"Voo"\r\n"AZU";"1"\r\n' * 3
    with pytest.raises(ValueError, match="Schema VRA"):
        ingest_vra(write(root, bad), root, "2026-08", "official_local_file")


# ------------------------------------------------------------------ distribuição de atrasos


def delays_from(root, **kwargs):
    ingest_vra(write(root, sample_vra()), root, "2026-08", "official_local_file")
    return EmpiricalDelays.from_store(Store(root), **kwargs)


def test_empirical_delays_reflect_the_real_distribution(root):
    delays = delays_from(root)
    summary = delays.summary
    assert summary["airline"] == "AZU" and summary["line_type"] == "N"
    assert summary["periods"] == ["2026-08"] and summary["source"].startswith("VRA")
    realized = (
        400 + 300 + 1
    )  # REC + GRU + o voo antecipado; cancelados, internacional e GLO ficam fora
    assert summary["flights"] == realized
    assert summary["share_delay_ge_60"] == pytest.approx(20 / realized, abs=1e-4)
    assert summary["cancellation_rate"] == pytest.approx(10 / (realized + 10), abs=1e-4)
    assert min(delays.overall) == 0  # antecipado conta como zero


def test_airport_distribution_is_used_only_with_enough_flights(root):
    delays = delays_from(root, min_origin=250)
    assert (
        set(delays.by_origin) == {"REC", "GRU"}
        and delays.summary["airports_with_own_distribution"] == 2
    )
    rng = random.Random(1)
    assert all(delays.sample("GRU", rng) == 0 for _ in range(200))  # GRU nunca atrasa
    assert any(delays.sample("REC", rng) >= 60 for _ in range(400))  # REC tem 5% de atrasos longos
    assert 0 <= delays.sample("ZZZ", rng) <= 90  # aeroporto desconhecido: distribuição geral
    sparse = delays_from_fresh(root, min_origin=10_000)
    assert sparse.by_origin == {} and sparse.summary["airports_with_own_distribution"] == 0


def delays_from_fresh(root, **kwargs):
    return EmpiricalDelays.from_store(Store(root), **kwargs)


def test_sampling_is_deterministic(root):
    delays = delays_from(root)
    first = [delays.sample("REC", random.Random(7)) for _ in range(5)]
    assert first == [delays.sample("REC", random.Random(7)) for _ in range(5)]


def test_too_few_flights_gives_no_calibration(root):
    delays_from(root)
    assert EmpiricalDelays.from_store(Store(root), min_flights=5000) is None
    assert EmpiricalDelays.from_store(Store(root), airline="XYZ") is None


# ------------------------------------------------------------------ gerador e ponta a ponta


def table():
    return [
        {"origin": "REC", "destination": "GRU", "mean_fare": 800.0, "weight": 5000},
        {"origin": "GRU", "destination": "BSB", "mean_fare": 600.0, "weight": 3000},
    ]


def test_generator_replaces_only_the_delays(root):
    delays = delays_from(root)
    window = (datetime(2025, 10, 1).date(), datetime(2026, 9, 30).date())
    base_customers, base_trips = PublicDemandGenerator().generate(table(), 300, 42, *window)
    customers, trips = PublicDemandGenerator(delays).generate(table(), 300, 42, *window)
    assert customers == base_customers and len(trips) == len(base_trips)
    for a, b in zip(base_trips, trips):  # tudo igual, exceto o atraso
        assert (a.trip_id, a.customer_id, a.origin, a.flight_date, a.fare_amount) == (
            b.trip_id,
            b.customer_id,
            b.origin,
            b.flight_date,
            b.fare_amount,
        )
    share = sum(t.delay_minutes >= 60 for t in trips) / len(trips)
    assert 0.01 < share < 0.07  # perto da taxa real, e longe dos 40% antigos
    assert sum(t.delay_minutes >= 60 for t in base_trips) / len(base_trips) > 0.30
    assert trips == PublicDemandGenerator(delays).generate(table(), 300, 42, *window)[1]


FARES = (
    "nr_ano_referencia;nr_mes_referencia;sg_empresa_icao;sg_icao_origem;sg_icao_destino;"
    "nr_tarifa;nr_assentos\n2026;9;AZU;SBRF;SBGR;800,00;5000\n2026;9;AZU;SBGR;SBBR;600,00;3000\n"
)


def test_public_generation_uses_real_delays_when_the_vra_is_ingested(root):
    store = Store(root)
    write(root, FARES, "fares.csv")
    ingest_fares(root / "fares.csv", root, "2026-09")
    plain = generate(Settings(root), 200, 42, public=True)
    assert plain["calibration_scope"] == "route_mean_fares_and_route_demand"
    assert plain["delay_calibration"] is None and "VRA" not in plain["notes"]
    before = sum(t["delay_minutes"] >= 60 for t in store.read("trips")) / len(store.read("trips"))

    ingest_vra(write(root, sample_vra()), root, "2026-08", "official_local_file")
    manifest = generate(Settings(root), 200, 42, public=True)
    assert manifest["calibration_scope"] == "route_mean_fares_and_route_demand_and_delays"
    assert manifest["delay_calibration"]["share_delay_ge_60"] > 0
    assert "VRA" in manifest["notes"]
    trips = store.read("trips")
    after = sum(t["delay_minutes"] >= 60 for t in trips) / len(trips)
    assert before > 0.30 and after < 0.10
    incident = [f["incident_rate"] for f in store.read("features")]
    assert sum(incident) / len(incident) < 0.15


def test_lake_carries_line_type_rejections_and_delay_calibration(root):
    store = Store(root)
    write(root, FARES, "fares.csv")
    ingest_fares(root / "fares.csv", root, "2026-09")
    rejected = vra_row("AZU", "N", "SBRF", "SBGR", datetime(2026, 9, 1, 3, 0, 0), 0)
    ingest_vra(write(root, sample_vra([rejected])), root, "2026-08", "official_local_file")
    generate(Settings(root), 120, 42, public=True)
    summary = export_lake(root, store, root / "lake")
    assert summary["rows"]["silver.operations"] > 0 and summary["rows"]["bronze.sources"] == 2
    operations = pq.read_table(root / "lake/silver/operations.parquet").to_pylist()
    assert {o["line_type"] for o in operations} == {"N", "I"}
    sources = {
        s["dataset"]: s for s in pq.read_table(root / "lake/bronze/sources.parquet").to_pylist()
    }
    assert sources["vra"]["rejected_rows"] == 1 and sources["fares"]["rejected_rows"] is None
    manifest = pq.read_table(root / "lake/gold/manifest.parquet").to_pylist()[0]
    assert json.loads(manifest["delay_calibration"])["source"] == "VRA (ANAC)"
    assert collections.Counter(o["origin"] for o in operations)["REC"] > 0


# ------------------------------------------------------------------ nome das personas


@pytest.mark.parametrize(
    "incident, population, expected",
    [
        (
            0.61,
            0.40,
            "Baixo Volume Ativo com Atrasos Frequentes",
        ),  # base antiga (atrasos inventados)
        (0.19, 0.024, "Baixo Volume Ativo com Atrasos Acima da Média"),  # base realista
        (0.09, 0.024, "Baixo Volume Ativo"),  # abaixo de 10%
        (0.30, 0.40, "Baixo Volume Ativo"),  # abaixo da média da base antiga: nada a destacar
        (0.00, 0.00, "Baixo Volume Ativo"),
    ],
)
def test_delay_rule_works_for_old_and_realistic_delay_rates(incident, population, expected):
    name, text, traits = _name_cluster(-1.0, 20.0, incident, population)
    assert name == expected
    assert traits["delays"] is (expected != "Baixo Volume Ativo")
    assert (f"{incident:.0%} das viagens" in text) is traits["delays"]


def test_reimport_vra_with_different_period_is_refused(root):
    path = write(root, sample_vra())
    ingest_vra(path, root, "2026-08", "official_local_file")
    before = Store(root).read("operations")
    with pytest.raises(ValueError, match="Período solicitado"):
        ingest_vra(path, root, "2026-09", "official_local_file")
    assert Store(root).read("operations") == before


def test_prepare_repair_preserves_public_calibration(root):
    from azul_crm.pipeline.demo import prepare_demo

    ingest_fares(write(root, FARES, "fares.csv"), root, "2026-09")
    ingest_vra(write(root, sample_vra()), root, "2026-08", "official_local_file")
    original = generate(Settings(root), 400, 42, public=True)
    prepare_demo(Settings(root))
    path = root / "artifacts/churn.json"
    model = json.loads(path.read_text())
    model["gold_fingerprint"] = "stale"
    path.write_text(json.dumps(model))
    before = Store(root).read("trips")
    result = prepare_demo(Settings(root))
    assert "repair-models" in result["steps"]
    assert Store(root).read("manifest")[0] == original
    assert Store(root).read("trips") == before
