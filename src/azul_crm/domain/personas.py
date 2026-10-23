"""Vetor de comportamento das personas. Só usa o que o cliente FEZ, nunca quem ele É.

Atributos cadastrais (canal preferido, aeroporto de origem, tier) ficam de fora de propósito:
agrupar por eles transformaria a persona em estereótipo e abriria risco de viés (LGPD).
Para incluir uma feature nova (por exemplo, tendência de frequência), basta acrescentá-la
em ``FEATURE_NAMES`` e em ``persona_vector``; treino e inferência usam as duas.
"""

import math

FEATURE_NAMES = (
    "log_spend",
    "frequency",
    "recency_days",
    "incident_rate",
    "log_avg_ticket",
)

# Atributos conhecidos que NÃO entram no agrupamento. Registrados no artefato para auditoria.
EXCLUDED_ATTRIBUTES = ("preferred_channel", "home_airport", "loyalty_tier")


def _get(source, name):
    return source[name] if isinstance(source, dict) else getattr(source, name)


def persona_vector(features) -> list[float]:
    """Aceita ``Features`` (domínio) ou um dict da tabela ``features`` do store."""
    spend = float(_get(features, "spend"))
    frequency = float(_get(features, "frequency"))
    ticket = spend / frequency if frequency > 0 else 0.0
    return [
        math.log1p(spend),
        frequency,
        float(_get(features, "recency_days")),
        float(_get(features, "incident_rate")),
        math.log1p(ticket),
    ]
