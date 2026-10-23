"""Valor do cliente: CLV de 12 meses, definição de alto valor, concentração e sensibilidade.

As fórmulas estão em ``domain/clv.py``. Aqui só se aplica a política a toda a carteira, sempre na
janela completa de 12 meses: filtros de período ou rota do painel recortam quem aparece, mas não
mudam quem é de alto valor.
"""

from azul_crm.domain.clv import ClvPolicy, concentration, estimate, high_value_ids, top_count

METHOD = "clv_margin_discounted_v1"
PARETO_SHARES = (0.10, 0.20, 0.30)
SENSITIVITY_MARGINS = (0.05, 0.10, 0.15, 0.20, 0.25)
SENSITIVITY_DISCOUNTS = (0.08, 0.12, 0.16)


def policy_of(container) -> ClvPolicy:
    data = container.metadata.get("clv_policy")
    return ClvPolicy(**data) if data else ClvPolicy()


def customer_values(container, policy: ClvPolicy | None = None) -> list[dict]:
    """Um registro por cliente, na janela completa de observação."""
    policy = policy or policy_of(container)
    crm = container.crm
    days = (crm.end - crm.start).days + 1
    rows = []
    for customer in crm.customers():
        cid = customer.customer_id
        score = crm.scores(cid)
        features = crm.features.build(cid, crm.trips(cid), crm.start, crm.end)
        annual = features.spend * 365.25 / days
        value = estimate(annual, score.churn_risk, policy)
        rows.append(
            {
                "customer_id": cid,
                "segment": score.segment,
                "annual_spend": round(annual, 2),
                "churn_risk": score.churn_risk,
                "value_score": score.value_score,
                "potential_value_12m": round(value.potential, 2),
                "clv_12m": round(value.expected, 2),
                "clv_at_risk": round(value.at_risk, 2),
            }
        )
    top = high_value_ids(
        {r["customer_id"]: r["potential_value_12m"] for r in rows}, policy.top_share
    )
    for row in rows:
        row["is_high_value"] = row["customer_id"] in top
    return rows


def _sensitivity(rows: list[dict]) -> list[dict]:
    result = []
    for margin in SENSITIVITY_MARGINS:
        for discount in SENSITIVITY_DISCOUNTS:
            alt = ClvPolicy(margin=margin, discount_rate=discount)
            parts = [estimate(r["annual_spend"], r["churn_risk"], alt) for r in rows]
            result.append(
                {
                    "margin": margin,
                    "discount_rate": discount,
                    "total_clv_12m": round(sum(p.expected for p in parts), 2),
                    "total_clv_at_risk": round(sum(p.at_risk for p in parts), 2),
                }
            )
    return result


def clv_report(container, policy: ClvPolicy | None = None) -> dict:
    policy = policy or policy_of(container)
    rows = customer_values(container, policy)
    if not rows:
        raise ValueError("Sem clientes para calcular o CLV")
    risk_cut = container.metadata["scoring_policy"]["high_risk_threshold"]
    top = [r for r in rows if r["is_high_value"]]
    at_risk = [r for r in top if r["churn_risk"] >= risk_cut]
    potentials = [r["potential_value_12m"] for r in rows]

    by_persona = {}
    for r in rows:
        by_persona.setdefault(r["segment"], []).append(r)
    personas = [
        {
            "persona": name,
            "customers": len(members),
            "high_value_customers": sum(m["is_high_value"] for m in members),
            "share_high_value": round(sum(m["is_high_value"] for m in members) / len(members), 4),
            "mean_churn_risk": round(sum(m["churn_risk"] for m in members) / len(members), 4),
            "potential_value_12m": round(sum(m["potential_value_12m"] for m in members), 2),
            "clv_12m": round(sum(m["clv_12m"] for m in members), 2),
            "clv_at_risk": round(sum(m["clv_at_risk"] for m in members), 2),
        }
        for name, members in sorted(by_persona.items())
    ]
    return {
        "method": METHOD,
        "synthetic_only": True,
        "assumptions": {
            "margin": policy.margin,
            "discount_rate": policy.discount_rate,
            "top_share": policy.top_share,
            "horizon_months": policy.horizon_months,
            "status": "hipóteses de demonstração; não são dados da Azul",
        },
        "definition": {
            "potential_value_12m": "gasto em dinheiro dos últimos 12 meses x margem x desconto",
            "clv_12m": "valor potencial x (1 - risco de evasão)",
            "clv_at_risk": "valor potencial x risco de evasão",
            "high_value": f"os {policy.top_share:.0%} clientes de maior valor potencial",
            "components": [
                {"component": "Valor monetário", "how": "gasto em dinheiro dos últimos 12 meses"},
                {
                    "component": "Frequência",
                    "how": "já está no gasto (mais viagens, mais gasto); entra também no risco",
                },
                {
                    "component": "Recência",
                    "how": "entra no risco de evasão, que reduz o CLV esperado",
                },
                {
                    "component": "Potencial futuro",
                    "how": "horizonte de 12 meses, com margem, desconto e risco de evasão",
                },
            ],
        },
        "summary": {
            "customers": len(rows),
            "high_value_customers": len(top),
            "cutoff_potential_12m": min(r["potential_value_12m"] for r in top),
            "top_value_share": round(concentration(potentials, policy.top_share), 4),
            "total_potential_12m": round(sum(potentials), 2),
            "total_clv_12m": round(sum(r["clv_12m"] for r in rows), 2),
            "total_clv_at_risk": round(sum(r["clv_at_risk"] for r in rows), 2),
            "risk_threshold": risk_cut,
            "high_value_at_risk_customers": len(at_risk),
            "high_value_at_risk_clv": round(sum(r["clv_at_risk"] for r in at_risk), 2),
        },
        "concentration": [
            {
                "top_share": share,
                "customers": top_count(len(rows), share),
                "value_share": round(concentration(potentials, share), 4),
            }
            for share in PARETO_SHARES
        ],
        "by_persona": personas,
        "sensitivity": _sensitivity(rows),
        "ranking_note": (
            "Margem e desconto mudam o tamanho do valor, não quem é de alto valor: o ranking "
            "depende só do gasto. Para o ranking mudar é preciso um modelo de frequência e ticket "
            "futuros, que exige dados reais."
        ),
        "limitations": [
            "Dados sintéticos: o resultado descreve o gerador, não clientes reais.",
            "Margem e taxa de desconto são hipóteses; ver a tabela de sensibilidade.",
            "O risco de evasão vem de "
            + str(container.metadata.get("risk_method", "índice heurístico"))
            + ", não de uma probabilidade validada.",
            "O gasto considera só receita em dinheiro: viagens pagas com pontos não entram.",
        ],
        "customers": rows,
    }
