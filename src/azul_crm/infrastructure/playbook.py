"""Carrega o playbook do TOML e redige rascunhos só com fatos do cliente."""

import tomllib
from pathlib import Path

from azul_crm.domain.models import Action, Customer, Evidence, Scores
from azul_crm.domain.playbook import Playbook


def load_playbook(path: Path) -> Playbook:
    with path.open("rb") as file:
        return Playbook.from_dict(tomllib.load(file))


class _Facts(dict):
    """Placeholder sem valor vira texto vazio em vez de quebrar a mensagem."""

    def __missing__(self, key):
        return ""


class PlaybookMessageGenerator:
    """Rascunho a partir do texto da ação. Ofertas NUNCA entram na mensagem."""

    def __init__(self, playbook: Playbook):
        self.playbook = playbook

    def draft(
        self,
        customer: Customer,
        scores: Scores,
        action: Action,
        evidence: tuple[Evidence, ...],
        context: dict | None = None,
    ) -> str:
        definition = self.playbook.actions.get(action.code)
        if action.code == "NO_ACTION" or definition is None:
            return "Aguardar revisão humana e inclusão de evidências verificadas."
        facts = _Facts(context or {})
        route = facts.get("favorite_route")
        facts["route_clause"] = f" na rota {route}" if route else ""
        usable = all(facts.get(key) for key in definition.needs)
        text = definition.template.format_map(facts) if usable else definition.fallback
        return text + " [Rascunho para revisão humana; nenhuma mensagem foi enviada.]"
