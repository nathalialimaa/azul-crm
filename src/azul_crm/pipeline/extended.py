"""Publicação SQL, fidelidade e janela de desfecho separada."""

import json
import math
import random
from dataclasses import asdict, replace
from datetime import timedelta

from azul_crm.application.features import FeatureBuilder
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.demand import PublicDemandGenerator
from azul_crm.pipeline.public_data import calibrated_routes
from azul_crm.pipeline.stages import DemoSyntheticGenerator, GoldPublisher, RouteCleaner


def generate(settings, count=400, seed=42, public=False):
    root = settings.root
    store = Store(root)
    routes = (
        calibrated_routes(store)
        if public
        else RouteCleaner().clean(root / "data/fixtures/routes.csv", root / "data/silver")
    )
    if not routes:
        raise ValueError(
            "Sem tarifas AZU com aeroportos resolvidos. Importe ANAC e dimensão primeiro."
        )
    w = settings.windows()
    start, end = w["observation_start"], w["observation_end"]
    if not 4 <= count <= 10000:
        raise ValueError("Clientes devem estar entre 4 e 10000")
    generator = PublicDemandGenerator() if public else DemoSyntheticGenerator()
    customers, trips = generator.generate(routes, count, seed, start, end)
    rng = random.Random(seed + 11)
    loyalty, outcomes, transactions, updated = [], [], [], []
    for t in trips:
        redeem = rng.random() < 0.12
        restricted = not redeem and rng.random() < 0.15
        cash = 0 if redeem else round(t.fare_amount * (0.8 if restricted else 1), 2)
        updated.append(replace(t, fare_amount=cash))
        transactions.append(
            {
                "trip_id": t.trip_id,
                "customer_id": t.customer_id,
                "payment_type": "points" if redeem else "restricted_cash" if restricted else "cash",
                "cash_revenue": cash,
                "reference_fare": t.fare_amount,
                "points_redeemed": round(t.fare_amount * 50) if redeem else 0,
                "is_synthetic": True,
            }
        )
    trips = updated
    features = [FeatureBuilder().build(c.customer_id, trips, start, end) for c in customers]
    for c, f in zip(customers, features):
        own = [t for t in transactions if t["customer_id"] == c.customer_id]
        earned = round(f.spend * 3)
        redeemed = sum(t["points_redeemed"] for t in own)
        opening = redeemed + rng.randint(0, 50000)
        loyalty.append(
            {
                "customer_id": c.customer_id,
                "opening_points": opening,
                "earned": earned,
                "redeemed": redeemed,
                "balance": opening + earned - redeemed,
                "tier": "SIMULADO_" + rng.choice(["BASICO", "INTERMEDIARIO", "PREMIUM"]),
                "transactions": own,
                "is_synthetic": True,
                "official_eligibility": False,
            }
        )
        latent = rng.gauss(0, 0.9)
        propensity = 1 / (
            1 + math.exp(-(-1.4 + 1.8 * f.recency_days / 180 + 1.1 * f.incident_rate + latent))
        )
        churn = rng.random() < propensity
        future_count = 0 if churn else rng.randint(1, max(2, f.frequency // 2))
        future_dates = [
            (
                w["outcome_start"]
                + timedelta(days=rng.randint(0, (w["outcome_end"] - w["outcome_start"]).days))
            ).isoformat()
            for _ in range(future_count)
        ]
        outcomes.append(
            {
                "customer_id": c.customer_id,
                "outcome_start": str(w["outcome_start"]),
                "outcome_end": str(w["outcome_end"]),
                "future_trip_dates": sorted(future_dates),
                "future_trip_count": future_count,
                "churn": future_count == 0,
                "is_synthetic": True,
            }
        )
    # CSVs mantidos como exportação v1 para compatibilidade, não consultados pela aplicação.
    GoldPublisher().publish(settings.gold_directory, customers, trips, seed, start, end)
    manifest = json.loads((settings.gold_directory / "manifest.json").read_text())
    manifest.update(
        mode="synthetic_public_fares" if public else "demo_fixture",
        calibrated_with_public_data=public,
        calibration_scope="route_mean_fares_and_route_demand" if public else "none",
        churn_label_status="synthetic_generated",
        storage=store.backend,
        schema_version="2.0",
        notes="Clientes, fidelidade, resgates, atrasos e desfechos simulados. Sem clientes reais.",
    )
    tables = {
        "customers": [(c.customer_id, asdict(c)) for c in customers],
        "trips": [(t.trip_id, asdict(t)) for t in trips],
        "features": [(f.customer_id, asdict(f)) for f in features],
        "loyalty": [(r["customer_id"], r) for r in loyalty],
        "outcomes": [(r["customer_id"], r) for r in outcomes],
        "manifest": [("current", manifest)],
        "scores": [],
        "decisions": [],
    }
    store.publish(tables)
    # Retira modelo de um snapshot anterior; novo treino deve ser explícito.
    for name in ["churn.json", "metrics.json", "personas.json", "bias_report.json"]:
        (root / "artifacts" / name).unlink(missing_ok=True)
    return manifest
