import json
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from azul_crm.api.routes import get_container
from azul_crm.application.dashboard import overview, simulation
from azul_crm.infrastructure.rag import DocumentIndex
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store

router = APIRouter(prefix="/api/v1")


@router.get("/dashboard")
def dashboard(
    months: int = Query(12, ge=1, le=12),
    segment: str | None = None,
    route: str | None = None,
    c=Depends(get_container),
):
    return overview(c, months, segment, route)


class SimulationRequest(BaseModel):
    cost_per_customer: float = Field(10, ge=0, le=100000, allow_inf_nan=False)
    assumed_retention: float = Field(0.1, ge=0, le=1, allow_inf_nan=False)
    months: int = Field(12, ge=1, le=12)
    segment: str | None = None
    route: str | None = None


@router.post("/simulations")
def simulate(body: SimulationRequest, c=Depends(get_container)):
    return simulation(
        overview(c, body.months, body.segment, body.route)["rows"],
        body.cost_per_customer,
        body.assumed_retention,
    )


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    customer_id: str | None = None


@router.post("/agent/ask")
def ask(body: Question, c=Depends(get_container)):
    if body.customer_id:
        scores = c.crm.scores(body.customer_id)
        if any(w in body.question.lower() for w in ["risco", "prioriz", "valor", "fator"]):
            return {
                "answer": "\n".join(scores.drivers) + "\nVersão: " + scores.model_version,
                "evidence": [],
                "mode": "structured_customer_facts",
            }
    try:
        return DocumentIndex(Settings.load().root).answer(body.question)
    except (ValueError, httpx.HTTPError, KeyError) as exc:
        raise HTTPException(
            503,
            "Assistente indisponível ou resposta sem referências válidas. Confira índice/provedor.",
        ) from exc


class Decision(BaseModel):
    customer_id: str
    status: str = Field(pattern="^(APPROVED|REJECTED)$")
    note: str = Field("", max_length=1000)


@router.post("/decisions")
def decide(body: Decision, c=Depends(get_container)):
    rec = c.recommendations.recommend(body.customer_id)
    if body.status == "APPROVED" and rec.action.code == "NO_ACTION":
        raise HTTPException(409, "Sem evidência: inclua e revise as fontes antes de aprovar.")
    from dataclasses import asdict

    row = {
        "id": str(uuid4()),
        **body.model_dump(),
        "recommendation": asdict(rec),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sent": False,
    }
    Store(Settings.load().root).publish({"decisions": [(row["id"], row)]}, replace=False)
    return row


@router.get("/customers/{customer_id}/loyalty")
def loyalty(customer_id: str, c=Depends(get_container)):
    c.crm.customer(customer_id)
    return next(
        (r for r in Store(Settings.load().root).read("loyalty") if r["customer_id"] == customer_id),
        {},
    )


@router.get("/personas")
def personas():
    path = Settings.load().root / "artifacts/personas.json"
    if not path.exists():
        return {"trained": False, "method": "rules"}
    artifact = json.loads(path.read_text(encoding="utf-8"))
    hidden = {"centroids", "scaler_mean", "scaler_scale", "clip_low", "clip_high"}
    return {"trained": True, **{k: v for k, v in artifact.items() if k not in hidden}}


@router.get("/models")
def models():
    path = Settings.load().root / "artifacts/metrics.json"
    return (
        json.loads(path.read_text())
        if path.exists()
        else {"selected": "heuristic", "trained": False}
    )
