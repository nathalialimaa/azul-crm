"""Validação manual opcional: uma solicitação, com a mesma cota da interface web."""

import argparse
import json
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real", action="store_true", help="Autoriza uma chamada real ao Gemini")
    parser.add_argument("--kind", choices=["assistant", "draft"], default="assistant")
    args = parser.parse_args()
    if not args.real:
        parser.error("Use --real somente quando desejar consumir uma chamada da cota diária.")
    import os
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from fastapi.testclient import TestClient

    from web.api.index import app

    with TestClient(app) as client:
        login = client.post("/api/session", json={"password": os.getenv("CRM_APP_PASSWORD", "")})
        login.raise_for_status()
        if args.kind == "assistant":
            response = client.post(
                "/api/ask",
                json={
                    "question": "Explique em duas frases os sinais de risco deste cliente.",
                    "customer_id": "SYN-0077",
                },
            )
        else:
            response = client.post(
                "/api/drafts", json={"customer_id": "SYN-0077", "generate": True}
            )
        response.raise_for_status()
        result = response.json()
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "maximum_provider_calls": 1,
        "kind": args.kind,
        "mode": result.get("mode"),
        "notice": result.get("notice"),
        "passed": result.get("mode") in {"gemini_grounded", "gemini_grounded_draft"},
    }
    target = root / ".runtime/gemini-check.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
