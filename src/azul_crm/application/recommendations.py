from collections import Counter
from dataclasses import replace
from uuid import uuid4

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
            "Catálogo interno do MVP",
        ),
    ]
    if offer is not None:
        items.append(
            ChecklistItem(
                "OFFER_NOT_IN_MESSAGE",
                "A oferta sugerida é uma hipótese a validar e não deve aparecer na mensagem.",
                "Playbook interno (hipótese)",
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
        self._drafts = {}
        self._latest_draft = {}

    def recommend(self, customer_id: str, generate=True) -> Recommendation:
        rec = self._recommend(customer_id, generate)
        if rec.mode == "gemini_grounded_draft" and "Modo de contingência:" in rec.draft:
            rec = replace(rec, mode="playbook_template")
        rec = replace(rec, draft_id=str(uuid4()))
        if len(self._drafts) >= 500:
            self._drafts.pop(next(iter(self._drafts)))
        self._drafts[rec.draft_id] = rec
        self._latest_draft[customer_id] = rec.draft_id
        return rec

    def for_review(self, customer_id, draft_id=None):
        if draft_id:
            rec = self._drafts.get(draft_id)
            if rec is None or rec.customer_id != customer_id:
                raise ValueError("Rascunho expirado ou incompatível. Gere e revise novamente.")
            return rec
        # Compatibilidade: clientes antigos podem omitir o ID. A UI nova sempre o envia.
        latest = self._drafts.get(self._latest_draft.get(customer_id))
        return latest or self.recommend(customer_id, generate=False)

    def _recommend(self, customer_id: str, generate=True) -> Recommendation:
        generator = (
            self.generator if generate else getattr(self.generator, "fallback", self.generator)
        )
        customer = self.crm.customer(customer_id)
        scores = self.crm.scores(customer_id)
        # Evidência de governança: sem ela nenhuma ação é liberada (regra anterior mantida).
        evidence = self.retriever.retrieve("relacionamento contato sem benefício")
        # O regulamento contextualiza revisão/consentimento; não concede benefícios.
        if evidence:
            public_context = self.retriever.retrieve(
                "consentimento comunicação e-mail SMS revogada regulamento Azul Fidelidade"
            )
            seen = {e.document_id for e in evidence}
            evidence += tuple(
                e for e in public_context if not e.is_demo and e.document_id not in seen
            )
        traits_of = getattr(self.crm.segments, "traits", None)
        traits = traits_of(scores.segment) if traits_of else None

        if self.playbook is None or traits is None:
            action = self.eligibility.select(scores, bool(evidence))
            draft = generator.draft(customer, scores, action, evidence)
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
                generator.draft(customer, scores, action, evidence),
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
            generator.draft(customer, scores, action, all_evidence, context),
            all_evidence,
            mode=getattr(generator, "mode", "playbook_template"),
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
