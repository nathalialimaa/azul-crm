from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class CustomerResponse(ApiModel):
    customer_id: str
    home_airport: str
    preferred_channel: str
    loyalty_tier: str
    is_synthetic: bool


class TripResponse(ApiModel):
    trip_id: str
    customer_id: str
    origin: str
    destination: str
    flight_date: date
    fare_amount: float = Field(ge=0)
    delay_minutes: int = Field(ge=0)


class ScoresResponse(ApiModel):
    customer_id: str
    value_score: float = Field(ge=0, le=100)
    churn_risk: float = Field(ge=0, le=1)
    priority_score: float = Field(ge=0, le=100)
    estimated_value_at_risk: float = Field(ge=0)
    segment: str
    drivers: list[str]
    model_version: str
    evaluated_at: date


class DetailResponse(ApiModel):
    customer: CustomerResponse
    trips: list[TripResponse]
    scores: ScoresResponse


class EvidenceResponse(ApiModel):
    document_id: str
    title: str
    text: str
    source: str
    version: str
    is_demo: bool


class ActionResponse(ApiModel):
    code: str
    title: str
    reason: str


class OfferResponse(ApiModel):
    code: str
    title: str
    description: str
    status: Literal["hypothesis_unverified", "verified"]
    requires: str


class RecommendationResponse(ApiModel):
    customer_id: str
    action: ActionResponse
    draft: str
    evidence: list[EvidenceResponse]
    status: Literal["DRAFT_REQUIRES_REVIEW"]
    mode: Literal["demo_template", "playbook_template"]
    offer: OfferResponse | None = None
    channel: str | None = None
    persona: str | None = None


class RecommendationRequest(ApiModel):
    customer_id: str = Field(min_length=1, max_length=80)


class CustomerPage(ApiModel):
    items: list[CustomerResponse]
    total: int
    offset: int
    limit: int
