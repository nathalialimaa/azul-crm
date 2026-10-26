import json
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from azul_crm.api.routes import get_container
from azul_crm.application.dashboard import overview, simulation, strategy
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
    confirmed_checklist: list[str] = Field(default_factory=list, max_length=20)


@router.post("/decisions")
def decide(body: Decision, c=Depends(get_container)):
    rec = c.recommendations.recommend(body.customer_id)
    if body.status == "APPROVED" and rec.action.code == "NO_ACTION":
        raise HTTPException(409, "Sem evidência: inclua e revise as fontes antes de aprovar.")
    if body.status == "APPROVED":
        missing = [i.code for i in rec.review_checklist if i.code not in body.confirmed_checklist]
        if missing:
            raise HTTPException(
                409, "Confirme o checklist de revisão antes de aprovar: " + ", ".join(missing)
            )
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


@router.get("/playbook")
def playbook(months: int = Query(12, ge=1, le=12), c=Depends(get_container)):
    return strategy(c, months)


@router.get("/lake")
def lake():
    from azul_crm.infrastructure.lake import load_dictionary

    return load_dictionary(Settings.load().root)


@router.get("/clv")
def clv():
    from azul_crm.pipeline.clv_report import load_clv_report

    root = Settings.load().root
    return load_clv_report(root, Store(root))


@router.get("/bias")
def bias():
    from azul_crm.pipeline.bias_audit import load_report

    root = Settings.load().root
    return load_report(root, Store(root))


@router.get("/models")
def models():
    path = Settings.load().root / "artifacts/metrics.json"
    return (
        json.loads(path.read_text())
        if path.exists()
        else {"selected": "heuristic", "trained": False}
    )


class ReviewInput(BaseModel):
    review_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=4000)
    source_url: str = Field("", max_length=2000)
    is_synthetic: bool = Field(strict=True)


class SentimentRequest(BaseModel):
    reviews: list[ReviewInput] = Field(min_length=1, max_length=1000)


@router.post("/sentiment/analyze")
def sentiment(body: SentimentRequest):
    from azul_crm.application.sentiment import analyze_reviews

    try:
        return analyze_reviews([r.model_dump() for r in body.reviews])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/customers/{customer_id}/explanation")
def explanation(customer_id: str, c=Depends(get_container)):
    from azul_crm.application.explanations import explain_customer

    return explain_customer(c, Settings.load().root, customer_id)
