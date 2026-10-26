"""Segmentador por personas treinadas. Cumpre a porta ``Segmenter`` por tipagem estrutural."""

import numpy as np

from azul_crm.domain.personas import FEATURE_NAMES, persona_vector
from azul_crm.domain.playbook import Traits

REQUIRED = (
    "method",
    "features",
    "clip_low",
    "clip_high",
    "scaler_mean",
    "scaler_scale",
    "centroids",
    "personas",
    "gold_fingerprint",
)


class ClusterSegmenter:
    def __init__(self, artifact: dict):
        missing = [k for k in REQUIRED if k not in artifact]
        if missing:
            raise ValueError("Artefato de personas incompleto: " + ", ".join(missing))
        if tuple(artifact["features"]) != FEATURE_NAMES:
            raise ValueError("Features do artefato divergem do código. Treine as personas de novo.")
        self.method = artifact["method"]
        self.low = np.array(artifact["clip_low"], dtype=float)
        self.high = np.array(artifact["clip_high"], dtype=float)
        self.mean = np.array(artifact["scaler_mean"], dtype=float)
        self.scale = np.array(artifact["scaler_scale"], dtype=float)
        self.centroids = np.array(artifact["centroids"], dtype=float)
        by_cluster = {p["cluster"]: p for p in artifact["personas"]}
        if sorted(by_cluster) != list(range(len(self.centroids))):
            raise ValueError("Personas e centróides inconsistentes")
        self.personas = [by_cluster[i] for i in range(len(self.centroids))]

    def _assign(self, features) -> tuple[int, float]:
        raw = np.clip(np.array(persona_vector(features)), self.low, self.high)
        z = (raw - self.mean) / self.scale
        distances = np.linalg.norm(self.centroids - z, axis=1)
        cluster = int(np.argmin(distances))
        return cluster, float(distances[cluster])

    def classify(self, value: float, risk: float, features=None) -> str:
        if features is None:
            raise ValueError("ClusterSegmenter exige as features do cliente")
        return self.personas[self._assign(features)[0]]["name"]

    def traits(self, segment: str) -> Traits | None:
        for persona in self.personas:
            if persona["name"] == segment:
                t = persona.get("traits")
                return Traits(**t) if t else None
        return None

    def explain(self, features) -> tuple[str, ...]:
        cluster, distance = self._assign(features)
        persona = self.personas[cluster]
        return (
            f"Persona: {persona['name']} (distância ao centro do grupo: {distance:.2f})",
            persona["description"],
        )
