"""CLV de 12 meses e definição de alto valor. As premissas são explícitas e configuráveis.

Definições (valem para toda a aplicação):

* **Valor potencial 12m** = gasto em dinheiro dos últimos 12 meses x margem x fator de desconto.
  É a margem que o cliente deve gerar nos próximos 12 meses SE permanecer.
* **CLV 12m** = valor potencial x (1 - risco de evasão). Margem esperada, já descontado o risco.
* **CLV em risco** = valor potencial x risco de evasão. O que se perde se o cliente sair.
* **Alto valor** = os ``top_share`` clientes de maior valor potencial (ranking exato, desempate
  por identificador). O corte é um percentil e não um número arbitrário, e acompanha a base.

Margem e taxa de desconto são HIPÓTESES de demonstração, não dados da Azul. Elas mudam o tamanho
do valor, não quem é de alto valor: o ranking depende só do gasto, porque margem e desconto são
multiplicadores iguais para todos. Com dados reais, trocar o gasto por um modelo de frequência e
ticket futuros (por exemplo, BG/NBD) mantém o resto da definição.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ClvPolicy:
    margin: float = 0.15  # margem de contribuição sobre a receita em dinheiro (hipótese)
    discount_rate: float = 0.10  # taxa de desconto anual (hipótese)
    top_share: float = 0.20  # fatia da carteira considerada de alto valor
    horizon_months: int = 12  # fixo: o app mostra CLV de 12 meses

    def __post_init__(self):
        if not 0 < self.margin <= 1:
            raise ValueError("margin deve estar entre 0 (exclusive) e 1")
        if not 0 <= self.discount_rate < 1:
            raise ValueError("discount_rate deve estar entre 0 e 1 (exclusive)")
        if not 0 < self.top_share < 1:
            raise ValueError("top_share deve estar entre 0 e 1 (exclusivos)")
        if self.horizon_months != 12:
            raise ValueError("Só o horizonte de 12 meses é suportado")

    @property
    def discount_factor(self) -> float:
        """Fluxo de caixa no meio do horizonte: 1 / (1 + taxa) ** 0,5."""
        return 1 / (1 + self.discount_rate) ** 0.5


@dataclass(frozen=True)
class ClvEstimate:
    potential: float  # margem esperada em 12 meses se o cliente permanecer
    retention: float  # 1 - risco de evasão
    expected: float  # CLV: potencial x retenção
    at_risk: float  # potencial x risco


def estimate(annual_spend: float, churn_risk: float, policy: ClvPolicy) -> ClvEstimate:
    if annual_spend < 0 or not 0 <= churn_risk <= 1:
        raise ValueError("Gasto não negativo e risco entre 0 e 1")
    potential = annual_spend * policy.margin * policy.discount_factor
    return ClvEstimate(
        potential, 1 - churn_risk, potential * (1 - churn_risk), potential * churn_risk
    )


def top_count(total: int, share: float) -> int:
    return min(total, max(1, math.ceil(share * total))) if total else 0


def high_value_ids(potentials: dict[str, float], share: float) -> set[str]:
    """Os ``share`` de maior valor potencial. Ranking exato; empate resolvido por id."""
    ordered = sorted(potentials, key=lambda cid: (-potentials[cid], cid))
    return set(ordered[: top_count(len(ordered), share)])


def concentration(values: list[float], share: float) -> float:
    """Fração do valor total que está nos ``share`` clientes mais valiosos (curva de Pareto)."""
    total = sum(values)
    if not values or total <= 0:
        return 0.0
    best = sorted(values, reverse=True)[: top_count(len(values), share)]
    return sum(best) / total
