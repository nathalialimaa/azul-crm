from collections import Counter

from azul_crm.application.crm import CrmService
from azul_crm.domain.decisions import EligibilityPolicy
from azul_crm.domain.models import Action, ChecklistItem, Evidence, Offer, Recommendation
from azul_crm.domain.playbook import Playbook, PlaybookAction
from azul_crm.domain.ports import KnowledgeRetriever, MessageGenerator

PLAYBOOK_SOURCE = "internal://playbook (hipótese interna; não é política da Azul)"


CONSENT_SOURCE = "Regulamento do Azul Fidelidade, item 3.6"


def review_checklist(action: Action, offer: Offer | None) -> tuple[ChecklistItem, ...]:
    """O que o revisor confirma antes de aprovar. Sem ação não há contato, logo não há checklist."""
    if action.code == "NO_ACTION":
        return ()
    items = [
        ChecklistItem(
            "CONSENT",
            "Confirmar o consentimento de comunicação do cliente antes de qualquer contato. "
            "O cadastro autoriza e-mail, push, SMS e telefone, e a autorização pode ser revogada "
            "a qualquer momento. Esta base sintética não tem dados de consentimento.",
            CONSENT_SOURCE,
        ),
        ChecklistItem(
            "HUMAN_REVIEW",
            "Ler o rascunho e conferir os fatos citados. O sistema não envia mensagens.",
            "internal://catalogo-acoes-mvp",
        ),
    ]
    if offer is not None:
        items.append(
            ChecklistItem(
                "OFFER_NOT_IN_MESSAGE",
                "A oferta sugerida é uma hipótese a validar e não deve aparecer na mensagem.",
                "internal://playbook",
            )
        )
    return tuple(items)


class _Facts(dict):
    def __missing__(self, key):
        return ""


class RecommendationService:
    def __init__(
        self,
        crm: CrmService,
        retriever: KnowledgeRetriever,
        eligibility: EligibilityPolicy,
        generator: MessageGenerator,
        playbook: Playbook | None = None,
    ):
        self.crm, self.retriever = crm, retriever
        self.eligibility, self.generator = eligibility, generator
        self.playbook = playbook

    def recommend(self, customer_id: str) -> Recommendation:
        customer = self.crm.customer(customer_id)
        scores = self.crm.scores(customer_id)
        # Evidência de governança: sem ela nenhuma ação é liberada (regra anterior mantida).
        evidence = self.retriever.retrieve("relacionamento contato sem benefício")
        traits_of = getattr(self.crm.segments, "traits", None)
        traits = traits_of(scores.segment) if traits_of else None

        if self.playbook is None or traits is None:
            action = self.eligibility.select(scores, bool(evidence))
            draft = self.generator.draft(customer, scores, action, evidence)
            return Recommendation(
                customer_id,
                action,
                draft,
                evidence,
                channel=customer.preferred_channel,
                persona=scores.segment,
                review_checklist=review_checklist(action, None),
            )

        definition, offer_def = self.playbook.decide(traits)
        if not evidence:
            action = Action(
                "NO_ACTION", "Revisão manual", "Sem evidência disponível para fundamentar a ação."
            )
            return Recommendation(
                customer_id,
                action,
                self.generator.draft(customer, scores, action, evidence),
                evidence,
                mode="playbook_template",
                channel=customer.preferred_channel,
                persona=scores.segment,
            )

        context = self._context(customer_id)
        action = Action(definition.code, definition.title, definition.reason)
        all_evidence = evidence + (self._playbook_evidence(definition),)
        offer = None
        if offer_def is not None:
            facts = _Facts(context)
            facts["favorite_route"] = context.get("favorite_route") or "rota mais usada"
            offer = Offer(
                offer_def.code,
                offer_def.title,
                offer_def.description.format_map(facts),
                offer_def.status,
                offer_def.requires,
            )
        return Recommendation(
            customer_id,
            action,
            self.generator.draft(customer, scores, action, all_evidence, context),
            all_evidence,
            mode="playbook_template",
            offer=offer,
            channel=customer.preferred_channel,
            persona=scores.segment,
            review_checklist=review_checklist(action, offer),
        )

    def _playbook_evidence(self, definition: PlaybookAction) -> Evidence:
        return Evidence(
            f"playbook-{definition.code}",
            f"Playbook · {definition.title}",
            definition.rule_text,
            PLAYBOOK_SOURCE,
            self.playbook.version,
            True,
        )

    def _context(self, customer_id: str) -> dict:
        """Fatos reais do cliente na janela de observação, usados no texto e na oferta."""
        trips = self.crm.trips(customer_id)
        features = self.crm.features.build(customer_id, trips, self.crm.start, self.crm.end)
        observed = [t for t in trips if self.crm.start <= t.flight_date <= self.crm.end]
        routes = Counter(f"{t.origin}-{t.destination}" for t in observed)
        return {
            "trips": features.frequency,
            "delayed_trips": sum(t.delay_minutes >= 60 for t in observed),
            "days_since_last": features.recency_days if features.frequency else 0,
            "favorite_route": routes.most_common(1)[0][0] if routes else None,
        }
