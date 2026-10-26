# ruff: noqa: E402
"""Publica somente uma projeção sintética, sem banco bruto, segredos ou chamadas LLM."""

import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["CRM_LLM_PROVIDER"] = "local"
os.environ["CRM_MESSAGE_PROVIDER"] = "template"
os.environ["RAG_PROVIDER"] = "local"
os.environ["CRM_UI_MODE"] = "local"
from azul_crm.application.sentiment import analyze_csv
from frontend.gateway import Gateway


def main():
    g = Gateway()
    dashboard = g.dashboard()
    customers = {}
    for row in dashboard["rows"]:
        cid = row["customer_id"]
        detail = g.customer(cid)
        if detail["customer"]["is_synthetic"] is not True:
            raise ValueError("Exportação web aceita apenas clientes sintéticos")
        customers[cid] = {
            **detail,
            "loyalty": g.loyalty(cid),
            "explanation": g.explanation(cid),
            "recommendation": g.recommend(cid, False),
        }
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dashboard": dashboard,
        "customers": customers,
        "metadata": g.metadata(),
        "strategy": g.playbook(),
        "models": g.models(),
        "personas": g.personas(),
        "bias": g.bias(),
        "clv": g.clv(),
        "sentiment": analyze_csv((ROOT / "data/fixtures/reviews.csv").read_bytes()),
    }
    texts = {
        r["review_id"]: r["text"]
        for r in csv.DictReader((ROOT / "data/fixtures/reviews.csv").open(encoding="utf-8"))
    }
    for review in payload["sentiment"]["reviews"]:
        review["text"] = texts[review["review_id"]]
    for detail in customers.values():
        detail["recommendation"]["draft_id"] = None
    target = ROOT / "web/data/snapshot.json"
    target.write_text(
        json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":")),
        encoding="utf-8",
    )
    for source, dest in [
        ("src/azul_crm/infrastructure/gemini.py", "gemini.py"),
        ("src/azul_crm/application/sentiment.py", "sentiment.py"),
    ]:
        shutil.copyfile(ROOT / source, ROOT / "web/crm_runtime" / dest)
    shutil.copyfile(ROOT / "frontend/assets/manrope.ttf", ROOT / "web/public/assets/Manrope.ttf")
    shutil.copyfile(
        ROOT / "frontend/assets/OFL-Manrope.txt", ROOT / "web/public/assets/OFL-Manrope.txt"
    )
    print(
        json.dumps(
            {
                "customers": len(customers),
                "bytes": target.stat().st_size,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
