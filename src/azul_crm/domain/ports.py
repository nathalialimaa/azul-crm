"""Portas pequenas: implementações podem mudar sem alterar os casos de uso."""

from typing import Protocol

from azul_crm.domain.models import (
    Action,
    Customer,
    Evidence,
    Features,
    RiskEstimate,
    Scores,
    Trip,
)


class CustomerRepository(Protocol):
    def list_customers(self) -> list[Customer]: ...
    def get_customer(self, customer_id: str) -> Customer | None: ...
    def trips_for(self, customer_id: str) -> list[Trip]: ...


class ChurnPredictor(Protocol):
    def predict(self, features: Features) -> RiskEstimate: ...


class Segmenter(Protocol):
    def classify(self, value: float, risk: float, features: Features | None = None) -> str: ...


class KnowledgeRetriever(Protocol):
    def retrieve(self, query: str) -> tuple[Evidence, ...]: ...


class MessageGenerator(Protocol):
    def draft(
        self, customer: Customer, scores: Scores, action: Action, evidence: tuple[Evidence, ...]
    ) -> str: ...
