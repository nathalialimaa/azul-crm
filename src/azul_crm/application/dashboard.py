"""Consultas estruturadas e simulação: o LLM não calcula indicadores."""

from collections import Counter
from dataclasses import asdict
from datetime import timedelta

from azul_crm.application.features import FeatureBuilder


def overview(c, months=12, segment=None, route=None):
    rows = []
    start = max(c.crm.start, c.crm.end - timedelta(days=round(months * 365.25 / 12) - 1))
    for customer in c.crm.customers():
        trips = [
            t for t in c.crm.trips(customer.customer_id) if start <= t.flight_date <= c.crm.end
        ]
        if route:
            trips = [t for t in trips if t.origin + "-" + t.destination == route]
        if not trips:
            continue
        f = FeatureBuilder().build(customer.customer_id, trips, start, c.crm.end)
        score = c.crm.scores(customer.customer_id)
        # Scores permanecem na janela contratual, filtros alteram população/indicadores do recorte.
        if segment and score.segment != segment:
            continue
        annual = f.spend * 365.25 / ((c.crm.end - start).days + 1)
        clv = round(annual * (1 - 0.5 * score.churn_risk), 2)
        preferred = Counter(t.origin + "-" + t.destination for t in trips).most_common(1)[0][0]
        rows.append(
            {
                **asdict(score),
                "home_airport": customer.home_airport,
                "route": preferred,
                "clv_12m_proxy": clv,
                "weighted_value_at_risk": round(clv * score.churn_risk, 2),
                "observed_spend": f.spend,
                "frequency": f.frequency,
                "recency_days": f.recency_days,
                "is_synthetic": customer.is_synthetic,
            }
        )
    rows.sort(key=lambda r: (-r["priority_score"], r["customer_id"]))
    p = c.metadata["scoring_policy"]
    high = [r for r in rows if r["value_score"] >= p["high_value_threshold"]]
    return {
        "rows": rows,
        "kpis": {
            "customers": len(rows),
            "high_value": len(high),
            "high_value_at_risk": sum(r["churn_risk"] >= p["high_risk_threshold"] for r in high),
            "clv_12m_proxy": round(sum(r["clv_12m_proxy"] for r in rows), 2),
            "weighted_value_at_risk": round(sum(r["weighted_value_at_risk"] for r in rows), 2),
        },
        "filters": {"months": months, "segment": segment, "route": route},
        "notes": "Scores usam janela de treinamento completa. Filtros de período/rota recortam viagens e público. CLV é proxy de receita, não margem nem previsão validada.",
    }


def simulation(rows, cost_per_customer, assumed_retention):
    cost = len(rows) * cost_per_customer
    value = sum(r["weighted_value_at_risk"] for r in rows)
    return {
        "customers": len(rows),
        "cost": round(cost, 2),
        "value_at_risk": round(value, 2),
        "assumed_retention": assumed_retention,
        "hypothetical_protected_value": round(value * assumed_retention, 2),
        "net_scenario": round(value * assumed_retention - cost, 2),
        "break_even_retention": cost / value if value else None,
        "causal_claim": False,
        "note": "Cenário hipotético; não estima uplift real.",
    }
