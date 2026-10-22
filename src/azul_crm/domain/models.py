"""Contratos canônicos imutáveis. Não dependem de FastAPI, Streamlit ou arquivos."""

from dataclasses import dataclass
from datetime import date
from math import isfinite


@dataclass(frozen=True)
class Customer:
    customer_id: str
    home_airport: str
    preferred_channel: str
    loyalty_tier: str
    is_synthetic: bool = True

    def __post_init__(self):
        if not self.customer_id or self.preferred_channel not in {"email", "app"}:
            raise ValueError("Cliente sem ID ou canal inválido")
        if (
            len(self.home_airport) != 3
            or not self.home_airport.isupper()
            or not self.home_airport.isalpha()
        ):
            raise ValueError("Aeroporto deve usar código IATA com três letras maiúsculas")


@dataclass(frozen=True)
class Trip:
    trip_id: str
    customer_id: str
    origin: str
    destination: str
    flight_date: date
    fare_amount: float
    delay_minutes: int

    def __post_init__(self):
        if not self.trip_id or not self.customer_id:
            raise ValueError("Viagem sem identificador")
        if not isfinite(self.fare_amount) or self.fare_amount < 0 or self.delay_minutes < 0:
            raise ValueError("Tarifa e atraso devem ser números não negativos")
        if any(
            len(code) != 3 or not code.isalpha() or not code.isupper()
            for code in (self.origin, self.destination)
        ):
            raise ValueError("Origem e destino devem ser códigos IATA")
        if type(self.delay_minutes) is not int:
            raise ValueError("Atraso deve ser inteiro")
        if self.origin == self.destination:
            raise ValueError("Origem e destino devem ser diferentes")


@dataclass(frozen=True)
class Features:
    customer_id: str
    spend: float
    frequency: int
    recency_days: int
    incident_rate: float
    observation_end: date


@dataclass(frozen=True)
class RiskEstimate:
    probability: float
    method: str
    drivers: tuple[str, ...]

    def __post_init__(self):
        if not 0 <= self.probability <= 1:
            raise ValueError("Risco deve estar entre zero e um")


@dataclass(frozen=True)
class Scores:
    customer_id: str
    value_score: float
    churn_risk: float
    priority_score: float
    estimated_value_at_risk: float
    segment: str
    drivers: tuple[str, ...]
    model_version: str
    evaluated_at: date


@dataclass(frozen=True)
class Evidence:
    document_id: str
    title: str
    text: str
    source: str
    version: str
    is_demo: bool


@dataclass(frozen=True)
class Action:
    code: str
    title: str
    reason: str


@dataclass(frozen=True)
class Offer:
    """Ideia comercial sugerida. Hipótese a validar; nunca entra no texto da mensagem."""

    code: str
    title: str
    description: str
    status: str
    requires: str


@dataclass(frozen=True)
class Recommendation:
    customer_id: str
    action: Action
    draft: str
    evidence: tuple[Evidence, ...]
    status: str = "DRAFT_REQUIRES_REVIEW"
    mode: str = "demo_template"
    offer: Offer | None = None
    channel: str | None = None
    persona: str | None = None
