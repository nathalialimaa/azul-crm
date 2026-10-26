from datetime import date

from azul_crm.application.features import FeatureBuilder
from azul_crm.infrastructure.store import StoredCustomerRepository


def validate_store(store):
    manifests = store.read("manifest")
    if len(manifests) != 1:
        raise ValueError("Manifesto Gold ausente ou duplicado")
    m = manifests[0]
    if m["schema_version"] != "2.0":
        raise ValueError("Versão Gold inválida")
    start, end = (
        date.fromisoformat(m["observation_start"]),
        date.fromisoformat(m["observation_end"]),
    )
    repo = StoredCustomerRepository(store)
    customers = repo.list_customers()
    if len(customers) != m["customer_count"] or not customers:
        raise ValueError("Contagem de clientes divergente")
    from dataclasses import asdict

    features = {r["customer_id"]: r for r in store.read("features")}
    outcomes = {r["customer_id"]: r for r in store.read("outcomes")}
    loyalties = {r["customer_id"]: r for r in store.read("loyalty")}
    ids = {c.customer_id for c in customers}
    if set(features) != ids or set(outcomes) != ids or set(loyalties) != ids:
        raise ValueError("Cobertura incompleta de features/desfechos/fidelidade")
    total = 0
    for c in customers:
        if c.is_synthetic is not True:
            raise ValueError("MVP requer dados sintéticos")
        trips = repo.trips_for(c.customer_id)
        total += len(trips)
        if any(not start <= t.flight_date <= end for t in trips):
            raise ValueError("Vazamento temporal na Gold")
        expected = asdict(FeatureBuilder().build(c.customer_id, trips, start, end))
        expected["observation_end"] = str(expected["observation_end"])
        if features[c.customer_id] != expected:
            raise ValueError("Feature inconsistente")
        o = outcomes[c.customer_id]
        if not end < date.fromisoformat(o["outcome_start"]) <= date.fromisoformat(o["outcome_end"]):
            raise ValueError("Janela de desfecho inválida")
        if any(not o["outcome_start"] <= d <= o["outcome_end"] for d in o["future_trip_dates"]):
            raise ValueError("Data fora do desfecho")
        if o["future_trip_count"] != len(o["future_trip_dates"]) or o["churn"] != (
            o["future_trip_count"] == 0
        ):
            raise ValueError("Desfecho inconsistente")
        loyalty = loyalties[c.customer_id]
        if (
            loyalty["balance"]
            != loyalty["opening_points"] + loyalty["earned"] - loyalty["redeemed"]
            or loyalty["balance"] < 0
        ):
            raise ValueError("Saldo de pontos inconsistente")
    if total != m["trip_count"]:
        raise ValueError("Contagem de viagens divergente")
    return {
        "status": "valid",
        "backend": store.backend,
        "customers": len(customers),
        "trips": total,
        "synthetic": True,
        "calibration": m["calibration_scope"],
    }
