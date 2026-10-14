"""Composition root: único lugar que escolhe adaptadores concretos."""

import json
from dataclasses import dataclass
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
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    policy = settings.scoring_policy()
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
