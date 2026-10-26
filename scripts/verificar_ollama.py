"""Diagnóstico opcional do Ollama real, sem instalar modelos ou alterar o .env.

python scripts/verificar_ollama.py
Retorna 0 somente após embeddings, busca e geração com citações válidas; 1 se falhar.
A validação de citações não prova correção semântica: revisão humana continua obrigatória.
"""
import json
import os
import sys
from datetime import datetime, timezone

import httpx

from azul_crm.infrastructure.rag import DocumentIndex
from azul_crm.infrastructure.settings import Settings


def check():
    settings = Settings.load()
    os.environ["RAG_PROVIDER"] = "ollama"
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "status": "failed"}
    try:
        response = httpx.get(base + "/api/tags", timeout=10)
        response.raise_for_status()
        result["available_models"] = [m["name"] for m in response.json()["models"]]
        index = DocumentIndex(settings.root)
        result["index"] = index.build()
        answer = index.answer("Qual a validade dos Pontos Azul?")
        if not answer["evidence"]:
            raise ValueError("Busca não recuperou evidências; geração não foi validada")
        result.update(status="ok", mode=answer["mode"], answer=answer["answer"],
                      evidence=answer["evidence"])
    except (httpx.HTTPError, ValueError, KeyError, TypeError, ImportError) as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["next_step"] = (
            "Inicie ollama serve, instale os modelos configurados e execute novamente. "
            "Mantenha RAG_PROVIDER=local no .env enquanto o diagnóstico não passar."
        )
    return result


if __name__ == "__main__":
    report = check()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(0 if report["status"] == "ok" else 1)
