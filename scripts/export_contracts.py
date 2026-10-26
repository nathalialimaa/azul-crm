"""Execute da raiz, após gerar a Gold. Exporta contratos e exemplos da API real."""

import json
import os
from pathlib import Path

os.environ["CRM_LLM_PROVIDER"] = "local"
os.environ["CRM_MESSAGE_PROVIDER"] = "template"

from fastapi.testclient import TestClient

from azul_crm.api.main import create_app

root = Path(__file__).resolve().parents[1]
output = root / "docs/api"
output.mkdir(parents=True, exist_ok=True)
with TestClient(create_app()) as client:
    samples = {}
    for name, url in {
        "metadata": "/api/v1/metadata",
        "customers": "/api/v1/customers?limit=2",
        "detail": "/api/v1/customers/SYN-0001",
        "scores": "/api/v1/customers/SYN-0001/scores",
        "priorities": "/api/v1/retention/priorities?limit=2",
        "segments": "/api/v1/segments",
        "not_found": "/api/v1/customers/missing",
        "invalid_limit": "/api/v1/customers?limit=0",
    }.items():
        response = client.get(url)
        samples[name] = {
            "method": "GET",
            "path": url,
            "status": response.status_code,
            "body": response.json(),
        }
    body = {"customer_id": "SYN-0001"}
    response = client.post("/api/v1/agent/recommend", json=body)
    samples["recommendation"] = {
        "method": "POST",
        "path": "/api/v1/agent/recommend",
        "request": body,
        "status": response.status_code,
        "body": response.json(),
    }
    (output / "examples.json").write_text(
        json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "openapi.json").write_text(
        json.dumps(client.get("/openapi.json").json(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
print("Contratos exportados para docs/api")
