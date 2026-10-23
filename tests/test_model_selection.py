import shutil
from pathlib import Path

import numpy as np
import pytest

from azul_crm.domain.models import Features
from azul_crm.domain.scoring import BaselineChurnPredictor
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.extended import generate
from azul_crm.pipeline.modeling import (
    CV_REPEATS,
    CV_SPLITS,
    MIN_T,
    baseline_risk,
    cross_validate,
    model_wins,
    train,
)

REPO = Path(__file__).resolve().parents[1]


def dataset(kind, seed, n=320):
    """Features no formato do modelo (gasto, frequência, recência, incidentes)."""
    rng = np.random.default_rng(seed)
    spend, freq = rng.gamma(3, 4000, n), rng.integers(2, 33, n).astype(float)
    recency, incident = rng.integers(0, 180, n).astype(float), rng.beta(1, 15, n)
    x = np.column_stack([spend, freq, recency, incident])

    def z(v):
        return (v - v.mean()) / v.std()

    if kind == "sinal_que_so_o_modelo_ve":
        logit = 1.6 * z(spend) - 1.0 * z(freq)
    elif kind == "regra_ja_e_a_verdade":
        logit = 1.5 * (0.6 * np.minimum(recency / 180, 1) + 0.25 * incident - 0.3) / 0.2
    else:
        logit = np.zeros(n)
    return x, (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)


def test_baseline_formula_matches_the_production_predictor():
    f = Features("C1", 5000.0, 12, 90, 0.2, None)
    row = np.array([[f.spend, f.frequency, f.recency_days, f.incident_rate]])
    assert baseline_risk(row)[0] == pytest.approx(
        BaselineChurnPredictor().predict(f).probability, abs=1e-4
    )


def test_model_is_adopted_only_when_it_has_a_real_advantage():
    wins = {
        kind: [model_wins(cross_validate(*dataset(kind, s), s)) for s in range(12)]
        for kind in ("sinal_que_so_o_modelo_ve", "regra_ja_e_a_verdade", "so_ruido")
    }
    assert all(wins["sinal_que_so_o_modelo_ve"])  # sinal que a regra não vê: modelo entra
    assert sum(wins["regra_ja_e_a_verdade"]) <= 1  # a regra já é a verdade: fica a regra
    assert sum(wins["so_ruido"]) <= 1  # ruído puro: fica a regra


def test_decision_needs_a_significant_gain_and_a_lower_brier():
    cv = {
        "auc_gain": {"t_statistic": MIN_T + 1},
        "model": {"brier_mean": 0.2},
        "baseline": {"brier_mean": 0.25},
    }
    assert model_wins(cv)
    assert not model_wins({**cv, "auc_gain": {"t_statistic": MIN_T - 0.5}})  # ganho dentro do ruído
    assert not model_wins({**cv, "model": {"brier_mean": 0.3}})  # AUC melhor, calibração pior


def test_cross_validation_report_has_the_expected_shape():
    cv = cross_validate(*dataset("so_ruido", 1), 1)
    assert set(cv) == {"model", "baseline", "auc_gain"}
    assert cv["auc_gain"]["std_error"] > 0 and abs(cv["auc_gain"]["t_statistic"]) < 5
    assert 0.3 < cv["model"]["roc_auc_mean"] < 0.7  # ruído: perto de 0,5


@pytest.fixture
def base(tmp_path, monkeypatch):
    for name in ["config", "data/fixtures", "data/knowledge"]:
        shutil.copytree(REPO / name, tmp_path / name)
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    generate(Settings(tmp_path), 300, 42)
    return tmp_path, Store(tmp_path)


def test_report_keeps_the_test_set_out_of_the_choice(base):
    root, store = base
    report = train(root, store, seed=42)
    cv, split = report["cross_validation"], report["split"]
    assert cv["customers"] == split["train"] + split["validation"]  # o teste não entra
    assert (cv["splits"], cv["repeats"]) == (CV_SPLITS, CV_REPEATS)
    assert "teste" in report["selection_rule"] and "t >" in report["selection_rule"]
    assert isinstance(report["validation_only_would_select"], bool)
    assert {"validation_model", "test_model", "test_baseline"} <= set(report)


def test_choice_does_not_flip_with_the_data_split(base):
    root, store = base
    choices = {train(root, store, seed=s)["selected"] for s in range(8)}
    assert len(choices) == 1  # a decisão não depende da divisão sorteada
