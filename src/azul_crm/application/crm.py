from datetime import date

from azul_crm.application.features import FeatureBuilder
from azul_crm.domain.models import Customer, Scores, Trip
from azul_crm.domain.ports import ChurnPredictor, CustomerRepository, Segmenter
from azul_crm.domain.scoring import PriorityScorer, ValueScorer


class CustomerNotFound(Exception):
    pass


class CrmService:
    """Orquestra contratos canônicos; não conhece HTTP, CSV ou Streamlit."""

    def __init__(
        self,
        repository: CustomerRepository,
        features: FeatureBuilder,
        value: ValueScorer,
        churn: ChurnPredictor,
        segments: Segmenter,
        priority: PriorityScorer,
        start: date,
        end: date,
    ):
        self.repository = repository
        self.features = features
        self.value = value
        self.churn = churn
        self.segments = segments
        self.priority = priority
        self.start, self.end = start, end

    def customers(self) -> list[Customer]:
        return self.repository.list_customers()

    def customer(self, customer_id: str) -> Customer:
        customer = self.repository.get_customer(customer_id)
        if customer is None:
            raise CustomerNotFound(customer_id)
        return customer

    def trips(self, customer_id: str) -> list[Trip]:
        self.customer(customer_id)
        return self.repository.trips_for(customer_id)

    def scores(self, customer_id: str) -> Scores:
        self.customer(customer_id)
        features = self.features.build(customer_id, self.trips(customer_id), self.start, self.end)
        value = self.value.score(features)
        risk = self.churn.predict(features)
        return Scores(
            customer_id,
            value,
            risk.probability,
            self.priority.score(value, risk.probability),
            round(features.spend * risk.probability, 2),
            self.segments.classify(value, risk.probability),
            (f"Gasto observado: R$ {features.spend:.2f}", f"Frequência: {features.frequency}")
            + risk.drivers,
            "value_baseline_v1+" + risk.method,
            self.end,
        )

    def priorities(self, segment: str | None = None) -> list[Scores]:
        result = [self.scores(c.customer_id) for c in self.repository.list_customers()]
        return sorted(
            (s for s in result if segment is None or s.segment == segment),
            key=lambda s: (-s.priority_score, s.customer_id),
        )
