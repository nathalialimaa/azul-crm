import collections
import shutil
from datetime import date
from pathlib import Path

import pytest

from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.demand import PublicDemandGenerator
from azul_crm.pipeline.extended import generate
from azul_crm.pipeline.public_data import import_airports, ingest_fares
from azul_crm.pipeline.stages import DemoSyntheticGenerator

REPO = Path(__file__).resolve().parents[1]
WINDOW = (date(2025, 10, 1), date(2026, 9, 30))


def code(prefix, i):
    """Código IATA válido (3 letras maiúsculas) e único: prefixo + duas letras."""
    return prefix + chr(65 + i // 26) + chr(65 + i % 26)


def routes(light=600, heavy=50):
    """Muitas rotas leves primeiro (em ordem), depois poucas rotas com quase toda a demanda."""
    light_routes = [
        {"origin": code("A", i), "destination": "XXX", "mean_fare": 500.0, "weight": 1}
        for i in range(light)
    ]
    heavy_routes = [
        {"origin": code("Z", i), "destination": "YYY", "mean_fare": 900.0, "weight": 1000}
        for i in range(heavy)
    ]
    return light_routes + heavy_routes


def home_counts(customers):
    return collections.Counter(c.home_airport[0] for c in customers)


def test_customers_follow_demand_instead_of_list_position():
    table = routes()
    old, _ = DemoSyntheticGenerator().generate(table, 300, 42, *WINDOW)
    new, _ = PublicDemandGenerator().generate(table, 300, 42, *WINDOW)
    assert (
        home_counts(old)["Z"] == 0
    )  # com mais rotas que clientes, o original só alcança as primeiras da lista
    assert home_counts(new)["Z"] / 300 > 0.9  # o novo segue o peso: 50.000 de 50.600 assentos


def test_distribution_matches_the_weights():
    table = [
        {"origin": "AAA", "destination": "BBB", "mean_fare": 500.0, "weight": 9000},
        {"origin": "CCC", "destination": "DDD", "mean_fare": 500.0, "weight": 1000},
    ]
    customers, _ = PublicDemandGenerator().generate(table, 1000, 42, *WINDOW)
    share = collections.Counter(c.home_airport for c in customers)["AAA"] / 1000
    assert 0.86 < share < 0.94


def test_generation_is_reproducible_and_seed_sensitive():
    table = routes()
    first = PublicDemandGenerator().generate(table, 100, 42, *WINDOW)
    assert first == PublicDemandGenerator().generate(table, 100, 42, *WINDOW)
    other = PublicDemandGenerator().generate(table, 100, 7, *WINDOW)
    assert [c.home_airport for c in first[0]] != [c.home_airport for c in other[0]]


@pytest.mark.parametrize("bad", [[], [{"origin": "AAA", "destination": "BBB", "mean_fare": 1}]])
def test_missing_demand_weights_are_rejected(bad):
    with pytest.raises(ValueError):
        PublicDemandGenerator().generate(bad, 10, 42, *WINDOW)
    zero = [{"origin": "AAA", "destination": "BBB", "mean_fare": 1, "weight": 0}]
    with pytest.raises(ValueError, match="peso"):
        PublicDemandGenerator().generate(zero, 10, 42, *WINDOW)


def test_public_generation_uses_real_demand_end_to_end(tmp_path, monkeypatch):
    for name in ["config", "data/fixtures", "data/knowledge"]:
        shutil.copytree(REPO / name, tmp_path / name)
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    store = Store(tmp_path)
    import_airports(REPO / "data/fixtures/airports_reference.csv", store)
    header = (
        "nr_ano_referencia;nr_mes_referencia;sg_empresa_icao;sg_icao_origem;"
        "sg_icao_destino;nr_tarifa;nr_assentos"
    )
    lines = ["2026;6;AZU;SBRF;SBGR;800,00;5000"]  # a rota dominante, em REC
    lines += [f"2026;6;AZU;SBGR;{d};600,00;10" for d in ["SBBR", "SBSV", "SBCF", "SBKP"]]
    path = tmp_path / "fares.csv"
    path.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")
    ingest_fares(path, tmp_path, "2026-06")

    manifest = generate(Settings(tmp_path), 200, 42, public=True)
    assert manifest["calibration_scope"] == "route_mean_fares_and_route_demand"
    assert manifest["calibrated_with_public_data"] is True
    homes = collections.Counter(c["home_airport"] for c in store.read("customers"))
    assert homes["REC"] / 200 > 0.9  # 5.000 de 5.040 assentos saem de REC
    fares = {t["fare_amount"] for t in store.read("trips") if t["origin"] == "REC"}
    assert fares and max(fares) < 800 * 1.5 + 1  # tarifas vêm da média real da rota, com variação
