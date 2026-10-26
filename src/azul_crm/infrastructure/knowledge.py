import json
import re
from pathlib import Path

from azul_crm.domain.models import Action, Customer, Evidence, Scores


class JsonKnowledgeRetriever:
    """Recuperação lexical mínima de fixtures; não equivale a RAG semântico + LLM."""

    def __init__(self, path: Path):
        self.documents = tuple(
            Evidence(**row) for row in json.loads(path.read_text(encoding="utf-8"))
        )

    def retrieve(self, query: str) -> tuple[Evidence, ...]:
        terms = set(re.findall(r"\w+", query.lower()))
        ranked = [
            (len(terms & set(re.findall(r"\w+", (d.title + " " + d.text).lower()))), d)
            for d in self.documents
        ]
        return tuple(d for score, d in sorted(ranked, key=lambda pair: -pair[0]) if score > 0)[:3]


class TemplateMessageGenerator:
    def draft(
        self, customer: Customer, scores: Scores, action: Action, evidence: tuple[Evidence, ...]
    ) -> str:
        if action.code == "NO_ACTION":
            return "Aguardar revisão humana e inclusão de evidências verificadas."
        return (
            f"Olá, {customer.customer_id}! Gostaríamos de ouvir como foi sua experiência "
            "de viagem e entender como podemos melhorar nosso atendimento. "
            "Rascunho de demonstração; revisar antes de qualquer contato."
        )
