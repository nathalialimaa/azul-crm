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
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from azul_crm.domain.models import RiskEstimate

NAMES = ["spend", "frequency", "recency_days", "incident_rate"]


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
    baseline = np.minimum(0.95, 0.1 + 0.6 * np.minimum(x[:, 2] / 180, 1) + 0.25 * x[:, 3])
    pv = model.predict_proba(scaler.transform(x[val_ids]))[:, 1]
    model_val = metrics(y[val_ids], pv)
    base_val = metrics(y[val_ids], baseline[val_ids])
    selected = model_val["roc_auc"] > base_val["roc_auc"] and model_val["brier"] < base_val["brier"]
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
        "selection_rule": "validation AUC greater AND Brier lower",
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
