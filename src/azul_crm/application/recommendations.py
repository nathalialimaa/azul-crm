from azul_crm.application.crm import CrmService
from azul_crm.domain.decisions import EligibilityPolicy
from azul_crm.domain.models import Recommendation
from azul_crm.domain.ports import KnowledgeRetriever, MessageGenerator


class RecommendationService:
    def __init__(
        self,
        crm: CrmService,
        retriever: KnowledgeRetriever,
        eligibility: EligibilityPolicy,
        generator: MessageGenerator,
    ):
        self.crm, self.retriever = crm, retriever
        self.eligibility, self.generator = eligibility, generator

    def recommend(self, customer_id: str) -> Recommendation:
        customer = self.crm.customer(customer_id)
        scores = self.crm.scores(customer_id)
        evidence = self.retriever.retrieve("relacionamento contato sem benefício")
        action = self.eligibility.select(scores, bool(evidence))
        draft = self.generator.draft(customer, scores, action, evidence)
        return Recommendation(customer_id, action, draft, evidence)
