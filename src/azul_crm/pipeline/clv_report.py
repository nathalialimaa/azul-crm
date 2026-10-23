"""Grava e lê o relatório de CLV (``artifacts/clv_report.json``), no mesmo padrão da auditoria."""

import json

from azul_crm.application.value import clv_report
from azul_crm.pipeline.bias_audit import current_fingerprint


def write_clv_report(root, container, store) -> dict:
    report = clv_report(container)
    report["gold_fingerprint"] = current_fingerprint(store)
    report["segmenter"] = container.metadata.get("segmenter", "rules")
    report["risk_method"] = container.metadata.get("risk_method", "heuristic_not_calibrated")
    target = root / "artifacts"
    target.mkdir(exist_ok=True)
    (target / "clv_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def load_clv_report(root, store=None) -> dict:
    """``stale`` indica que a Gold mudou depois do relatório."""
    path = root / "artifacts" / "clv_report.json"
    if not path.exists():
        return {"available": False}
    report = json.loads(path.read_text(encoding="utf-8"))
    stale = store is not None and report.get("gold_fingerprint") != current_fingerprint(store)
    return {"available": True, "stale": stale, **report}
