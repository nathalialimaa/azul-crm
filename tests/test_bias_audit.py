import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from azul_crm.api.main import create_app
from azul_crm.bootstrap import build_container
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.bias_audit import (
    ATTRIBUTES,
    FOUR_FIFTHS,
    build_records,
    load_report,
    region_of,
    run_audit,
    select_top,
    write_report,
)
from azul_crm.pipeline.extended import generate
from azul_crm.pipeline.personas import train_personas


def rec(i, persona, priority, airport="REC", channel="app", tier="T1", risk=0.5, churn=False):
    return {
        "customer_id": f"C{i:04d}",
        "persona": persona,
        "priority_score": priority,
        "churn_risk": risk,
        "churn_observed": churn,
        "home_airport": airport,
        "region": region_of(airport),
        "preferred_channel": channel,
        "tier": tier,
    }


def population(channel_penalty=0.0):
    """100 'Alto' (50 app / 50 email) e 100 'Baixo'. Penalidade reduz a prioridade do email."""
    rows = []
    for i in range(100):
        channel = "app" if i % 2 == 0 else "email"
        score = 90 - i * 0.1 - (channel_penalty if channel == "email" else 0)
        rows.append(rec(i, "Alto", score, channel=channel))
    for i in range(100, 200):
        rows.append(rec(i, "Baixo", 10 - (i - 100) * 0.01, channel="app" if i % 2 else "email"))
    return rows


def test_select_top_is_exact_and_deterministic():
    rows = [rec(i, "P", 50) for i in range(103)]  # empate total
    chosen = select_top(rows, 0.2)
    assert len(chosen) == 21  # ceil(0,2 * 103)
    assert chosen == select_top(list(reversed(rows)), 0.2)
    assert chosen == {f"C{i:04d}" for i in range(21)}  # desempate estável por id


def test_equal_treatment_is_ok():
    report = run_audit(population())
    channel = report["attributes"]["preferred_channel"]
    assert channel["verdict"] == "ok"
    assert channel["selection_ratio"] >= FOUR_FIFTHS
    assert report["synthetic_only"] is True
    assert set(report["attributes"]) == set(ATTRIBUTES)


def test_unequal_treatment_inside_same_persona_is_an_alert():
    report = run_audit(population(channel_penalty=30))
    channel = report["attributes"]["preferred_channel"]
    assert channel["verdict"] == "alerta"
    alto = next(w for w in channel["within_persona"] if w["persona"] == "Alto")
    assert alto["flag"] and alto["selection_ratio"] < FOUR_FIFTHS
    assert report["summary"]["alerts"] >= 1


def test_attribute_that_determines_persona_is_confounded_not_excused():
    rows = [rec(i, "Alto", 90 - i * 0.1, airport="VCP") for i in range(100)]
    rows += [rec(i, "Baixo", 10 - i * 0.01, airport="CNF") for i in range(100, 200)]
    airport = run_audit(rows)["attributes"]["home_airport"]
    assert airport["selection_flag"] is True
    assert airport["within_persona"] == []  # nenhum grupo divide persona
    assert airport["verdict"] == "confundido"
    assert airport["persona_association"]["relevant"] is True


def test_small_groups_are_skipped_not_compared():
    rows = population()
    for r in rows[:5]:
        r["tier"] = "RARO"
    tier = run_audit(rows)["attributes"]["tier"]
    assert [g["group"] for g in tier["groups"]] == ["T1"]
    assert tier["skipped_small_groups"] == [{"group": "RARO", "customers": 5}]
    assert tier["verdict"] == "amostra_insuficiente"


def test_calibration_and_recall_are_reported_per_group():
    rows = population()
    for r in rows:
        if r["preferred_channel"] == "email":
            r["churn_risk"], r["churn_observed"] = 0.9, False  # superestima o risco
        else:
            r["churn_risk"], r["churn_observed"] = 0.4, True
    channel = run_audit(rows)["attributes"]["preferred_channel"]
    gaps = {g["group"]: g["calibration_gap"] for g in channel["groups"]}
    assert gaps["email"] == pytest.approx(0.9) and gaps["app"] == pytest.approx(-0.6)
    assert channel["calibration_flag"] is True
    assert any(g["recall_among_churners"] is not None for g in channel["groups"])


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError):
        run_audit([])
    broken = population()
    broken[0].pop("region")
    with pytest.raises(ValueError, match="region"):
        run_audit(broken)


def test_region_mapping():
    assert region_of("REC") == "Nordeste"
    assert region_of("GRU") == "Sudeste"
    assert region_of("POA") == "Sul"
    assert region_of("BSB") == "Centro-Oeste"
    assert region_of("XXX") == "Outra"


@pytest.fixture
def base(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1]
    for name in ["config", "data/fixtures", "data/knowledge"]:
        shutil.copytree(source / name, tmp_path / name)
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    generate(Settings(tmp_path), 300, 42)
    store = Store(tmp_path)
    train_personas(tmp_path, store, seed=42, k=4)
    return tmp_path, store


def test_end_to_end_report_and_staleness(base):
    root, store = base
    assert load_report(root, store) == {"available": False}
    report = write_report(root, build_container(Settings(root)), store)
    assert report["segmenter"] == "kmeans_personas_v1"
    assert report["settings"]["customers"] == 300
    assert report["settings"]["selected_customers"] == 60
    loaded = load_report(root, store)
    assert loaded["available"] and loaded["stale"] is False
    stored = json.loads((root / "artifacts/bias_report.json").read_text(encoding="utf-8"))
    stored["gold_fingerprint"] = "0" * 64
    (root / "artifacts/bias_report.json").write_text(json.dumps(stored), encoding="utf-8")
    assert load_report(root, store)["stale"] is True


def test_regenerating_gold_discards_report(base):
    root, store = base
    write_report(root, build_container(Settings(root)), store)
    assert (root / "artifacts/bias_report.json").exists()
    generate(Settings(root), 300, 7)
    assert not (root / "artifacts/bias_report.json").exists()


def test_missing_outcomes_fail_clearly(base):
    root, store = base
    store.publish({"outcomes": []})
    with pytest.raises(ValueError, match="Desfechos ausentes"):
        build_records(build_container(Settings(root)), store)


def test_bias_endpoint(base):
    root, store = base
    with TestClient(create_app(build_container(Settings(root)))) as api:
        assert api.get("/api/v1/bias").json() == {"available": False}
        write_report(root, build_container(Settings(root)), store)
        body = api.get("/api/v1/bias").json()
        assert body["available"] and body["stale"] is False
        assert set(body["attributes"]) == set(ATTRIBUTES)


def test_small_samples_per_persona_are_not_called_confounded():
    # Dois aeroportos com a MESMA mistura de personas, mas só 10 clientes de cada persona por
    # aeroporto (abaixo do mínimo de 20): não há como comparar dentro da persona.
    rows, i = [], 0
    for persona in ["P1", "P2", "P3", "P4"]:
        for airport in ["AAA", "BBB"]:
            for _ in range(10):
                score = 90 - i * 0.01 if airport == "AAA" else 10 - i * 0.01  # AAA é favorecido
                rows.append(rec(i, persona, score, airport=airport))
                i += 1
    airport = run_audit(rows)["attributes"]["home_airport"]
    assert airport["selection_flag"] is True and airport["within_persona"] == []
    assert airport["persona_association"]["relevant"] is False  # a mistura é igual nos dois
    assert airport["verdict"] == "amostra_insuficiente"
