import json
import math
import shutil
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from azul_crm.api.main import create_app
from azul_crm.application.dashboard import overview, simulation, strategy
from azul_crm.application.value import (
    SENSITIVITY_DISCOUNTS,
    SENSITIVITY_MARGINS,
    clv_report,
    customer_values,
    policy_of,
)
from azul_crm.bootstrap import build_container
from azul_crm.domain.clv import ClvPolicy, concentration, estimate, high_value_ids, top_count
from azul_crm.infrastructure.lake import export_lake
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.clv_report import load_clv_report, write_clv_report
from azul_crm.pipeline.demo import prepare_demo
from azul_crm.pipeline.extended import generate

REPO = Path(__file__).resolve().parents[1]
N = 300


def copy_project(root):
    for name in ["config", "data/fixtures", "data/knowledge"]:
        shutil.copytree(REPO / name, root / name)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    patch = pytest.MonkeyPatch()
    root = tmp_path_factory.mktemp("clv")
    copy_project(root)
    for key, value in {
        "CRM_PROJECT_ROOT": str(root),
        "CRM_STORAGE": "sqlite",
        "RAG_PROVIDER": "local",
    }.items():
        patch.setenv(key, value)
    prepare_demo(Settings(root), customers=N)
    yield root, Store(root), build_container(Settings(root))
    patch.undo()


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    """Base própria para testes que alteram arquivos."""
    copy_project(tmp_path)
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    prepare_demo(Settings(tmp_path), customers=120)
    return tmp_path, Store(tmp_path)


# ------------------------------------------------------------------ fórmulas e política


@pytest.mark.parametrize(
    "kwargs",
    [
        {"margin": 0},
        {"margin": 1.5},
        {"discount_rate": -0.1},
        {"discount_rate": 1},
        {"top_share": 0},
        {"top_share": 1},
        {"horizon_months": 6},
    ],
)
def test_invalid_assumptions_are_rejected(kwargs):
    with pytest.raises(ValueError):
        ClvPolicy(**kwargs)


def test_estimate_formula():
    policy = ClvPolicy(margin=0.15, discount_rate=0.10)
    value = estimate(10000, 0.4, policy)
    potential = 10000 * 0.15 / math.sqrt(1.10)
    assert value.potential == pytest.approx(potential)
    assert value.expected == pytest.approx(potential * 0.6)
    assert value.at_risk == pytest.approx(potential * 0.4)
    assert value.expected + value.at_risk == pytest.approx(value.potential)


def test_estimate_moves_in_the_right_direction():
    base = ClvPolicy()
    low, high = estimate(10000, 0.2, base), estimate(10000, 0.8, base)
    assert high.expected < low.expected and high.at_risk > low.at_risk
    assert high.potential == pytest.approx(low.potential)  # o risco não muda o potencial
    assert estimate(20000, 0.2, base).potential == pytest.approx(2 * low.potential)
    assert estimate(10000, 0.2, ClvPolicy(margin=0.30)).potential == pytest.approx(
        2 * low.potential
    )
    assert estimate(10000, 0.2, ClvPolicy(discount_rate=0.20)).potential < low.potential
    assert estimate(10000, 0.0, base).expected == pytest.approx(low.potential)
    assert estimate(10000, 1.0, base).expected == 0


@pytest.mark.parametrize("spend, risk", [(-1, 0.5), (100, 1.2), (100, -0.1)])
def test_estimate_rejects_invalid_inputs(spend, risk):
    with pytest.raises(ValueError):
        estimate(spend, risk, ClvPolicy())


def test_top_count_and_high_value_selection():
    assert [top_count(n, 0.2) for n in (0, 1, 5, 10, 103)] == [0, 1, 1, 2, 21]
    values = {"a": 100.0, "b": 50.0, "c": 50.0, "d": 10.0, "e": 1.0}
    assert high_value_ids(values, 0.4) == {"a", "b"}  # empate entre b e c: vence o menor id
    assert high_value_ids(dict(reversed(list(values.items()))), 0.4) == {"a", "b"}
    assert high_value_ids({}, 0.2) == set()


def test_concentration_curve():
    assert concentration([100, 50, 50, 10, 1], 0.4) == pytest.approx(150 / 211)
    assert concentration([5, 5, 5, 5], 0.25) == pytest.approx(
        0.25
    )  # base uniforme: sem concentração
    assert concentration([], 0.2) == 0 and concentration([0, 0], 0.5) == 0


def test_policy_comes_from_config_and_old_configs_still_work(tmp_path):
    shutil.copytree(REPO / "config", tmp_path / "config")
    assert Settings(tmp_path).clv_policy() == ClvPolicy(0.15, 0.10, 0.20)
    path = tmp_path / "config/settings.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text[: text.index("[clv]")] + text[text.index("[windows]") :], encoding="utf-8")
    assert Settings(tmp_path).clv_policy() == ClvPolicy()  # sem [clv]: valores padrão


# ------------------------------------------------------------------ carteira


def test_high_value_is_a_percentile_of_potential_value(world):
    _, _, container = world
    rows = customer_values(container)
    top = [r for r in rows if r["is_high_value"]]
    rest = [r for r in rows if not r["is_high_value"]]
    assert len(rows) == N and len(top) == math.ceil(0.2 * N)
    assert min(r["potential_value_12m"] for r in top) >= max(r["potential_value_12m"] for r in rest)
    assert len({r["customer_id"] for r in rows}) == N
    for r in rows:
        assert r["clv_12m"] == pytest.approx(
            r["potential_value_12m"] * (1 - r["churn_risk"]), abs=0.02
        )
        assert r["clv_12m"] + r["clv_at_risk"] == pytest.approx(r["potential_value_12m"], abs=0.02)


def test_margin_and_discount_change_the_size_not_the_ranking(world):
    _, _, container = world
    base = {r["customer_id"] for r in customer_values(container) if r["is_high_value"]}
    other_policy = ClvPolicy(margin=0.05, discount_rate=0.16)
    other = customer_values(container, other_policy)
    assert {r["customer_id"] for r in other if r["is_high_value"]} == base
    assert sum(r["clv_12m"] for r in other) < sum(r["clv_12m"] for r in customer_values(container))


def test_report_is_consistent(world):
    _, _, container = world
    report = clv_report(container)
    summary = report["summary"]
    assert summary["customers"] == N and len(report["customers"]) == N
    assert sum(p["customers"] for p in report["by_persona"]) == N
    assert (
        sum(p["high_value_customers"] for p in report["by_persona"])
        == summary["high_value_customers"]
    )
    shares = [c["value_share"] for c in report["concentration"]]
    assert shares == sorted(shares) and 0.2 < shares[1] <= 1  # há concentração de valor
    assert summary["top_value_share"] == shares[1]
    assert summary["total_clv_12m"] + summary["total_clv_at_risk"] == pytest.approx(
        summary["total_potential_12m"], abs=1
    )
    top = [r for r in report["customers"] if r["is_high_value"]]
    at_risk = [r for r in top if r["churn_risk"] >= summary["risk_threshold"]]
    assert summary["high_value_at_risk_customers"] == len(at_risk)
    assert summary["cutoff_potential_12m"] == min(r["potential_value_12m"] for r in top)
    assert {c["component"] for c in report["definition"]["components"]} == {
        "Valor monetário",
        "Frequência",
        "Recência",
        "Potencial futuro",
    }
    assert report["assumptions"]["status"].startswith("hipóteses")


def test_sensitivity_grid_is_monotonic_and_matches_the_formula(world):
    _, _, container = world
    report = clv_report(container)
    grid = {(x["margin"], x["discount_rate"]): x for x in report["sensitivity"]}
    assert len(grid) == len(SENSITIVITY_MARGINS) * len(SENSITIVITY_DISCOUNTS)
    for d in SENSITIVITY_DISCOUNTS:
        totals = [grid[(m, d)]["total_clv_12m"] for m in SENSITIVITY_MARGINS]
        assert totals == sorted(totals)  # mais margem, mais valor
    for m in SENSITIVITY_MARGINS:
        totals = [grid[(m, d)]["total_clv_12m"] for d in SENSITIVITY_DISCOUNTS]
        assert totals == sorted(totals, reverse=True)  # mais desconto, menos valor
    alt = ClvPolicy(margin=0.15, discount_rate=0.12)
    expected = sum(
        estimate(r["annual_spend"], r["churn_risk"], alt).expected for r in report["customers"]
    )
    assert grid[(0.15, 0.12)]["total_clv_12m"] == pytest.approx(expected, abs=0.05)


# ------------------------------------------------------------------ painel, cenário e API


def test_overview_uses_the_new_definition_and_keeps_old_fields(world):
    _, _, container = world
    data = overview(container, 12)
    kpis, rows = data["kpis"], data["rows"]
    assert kpis["high_value"] == math.ceil(0.2 * N)
    assert kpis["clv_12m"] == pytest.approx(sum(r["clv_12m"] for r in rows), abs=0.05)
    assert kpis["high_value_cutoff"] == clv_report(container)["summary"]["cutoff_potential_12m"]
    assert {"clv_12m_proxy", "weighted_value_at_risk"} <= set(rows[0]) and "clv_12m_proxy" in kpis
    risky = [r for r in rows if r["is_high_value"] and r["churn_risk"] >= 0.6]
    assert kpis["high_value_at_risk"] == len(risky)


def test_filters_cut_the_portfolio_but_not_who_is_high_value(world):
    _, _, container = world
    full = {r["customer_id"]: r for r in overview(container, 12)["rows"]}
    short = {r["customer_id"]: r for r in overview(container, 3)["rows"]}
    assert short and set(short) <= set(full)
    for cid, row in short.items():
        assert row["is_high_value"] == full[cid]["is_high_value"]
        assert row["clv_12m"] == full[cid]["clv_12m"]
    persona = next(iter({r["segment"] for r in full.values()}))
    cut = overview(container, 12, segment=persona)
    assert cut["kpis"]["high_value"] == sum(
        r["is_high_value"] for r in full.values() if r["segment"] == persona
    )


def test_scenario_and_strategy_use_clv_at_risk(world):
    _, _, container = world
    rows = overview(container, 12)["rows"]
    result = simulation(rows, 0, 1.0)
    assert result["value_at_risk"] == pytest.approx(sum(r["clv_at_risk"] for r in rows), abs=0.05)
    plan = strategy(container, 12)
    for row in plan["rows"]:
        members = [r for r in rows if r["segment"] == row["persona"]]
        assert row["value_at_risk"] == pytest.approx(
            sum(m["clv_at_risk"] for m in members), abs=0.05
        )
        assert row["net"] == pytest.approx(row["protected_value"] - row["cost"], abs=0.02)


def test_api_exposes_the_report_and_the_new_kpis(world):
    root, store, container = world
    with TestClient(create_app(container)) as api:
        body = api.get("/api/v1/clv").json()
        assert body["available"] and body["stale"] is False and body["summary"]["customers"] == N
        kpis = api.get("/api/v1/dashboard").json()["kpis"]
        assert kpis["high_value"] == math.ceil(0.2 * N) and kpis["high_value_cutoff"] > 0
    assert policy_of(container) == Settings(root).clv_policy()


def test_report_staleness_and_cleanup(fresh):
    root, store = fresh
    assert (root / "artifacts/clv_report.json").exists()  # o prepare já gera
    assert load_clv_report(root, store)["stale"] is False
    path = root / "artifacts/clv_report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["gold_fingerprint"] = "0" * 64
    path.write_text(json.dumps(report), encoding="utf-8")
    assert load_clv_report(root, store)["stale"] is True
    write_clv_report(root, build_container(Settings(root)), store)
    assert load_clv_report(root, store)["stale"] is False
    generate(Settings(root), 120, 7)  # base nova apaga o relatório da anterior
    assert load_clv_report(root, store) == {"available": False}


def test_lake_publishes_the_assumptions_and_per_customer_value(fresh):
    root, store = fresh
    summary = export_lake(root, store, root / "lake")
    assert (
        summary["rows"]["gold.customer_value"] == 120
        and summary["rows"]["gold.clv_assumptions"] == 1
    )
    value = pq.read_table(root / "lake/gold/customer_value.parquet")
    assert value.schema.field("is_high_value").type == pa.bool_()
    assumptions = pq.read_table(root / "lake/gold/clv_assumptions.parquet").to_pylist()[0]
    assert assumptions["margin"] == 0.15 and assumptions["top_share"] == 0.20
    assert assumptions["high_value_customers"] == math.ceil(0.2 * 120)
    assert 0.2 < assumptions["top_value_share"] <= 1


def test_cli_clv_report(fresh, monkeypatch, capsys):
    from azul_crm import cli

    monkeypatch.setattr(sys, "argv", ["azul-crm", "clv-report"])
    cli.main()
    out = json.loads(capsys.readouterr().out)
    assert out["method"] == "clv_margin_discounted_v1" and out["summary"]["customers"] == 120
