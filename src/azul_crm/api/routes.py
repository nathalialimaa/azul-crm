from fastapi import APIRouter, Depends, Query, Request

from azul_crm.api.schemas import (
    CustomerPage,
    DetailResponse,
    RecommendationRequest,
    RecommendationResponse,
    ScoresResponse,
)
from azul_crm.bootstrap import Container

router = APIRouter(prefix="/api/v1")


def get_container(request: Request) -> Container:
    return request.app.state.container


@router.get("/metadata")
def metadata(c: Container = Depends(get_container)):
    return {**c.metadata, "risk_method": "heuristic_not_calibrated", "agent_mode": "demo_template"}


@router.get("/customers", response_model=CustomerPage)
def customers(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    c: Container = Depends(get_container),
):
    rows = c.crm.customers()
    return {
        "items": rows[offset : offset + limit],
        "total": len(rows),
        "offset": offset,
        "limit": limit,
    }


@router.get("/customers/{customer_id}", response_model=DetailResponse)
def customer(customer_id: str, c: Container = Depends(get_container)):
    return {
        "customer": c.crm.customer(customer_id),
        "trips": c.crm.trips(customer_id),
        "scores": c.crm.scores(customer_id),
    }


@router.get("/customers/{customer_id}/scores", response_model=ScoresResponse)
def scores(customer_id: str, c: Container = Depends(get_container)):
    return c.crm.scores(customer_id)


@router.get("/customers/{customer_id}/recommendations", response_model=RecommendationResponse)
def recommendations(customer_id: str, c: Container = Depends(get_container)):
    return c.recommendations.recommend(customer_id)


@router.get("/retention/priorities", response_model=list[ScoresResponse])
def priorities(
    segment: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    c: Container = Depends(get_container),
):
    return c.crm.priorities(segment)[:limit]


@router.get("/segments")
def segments(c: Container = Depends(get_container)):
    counts: dict[str, int] = {}
    for score in c.crm.priorities():
        counts[score.segment] = counts.get(score.segment, 0) + 1
    return [{"segment": name, "count": count} for name, count in sorted(counts.items())]


@router.post("/agent/recommend", response_model=RecommendationResponse)
def recommend(body: RecommendationRequest, c: Container = Depends(get_container)):
    return c.recommendations.recommend(body.customer_id)
