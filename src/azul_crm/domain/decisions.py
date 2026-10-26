"""Catálogo inicial seguro. Benefícios comerciais exigirão políticas verificadas."""

from azul_crm.domain.models import Action, Scores


class EligibilityPolicy:
    def __init__(self, high_risk_threshold: float = 0.6):
        self.high_risk_threshold = high_risk_threshold

    def select(self, scores: Scores, has_evidence: bool) -> Action:
        if not has_evidence:
            return Action(
                "NO_ACTION", "Revisão manual", "Sem evidência disponível para fundamentar a ação."
            )
        if scores.churn_risk >= self.high_risk_threshold:
            return Action(
                "CONTACT_SUPPORT",
                "Contato de escuta",
                "Entender possíveis atritos, sem prometer benefícios.",
            )
        return Action(
            "RELATIONSHIP",
            "Contato de relacionamento",
            "Manter relacionamento, sem oferta comercial automática.",
        )
