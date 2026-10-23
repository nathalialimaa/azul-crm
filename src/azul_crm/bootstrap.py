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
    from azul_crm.infrastructure.store import Store

    store = Store(settings.root)
    stored = store.read("manifest")
    if stored:
        return build_stored_container(settings, store, stored[0])
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


def build_stored_container(settings, store, manifest):
    import hashlib

    from azul_crm.infrastructure.rag import DocumentIndex, SafeMessageGenerator
    from azul_crm.infrastructure.store import StoredCustomerRepository
    from azul_crm.pipeline.modeling import LogisticPredictor

    policy = settings.scoring_policy()
    windows = settings.windows()
    for key in ("observation_start", "observation_end"):
        if manifest[key] != windows[key].isoformat():
            raise ValueError("Janela mudou: regenere a Gold SQL")
    churn = BaselineChurnPredictor()
    path = settings.root / "artifacts/churn.json"
    if path.exists():
        artifact = json.loads(path.read_text())
        features = sorted(store.read("features"), key=lambda r: r["customer_id"])
        fingerprint = hashlib.sha256(json.dumps(features, sort_keys=True).encode()).hexdigest()
        if fingerprint != artifact["gold_fingerprint"]:
            raise ValueError("Modelo incompatível com a Gold. Treine novamente.")
        if artifact["report"]["selected"] == "logistic":
            churn = LogisticPredictor(artifact)
    segmenter, segmenter_method = RuleSegmenter(policy), "rules"
    personas_path = settings.root / "artifacts/personas.json"
    if personas_path.exists():
        from azul_crm.infrastructure.personas import ClusterSegmenter
        from azul_crm.pipeline.personas import fingerprint

        persona_artifact = json.loads(personas_path.read_text(encoding="utf-8"))
        current = fingerprint(sorted(store.read("features"), key=lambda r: r["customer_id"]))
        if persona_artifact.get("gold_fingerprint") != current:
            raise ValueError("Personas incompatíveis com a Gold. Execute: azul-crm personas")
        segmenter = ClusterSegmenter(persona_artifact)
        segmenter_method = segmenter.method
    crm = CrmService(
        StoredCustomerRepository(store),
        FeatureBuilder(),
        ValueScorer(policy),
        churn,
        segmenter,
        PriorityScorer(),
        windows["observation_start"],
        windows["observation_end"],
    )
    index = DocumentIndex(settings.root)
    playbook, generator = None, SafeMessageGenerator()
    playbook_path = settings.root / "config/playbook.toml"
    if playbook_path.exists():
        from azul_crm.infrastructure.playbook import PlaybookMessageGenerator, load_playbook

        playbook = load_playbook(playbook_path)
        generator = PlaybookMessageGenerator(playbook)
    recommendations = RecommendationService(
        crm, index, EligibilityPolicy(policy.high_risk_threshold), generator, playbook
    )
    manifest = {
        **manifest,
        "scoring_policy": asdict(policy),
        "risk_method": "logistic_synthetic"
        if isinstance(churn, LogisticPredictor)
        else "heuristic_not_calibrated",
        "agent_mode": index.mode,
        "segmenter": segmenter_method,
        "clv_policy": asdict(settings.clv_policy()),
        "playbook": playbook.version if playbook else "none",
        "storage": store.backend,
    }
    return Container(crm, recommendations, manifest)
