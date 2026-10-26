import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from azul_crm.api.main import create_app
from azul_crm.bootstrap import build_container
from azul_crm.domain.personas import EXCLUDED_ATTRIBUTES, FEATURE_NAMES, persona_vector
from azul_crm.domain.scoring import RuleSegmenter, ScoringPolicy
from azul_crm.infrastructure.personas import ClusterSegmenter
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.extended import generate
from azul_crm.pipeline.personas import MIN_CUSTOMERS, train_personas


@pytest.fixture
def base(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1]
    for name in ["config", "data/fixtures", "data/knowledge"]:
        shutil.copytree(source / name, tmp_path / name)
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    generate(Settings(tmp_path), 300, 42)
    return tmp_path, Store(tmp_path)


def artifact_of(root):
    return json.loads((root / "artifacts/personas.json").read_text(encoding="utf-8"))


def test_training_produces_balanced_named_personas(base):
    root, store = base
    result = train_personas(root, store, seed=42, k=4)
    names = [p["name"] for p in result["personas"]]
    assert len(names) == 4 and len(set(names)) == 4
    assert sum(p["size"] for p in result["personas"]) == 300
    quality = result["quality"]
    assert quality["smallest_group_share"] >= 0.05
    assert quality["silhouette"] > 0.2
    assert quality["bootstrap_ari_mean"] > 0.7
    assert {"3", "4", "5"} <= set(quality["silhouette_by_k"])


def test_training_is_reproducible(base):
    root, store = base
    train_personas(root, store, seed=42, k=4)
    first = artifact_of(root)
    train_personas(root, store, seed=42, k=4)
    assert artifact_of(root) == first


def test_protected_attributes_never_used_for_clustering(base):
    root, store = base
    train_personas(root, store, seed=42, k=4)
    artifact = artifact_of(root)
    assert tuple(artifact["features"]) == FEATURE_NAMES
    assert set(EXCLUDED_ATTRIBUTES) == set(artifact["excluded_attributes"])
    assert not set(artifact["features"]) & set(EXCLUDED_ATTRIBUTES)
    assert artifact["synthetic_only"] is True


def test_outlier_group_is_rejected(base):
    root, store = base
    with pytest.raises(ValueError):
        train_personas(root, store, seed=42, k=8)  # força grupos pequenos demais
    with pytest.raises(ValueError):
        train_personas(root, store, seed=42, k=1)


def test_too_few_customers_is_rejected(tmp_path):
    class Tiny:
        def read(self, name):
            return [
                {
                    "customer_id": f"C{i}",
                    "spend": 1,
                    "frequency": 1,
                    "recency_days": 1,
                    "incident_rate": 0,
                }
                for i in range(MIN_CUSTOMERS - 1)
            ]

    with pytest.raises(ValueError):
        train_personas(tmp_path, Tiny())


def test_container_uses_personas_and_explains(base):
    root, store = base
    assert build_container(Settings(root)).metadata["segmenter"] == "rules"
    train_personas(root, store, seed=42, k=4)
    container = build_container(Settings(root))
    assert container.metadata["segmenter"] == "kmeans_personas_v1"
    names = {p["name"] for p in artifact_of(root)["personas"]}
    rows = container.crm.priorities()
    assert len(rows) == 300 and {r.segment for r in rows} == names
    assert rows[0].model_version.endswith("+kmeans_personas_v1")
    assert any(d.startswith("Persona: " + rows[0].segment) for d in rows[0].drivers)


def test_stale_personas_fail_loudly(base):
    root, store = base
    train_personas(root, store, seed=42, k=4)
    artifact = artifact_of(root)
    artifact["gold_fingerprint"] = "0" * 64
    (root / "artifacts/personas.json").write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match="Personas incompatíveis"):
        build_container(Settings(root))


def test_regenerating_gold_discards_old_personas(base):
    root, store = base
    train_personas(root, store, seed=42, k=4)
    assert (root / "artifacts/personas.json").exists()
    generate(Settings(root), 300, 7)
    assert not (root / "artifacts/personas.json").exists()
    assert build_container(Settings(root)).metadata["segmenter"] == "rules"


def test_segmenter_contract_and_backward_compatibility(base):
    root, store = base
    train_personas(root, store, seed=42, k=4)
    segmenter = ClusterSegmenter(artifact_of(root))
    features = {"spend": 20000, "frequency": 25, "recency_days": 10, "incident_rate": 0.1}
    assert segmenter.classify(0, 0, features) == segmenter.classify(99, 1, features)
    assert len(persona_vector(features)) == len(FEATURE_NAMES)
    with pytest.raises(ValueError):
        segmenter.classify(50, 0.5)  # sem features não há como classificar
    # RuleSegmenter continua aceitando a chamada antiga de dois argumentos.
    assert RuleSegmenter(ScoringPolicy()).classify(80, 0.7) == "Alto Valor em Risco"
    broken = artifact_of(root)
    broken.pop("centroids")
    with pytest.raises(ValueError):
        ClusterSegmenter(broken)


def test_extreme_customer_is_clipped_not_isolated(base):
    root, store = base
    train_personas(root, store, seed=42, k=4)
    segmenter = ClusterSegmenter(artifact_of(root))
    extreme = {"spend": 0, "frequency": 2, "recency_days": 103, "incident_rate": 0.5}
    assert segmenter.classify(0, 0, extreme) in {p["name"] for p in segmenter.personas}


def test_personas_endpoint(base):
    root, store = base
    with TestClient(create_app(build_container(Settings(root)))) as api:
        assert api.get("/api/v1/personas").json() == {"trained": False, "method": "rules"}
    train_personas(root, store, seed=42, k=4)
    with TestClient(create_app(build_container(Settings(root)))) as api:
        body = api.get("/api/v1/personas").json()
        assert body["trained"] and len(body["personas"]) == 4
        assert "centroids" not in body and "clip_low" not in body
        segments = {s["segment"] for s in api.get("/api/v1/segments").json()}
        assert segments == {p["name"] for p in body["personas"]}
