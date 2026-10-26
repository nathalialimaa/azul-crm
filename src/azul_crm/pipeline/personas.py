"""Personas orientadas por dados: KMeans sobre comportamento observado.

Roda offline (``azul-crm personas``), nunca durante uma requisição. O resultado é um artefato
JSON versionado junto com o fingerprint da Gold usada, no mesmo padrão do modelo de churn.
"""

import hashlib
import json

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from azul_crm.domain.personas import EXCLUDED_ATTRIBUTES, FEATURE_NAMES, persona_vector

METHOD = "kmeans_personas_v1"
MIN_CUSTOMERS = 50
MIN_SHARE = 0.05  # grupo menor que isso é outlier, não persona
CLIP_PERCENTILES = (1, 99)
K_SCAN = (3, 4, 5)

# Critérios de nome. Todos explícitos e auditáveis; nada de rótulo por atributo cadastral.
COOLING_DAYS = 90  # média de dias sem voar a partir da qual o grupo está "esfriando"
DELAY_RATE = 0.5  # fração de viagens com atraso >= 60 min que marca "atrasos frequentes"
# Em bases com atraso realista (poucos por cento), 50% nunca ocorre. Então também vale a regra
# relativa: o grupo tem atraso de pelo menos 10% das viagens E de 3x a taxa média da base.
RELATIVE_DELAY_MIN = 0.10
RELATIVE_DELAY_MULTIPLE = 3.0


def fingerprint(features: list[dict]) -> str:
    """Mesma definição usada pelo treino de churn: liga o artefato ao snapshot da Gold."""
    return hashlib.sha256(json.dumps(features, sort_keys=True).encode()).hexdigest()


def _fit(matrix, k, seed, n_init=10):
    return KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(matrix)


def _brl(value: float) -> str:
    return "R$ " + f"{value:,.0f}".replace(",", ".")


def _name_cluster(
    value_z: float, recency_days: float, incident_rate: float, population_incident: float = 0.0
):
    """Nome e descrição a partir do comportamento médio do grupo."""
    high = value_z > 0
    cooling = recency_days >= COOLING_DAYS
    frequent = incident_rate >= DELAY_RATE
    above_average = not frequent and incident_rate >= max(
        RELATIVE_DELAY_MIN, RELATIVE_DELAY_MULTIPLE * population_incident
    )
    delays = frequent or above_average
    traits = {"high_value": bool(high), "cooling": bool(cooling), "delays": bool(delays)}
    if high:
        name = "Alto Valor Esfriando" if cooling else "Fiéis de Alto Valor"
    else:
        name = "Baixo Volume Esfriando" if cooling else "Baixo Volume Ativo"
    if delays:
        name += " com Atrasos Frequentes" if frequent else " com Atrasos Acima da Média"
    text = (
        (
            "Gastam e voam acima da média da base"
            if high
            else "Gastam e voam abaixo da média da base"
        )
        + (", estão há bastante tempo sem voar" if cooling else ", voaram recentemente")
        + (
            f", e {incident_rate:.0%} das viagens tiveram atraso de 60 min ou mais."
            if delays
            else "."
        )
    )
    return name, text, traits


def _bootstrap_stability(matrix, labels, k, seed, rounds=10):
    """ARI entre o agrupamento de referência e reajustes com 80% dos clientes."""
    rng = np.random.default_rng(seed)
    size = max(k * 5, int(0.8 * len(matrix)))
    scores = []
    for i in range(rounds):
        idx = rng.choice(len(matrix), size=size, replace=False)
        model = _fit(matrix[idx], k, seed + i + 1, n_init=5)
        scores.append(adjusted_rand_score(labels, model.predict(matrix)))
    return float(np.mean(scores)), float(np.min(scores))


def train_personas(root, store, seed=42, k=4):
    feats = sorted(store.read("features"), key=lambda r: r["customer_id"])
    if len(feats) < MIN_CUSTOMERS:
        raise ValueError(f"Gere pelo menos {MIN_CUSTOMERS} clientes para formar personas")
    if not 2 <= k <= 8:
        raise ValueError("k deve estar entre 2 e 8")

    raw = np.array([persona_vector(f) for f in feats])
    # Winsorização: um cliente extremo (ex.: tudo pago com pontos) não pode virar um grupo.
    clip_low, clip_high = np.percentile(raw, CLIP_PERCENTILES, axis=0)
    raw = np.clip(raw, clip_low, clip_high)
    scaler = StandardScaler().fit(raw)
    matrix = scaler.transform(raw)

    scan = {}
    for candidate in sorted({*K_SCAN, k}):
        labels_c = _fit(matrix, candidate, seed).labels_
        scan[str(candidate)] = round(float(silhouette_score(matrix, labels_c)), 4)

    model = _fit(matrix, k, seed)
    labels = model.labels_
    smallest = float(np.bincount(labels, minlength=k).min()) / len(feats)
    if smallest < MIN_SHARE:
        raise ValueError(
            f"Há grupo com {smallest:.1%} da base (mínimo {MIN_SHARE:.0%}). "
            "Reduza k ou revise os dados antes de publicar personas."
        )
    ari_mean, ari_min = _bootstrap_stability(matrix, labels, k, seed)

    centroids = model.cluster_centers_
    population_incident = float(np.mean([f["incident_rate"] for f in feats]))
    personas, used = [], set()
    for cluster in range(k):
        members = [feats[i] for i in np.where(labels == cluster)[0]]
        spend = float(np.mean([m["spend"] for m in members]))
        frequency = float(np.mean([m["frequency"] for m in members]))
        recency = float(np.mean([m["recency_days"] for m in members]))
        incident = float(np.mean([m["incident_rate"] for m in members]))
        name, text, traits = _name_cluster(
            (centroids[cluster][0] + centroids[cluster][1]) / 2,
            recency,
            incident,
            population_incident,
        )
        if name in used:  # nomes precisam ser únicos para filtros e relatórios
            name = f"{name} ({cluster + 1})"
        used.add(name)
        personas.append(
            {
                "cluster": cluster,
                "name": name,
                "description": (
                    f"{text} Em média: {_brl(spend)} gastos, "
                    f"{frequency:.0f} viagens, {recency:.0f} dias desde a última viagem."
                ),
                "traits": traits,
                "size": len(members),
                "share": round(len(members) / len(feats), 4),
                "profile": {
                    "spend": round(spend, 2),
                    "frequency": round(frequency, 2),
                    "recency_days": round(recency, 1),
                    "incident_rate": round(incident, 4),
                },
            }
        )

    artifact = {
        "method": METHOD,
        "synthetic_only": True,
        "seed": seed,
        "k": k,
        "features": list(FEATURE_NAMES),
        "excluded_attributes": list(EXCLUDED_ATTRIBUTES),
        "clip_low": clip_low.tolist(),
        "clip_high": clip_high.tolist(),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "centroids": model.cluster_centers_.tolist(),
        "personas": personas,
        "quality": {
            "customers": len(feats),
            "silhouette": scan[str(k)],
            "smallest_group_share": round(smallest, 4),
            "silhouette_by_k": scan,
            "bootstrap_ari_mean": round(ari_mean, 4),
            "bootstrap_ari_min": round(ari_min, 4),
        },
        "limitation": (
            "Grupos formados sobre dados sintéticos. Mostram estrutura do gerador, não "
            "comportamento real. Recalibrar com dados reais antes de qualquer uso."
        ),
        "gold_fingerprint": fingerprint(feats),
    }
    target = root / "artifacts"
    target.mkdir(exist_ok=True)
    (target / "personas.json").write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "method": METHOD,
        "k": k,
        "quality": artifact["quality"],
        "personas": personas,
    }
