"""Treino demonstrativo, seleção em validação e avaliação em teste intocado."""

import hashlib
import json
import math
import os

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler

from azul_crm.domain.models import RiskEstimate

NAMES = ["spend", "frequency", "recency_days", "incident_rate"]

# A escolha entre modelo e regra usa validação cruzada em treino + validação (320 clientes), não só
# os 80 da validação: com tão poucos clientes a decisão virava de acordo com a divisão sorteada.
CV_SPLITS = 5
CV_REPEATS = 3
MIN_T = 1.65  # o ganho de AUC precisa ser distinguível de ruído (teste unilateral a 5%)


def baseline_risk(x):
    """Índice heurístico (mesma fórmula de ``BaselineChurnPredictor``) sobre a matriz de features."""
    return np.minimum(0.95, 0.1 + 0.6 * np.minimum(x[:, 2] / 180, 1) + 0.25 * x[:, 3])


def cross_validate(x, y, seed):
    """Média e desvio de AUC e Brier de modelo e regra nas mesmas dobras."""
    folds = RepeatedStratifiedKFold(n_splits=CV_SPLITS, n_repeats=CV_REPEATS, random_state=seed)
    got = {"model": {"auc": [], "brier": []}, "baseline": {"auc": [], "brier": []}}
    for fit, test in folds.split(x, y):
        scaler = StandardScaler().fit(x[fit])
        clf = LogisticRegression(random_state=seed, max_iter=1000).fit(
            scaler.transform(x[fit]), y[fit]
        )
        for name, p in (
            ("model", clf.predict_proba(scaler.transform(x[test]))[:, 1]),
            ("baseline", baseline_risk(x[test])),
        ):
            got[name]["auc"].append(roc_auc_score(y[test], p))
            got[name]["brier"].append(brier_score_loss(y[test], p))
    summary = {
        name: {
            "roc_auc_mean": float(np.mean(v["auc"])),
            "roc_auc_std": float(np.std(v["auc"])),
            "brier_mean": float(np.mean(v["brier"])),
        }
        for name, v in got.items()
    }
    # Teste t pareado por dobra, com a correção de Nadeau e Bengio: as dobras repetidas compartilham
    # dados, então o erro-padrão simples seria otimista demais.
    gains = np.array(got["model"]["auc"]) - np.array(got["baseline"]["auc"])
    ratio = 1 / (CV_SPLITS - 1)  # tamanho do teste sobre o do treino em cada dobra
    variance = float(np.var(gains, ddof=1)) * (1 / len(gains) + ratio)
    error = math.sqrt(variance)
    summary["auc_gain"] = {
        "mean": float(np.mean(gains)),
        "std_error": error,
        "t_statistic": float(np.mean(gains) / error) if error > 0 else 0.0,
    }
    return summary


def model_wins(cv) -> bool:
    """O modelo só substitui a regra com ganho de AUC estatisticamente distinguível e Brier menor."""
    return bool(
        cv["auc_gain"]["t_statistic"] > MIN_T
        and cv["model"]["brier_mean"] < cv["baseline"]["brier_mean"]
    )


class LogisticPredictor:
    def __init__(self, artifact):
        self.a = artifact

    def predict(self, f):
        values = np.array([getattr(f, n) for n in NAMES])
        contributions = (values - self.a["mean"]) / np.array(self.a["scale"]) * self.a["coef"]
        logit = float(sum(contributions) + self.a["intercept"])
        risk = 1 / (1 + math.exp(-max(-40, min(40, logit))))
        drivers = tuple(
            f"{NAMES[i]}: contribuição {contributions[i]:+.3f} em log-odds"
            for i in np.argsort(-abs(contributions))
        )
        return RiskEstimate(round(risk, 4), "logistic_synthetic_v2", drivers)


def metrics(y, p):
    binary = np.array(p) >= 0.5
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "precision": float(precision_score(y, binary, zero_division=0)),
        "recall": float(recall_score(y, binary, zero_division=0)),
        "confusion_matrix": confusion_matrix(y, binary).tolist(),
    }


def train(root, store, seed=42):
    feats = sorted(store.read("features"), key=lambda x: x["customer_id"])
    outcomes = {x["customer_id"]: x for x in store.read("outcomes")}
    if len(feats) < 100:
        raise ValueError("Gere pelo menos 100 clientes para treino demonstrativo")
    x = np.array([[f[n] for n in NAMES] for f in feats])
    y = np.array([outcomes[f["customer_id"]]["churn"] for f in feats])
    ids = np.arange(len(y))
    train_ids, test_ids = train_test_split(ids, test_size=0.2, random_state=seed, stratify=y)
    train_ids, val_ids = train_test_split(
        train_ids, test_size=0.25, random_state=seed, stratify=y[train_ids]
    )
    scaler = StandardScaler().fit(x[train_ids])
    model = LogisticRegression(random_state=seed, max_iter=1000).fit(
        scaler.transform(x[train_ids]), y[train_ids]
    )
    baseline = baseline_risk(x)
    pv = model.predict_proba(scaler.transform(x[val_ids]))[:, 1]
    model_val = metrics(y[val_ids], pv)
    base_val = metrics(y[val_ids], baseline[val_ids])
    validation_only = (
        model_val["roc_auc"] > base_val["roc_auc"] and model_val["brier"] < base_val["brier"]
    )
    development = np.concatenate([train_ids, val_ids])
    cv = cross_validate(x[development], y[development], seed)
    selected = model_wins(cv)
    pt = model.predict_proba(scaler.transform(x[test_ids]))[:, 1]
    report = {
        "synthetic_only": True,
        "seed": seed,
        "features": NAMES,
        "split": {"train": len(train_ids), "validation": len(val_ids), "test": len(test_ids)},
        "validation_model": model_val,
        "validation_baseline": base_val,
        "test_model": metrics(y[test_ids], pt),
        "test_baseline": metrics(y[test_ids], baseline[test_ids]),
        "selected": "logistic" if selected else "heuristic",
        "cross_validation": {
            "splits": CV_SPLITS,
            "repeats": CV_REPEATS,
            "customers": int(len(development)),
            "min_t_statistic": MIN_T,
            **cv,
        },
        "validation_only_would_select": bool(validation_only),
        "selection_rule": (
            f"validação cruzada {CV_SPLITS}x{CV_REPEATS} em treino+validação: ganho de AUC com "
            f"t > {MIN_T} (teste pareado corrigido) E Brier menor. O teste não participa da escolha."
        ),
        "limitation": "Desfechos simulados. Não comprova previsão de churn real.",
    }
    report["leakage_warning"] = report["test_model"]["roc_auc"] > 0.95
    # Uma métrica suspeita bloqueia promoção automática.
    if report["leakage_warning"]:
        report["selected"] = "heuristic"
    artifact = {
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coef": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "features": NAMES,
        "report": report,
        "gold_fingerprint": hashlib.sha256(json.dumps(feats, sort_keys=True).encode()).hexdigest(),
    }
    path = root / "artifacts"
    path.mkdir(exist_ok=True)
    (path / "churn.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    (path / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if os.getenv("MLFLOW_ENABLED", "false").lower() == "true":
        import mlflow

        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
        mlflow.set_experiment("azul-crm-synthetic")
        with mlflow.start_run():
            mlflow.log_params({"seed": seed, "data": "synthetic", "features": ",".join(NAMES)})
            mlflow.log_metrics(
                {k: v for k, v in report["test_model"].items() if isinstance(v, float)}
            )
            mlflow.log_artifact(str(path / "churn.json"))
            mlflow.log_artifact(str(path / "metrics.json"))
    return report
