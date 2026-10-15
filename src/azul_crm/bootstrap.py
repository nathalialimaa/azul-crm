"""Composition root: único lugar que escolhe adaptadores concretos."""

import json
from dataclasses import asdict, dataclass
from datetime import date

from azul_crm.application.crm import CrmService
from azul_crm.application.features import FeatureBuilder
from azul_crm.application.recommendations import RecommendationService
from azul_crm.domain.decisions import EligibilityPolicy
from azul_crm.domain.scoring import (
    BaselineChurnPredictor,
    PriorityScorer,
    RuleSegmenter,
    ValueScorer,
)
from azul_crm.infrastructure.csv_repository import CsvCustomerRepository
from azul_crm.infrastructure.gold_validation import validate_gold
from azul_crm.infrastructure.knowledge import JsonKnowledgeRetriever, TemplateMessageGenerator
from azul_crm.infrastructure.settings import Settings


@dataclass(frozen=True)
class Container:
    crm: CrmService
    recommendations: RecommendationService
    metadata: dict


def build_container(settings: Settings) -> Container:
    manifest_path = settings.gold_directory / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("Gold ausente. Execute: python -m azul_crm.pipeline.cli demo")
    validate_gold(settings.gold_directory)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    policy = settings.scoring_policy()
    windows = settings.windows()
    for key in ("observation_start", "observation_end"):
        if manifest[key] != windows[key].isoformat():
            raise ValueError("Janelas mudaram: gere a Gold novamente antes de iniciar a API")
    manifest["scoring_policy"] = asdict(policy)
    manifest["planned_outcome_window"] = {
        key: windows[key].isoformat() for key in ("outcome_start", "outcome_end")
    }
    manifest["churn_label_status"] = "planned_not_generated"

    crm = CrmService(
        CsvCustomerRepository(settings.gold_directory),
        FeatureBuilder(),
        ValueScorer(policy),
        BaselineChurnPredictor(),
        RuleSegmenter(policy),
        PriorityScorer(),
        date.fromisoformat(manifest["observation_start"]),
        date.fromisoformat(manifest["observation_end"]),
    )
    recommendations = RecommendationService(
        crm,
        JsonKnowledgeRetriever(settings.root / "data" / "fixtures" / "knowledge.json"),
        EligibilityPolicy(policy.high_risk_threshold),
        TemplateMessageGenerator(),
    )
    return Container(crm, recommendations, manifest)
