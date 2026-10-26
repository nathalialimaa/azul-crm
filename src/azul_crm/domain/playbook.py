"""Playbook de retenção: qual a próxima melhor ação para cada persona.

Duas camadas, de propósito:

* **Ação principal**: contato sem benefício comercial (escuta, recuperação de serviço, convite).
  É o que pode virar rascunho de mensagem, sempre com revisão humana.
* **Oferta sugerida**: ideia comercial (bônus, upgrade, oferta de rota). Entra como HIPÓTESE
  não verificada, a validar com a área dona do Azul Fidelidade. Nunca entra no texto da mensagem.

Uma oferta só pode ser marcada como ``verified`` se registrar a fonte oficial. Enquanto as regras
públicas vigentes não forem coletadas, todas ficam como ``hypothesis_unverified``.
"""

from dataclasses import dataclass
from itertools import product

TRAIT_NAMES = ("high_value", "cooling", "delays")
STATUS_HYPOTHESIS = "hypothesis_unverified"
STATUS_VERIFIED = "verified"


@dataclass(frozen=True)
class Traits:
    """Comportamento médio de um grupo (persona ou segmento)."""

    high_value: bool
    cooling: bool  # está há bastante tempo sem voar
    delays: bool  # muitas viagens com atraso >= 60 min


@dataclass(frozen=True)
class PlaybookAction:
    code: str
    title: str
    kind: str
    reason: str
    rule_text: str
    template: str
    fallback: str
    needs: tuple[str, ...] = ()
    assumed_cost: float = 0.0  # R$ por cliente, hipótese
    assumed_retention: float = 0.0  # fração do valor em risco protegida, hipótese


@dataclass(frozen=True)
class PlaybookOffer:
    code: str
    title: str
    description: str
    requires: str
    status: str = STATUS_HYPOTHESIS
    source: str = ""


@dataclass(frozen=True)
class Rule:
    id: str
    when: tuple[tuple[str, bool], ...]
    action: str
    offer: str | None = None

    def matches(self, traits: Traits) -> bool:
        return all(getattr(traits, key) == value for key, value in self.when)


class Playbook:
    def __init__(self, version, note, rules, actions, offers):
        self.version, self.note = version, note
        self.rules = tuple(rules)
        self.actions = {a.code: a for a in actions}
        self.offers = {o.code: o for o in offers}
        if len(self.actions) != len(actions) or len(self.offers) != len(offers):
            raise ValueError("Códigos duplicados no playbook")
        self._validate()

    def _validate(self):
        for action in self.actions.values():
            if action.assumed_cost < 0 or not 0 <= action.assumed_retention <= 1:
                raise ValueError(f"Premissas inválidas na ação {action.code}")
            if not action.template or not action.fallback or not action.rule_text:
                raise ValueError(f"Ação {action.code} sem texto, fallback ou regra")
        for offer in self.offers.values():
            if offer.status not in {STATUS_HYPOTHESIS, STATUS_VERIFIED}:
                raise ValueError(f"Status inválido na oferta {offer.code}")
            if offer.status == STATUS_VERIFIED and not offer.source:
                raise ValueError(f"Oferta {offer.code} verificada exige fonte oficial")
        for rule in self.rules:
            if rule.action not in self.actions:
                raise ValueError(f"Regra {rule.id}: ação desconhecida {rule.action}")
            if rule.offer is not None and rule.offer not in self.offers:
                raise ValueError(f"Regra {rule.id}: oferta desconhecida {rule.offer}")
            if any(key not in TRAIT_NAMES for key, _ in rule.when):
                raise ValueError(f"Regra {rule.id}: condição desconhecida")
        for values in product([False, True], repeat=len(TRAIT_NAMES)):
            traits = Traits(*values)
            if not any(rule.matches(traits) for rule in self.rules):
                raise ValueError(f"Playbook não cobre a combinação {traits}")

    def rule_for(self, traits: Traits) -> Rule:
        """A primeira regra que casa vence; a ordem das regras é a prioridade."""
        return next(rule for rule in self.rules if rule.matches(traits))

    def decide(self, traits: Traits) -> tuple[PlaybookAction, PlaybookOffer | None]:
        rule = self.rule_for(traits)
        return self.actions[rule.action], self.offers.get(rule.offer) if rule.offer else None

    @classmethod
    def from_dict(cls, data: dict) -> "Playbook":
        try:
            rules = [
                Rule(
                    r["id"],
                    tuple(sorted(r.get("when", {}).items())),
                    r["action"],
                    r.get("offer"),
                )
                for r in data["rule"]
            ]
            actions = [
                PlaybookAction(**{**a, "needs": tuple(a.get("needs", ()))}) for a in data["action"]
            ]
            offers = [PlaybookOffer(**o) for o in data["offer"]]
            return cls(data["version"], data.get("note", ""), rules, actions, offers)
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Playbook malformado: {exc}") from exc
