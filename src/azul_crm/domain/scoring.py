"""Políticas de demonstração, parametrizadas e sem dependências de infraestrutura."""

from dataclasses import dataclass
from math import isfinite

from azul_crm.domain.models import Features, RiskEstimate


@dataclass(frozen=True)
class ScoringPolicy:
    spend_weight: float = 0.5
    frequency_weight: float = 0.3
    recency_weight: float = 0.2
    spend_reference: float = 18000
    frequency_reference: int = 24
    recency_reference: int = 180
    high_value_threshold: float = 70
    high_risk_threshold: float = 0.6

    def __post_init__(self):
        weights = (self.spend_weight, self.frequency_weight, self.recency_weight)
        if any(not isfinite(w) or w < 0 for w in weights) or abs(sum(weights) - 1) > 1e-6:
            raise ValueError("Pesos devem ser não negativos e somar 1")
        references = (self.spend_reference, self.frequency_reference, self.recency_reference)
        if any(not isfinite(x) or x <= 0 for x in references):
            raise ValueError("Referências devem ser positivas e finitas")
        if not 0 <= self.high_value_threshold <= 100 or not 0 <= self.high_risk_threshold <= 1:
            raise ValueError("Limiares fora do intervalo")


class ValueScorer:
    def __init__(self, policy: ScoringPolicy):
        self.policy = policy

    def score(self, features: Features) -> float:
        p = self.policy
        return round(
            100
            * (
                p.spend_weight * min(features.spend / p.spend_reference, 1)
                + p.frequency_weight * min(features.frequency / p.frequency_reference, 1)
                + p.recency_weight * max(0, 1 - features.recency_days / p.recency_reference)
            ),
            2,
        )


class BaselineChurnPredictor:
    """Índice heurístico limitado a [0,1]; NÃO é probabilidade calibrada de ML."""

    def predict(self, features: Features) -> RiskEstimate:
        recency = min(features.recency_days / 180, 1)
        risk = round(min(0.95, 0.1 + 0.6 * recency + 0.25 * features.incident_rate), 4)
        return RiskEstimate(
            risk,
            "baseline_heuristic_v1",
            (
                f"Recência: {features.recency_days} dias",
                f"Taxa de viagens com atraso >= 60 min: {features.incident_rate:.0%}",
            ),
        )


class RuleSegmenter:
    def __init__(self, policy: ScoringPolicy):
        self.policy = policy

    def classify(self, value: float, risk: float) -> str:
        if value >= self.policy.high_value_threshold:
            return (
                "Alto Valor em Risco" if risk >= self.policy.high_risk_threshold else "Premium Leal"
            )
        return (
            "Reativação de Baixo Custo"
            if risk >= self.policy.high_risk_threshold
            else "Lazer com Potencial"
        )


class PriorityScorer:
    def score(self, value: float, risk: float) -> float:
        return round(value * risk, 2)
