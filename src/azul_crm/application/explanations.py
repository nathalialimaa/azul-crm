"""Valores de Shapley exatos por enumeração com referência única explícita.

Ausência de variável = valor da referência. Não modela correlação nem causalidade.
"""

import json
import math
from dataclasses import replace
from statistics import mean

NAMES = ("spend", "frequency", "recency_days", "incident_rate")


def exact_shapley(predict, values, reference):
    n = len(values)
    if n != len(reference) or not 1 <= n <= 8:
        raise ValueError("Valores e referência devem ter de 1 a 8 variáveis")
    if not all(math.isfinite(v) for v in [*values, *reference]):
        raise ValueError("Valores não finitos")
    outputs = {}
    for mask in range(1 << n):
        row = [values[i] if mask & (1 << i) else reference[i] for i in range(n)]
        outputs[mask] = float(predict(row))
    contributions = []
    for i in range(n):
        contribution = 0.0
        for mask in range(1 << n):
            if mask & (1 << i):
                continue
            size = mask.bit_count()
            weight = math.factorial(size) * math.factorial(n - size - 1) / math.factorial(n)
            contribution += weight * (outputs[mask | (1 << i)] - outputs[mask])
        contributions.append(contribution)
    return {
        "base_value": outputs[0],
        "prediction": outputs[(1 << n) - 1],
        "contributions": contributions,
        "additivity_error": abs(outputs[0] + sum(contributions) - outputs[(1 << n) - 1]),
    }


def explain_customer(container, root, customer_id):
    crm = container.crm
    crm.customer(customer_id)
    features = crm.features.build(customer_id, crm.trips(customer_id), crm.start, crm.end)
    artifact = root / "artifacts/churn.json"
    if artifact.exists():
        data = json.loads(artifact.read_text(encoding="utf-8"))
        background = dict(zip(data["features"], data["mean"], strict=True))
        reference_kind = "single_training_mean"
    else:
        population = [
            crm.features.build(c.customer_id, crm.trips(c.customer_id), crm.start, crm.end)
            for c in crm.customers()
        ]
        background = {name: mean(getattr(f, name) for f in population) for name in NAMES}
        reference_kind = "single_observed_portfolio_mean"
    values = [getattr(features, name) for name in NAMES]
    reference = [background[name] for name in NAMES]
    results = {}
    for target, predict in {
        "value_score": lambda f: crm.value.score(f),
        "churn_risk": lambda f: crm.churn.predict(f).probability,
    }.items():
        result = exact_shapley(
            lambda row: predict(replace(features, **dict(zip(NAMES, row, strict=True)))),
            values,
            reference,
        )
        result["features"] = [
            {
                "name": name,
                "value": values[i],
                "reference": reference[i],
                "shapley_value": result["contributions"][i],
            }
            for i, name in enumerate(NAMES)
        ]
        del result["contributions"]
        results[target] = result
    return {
        "customer_id": customer_id,
        "method": "exact_interventional_shapley_single_reference_v1",
        "reference_kind": reference_kind,
        "model_version": crm.scores(customer_id).model_version,
        "evaluated_at": crm.end.isoformat(),
        "outputs": results,
        "limitation": "Enumeração exata de 16 coalizões por saída, referência única da média de treino (ou carteira observada sem artefato). Não é SHAP condicional nem estima causalidade. Atribuições dependem da referência; combinações mascaradas podem não representar viagens reais. Risco heurístico não é probabilidade calibrada.",
    }
