"""Auditoria de viés das recomendações (IA responsável / LGPD).

Pergunta central: clientes com o MESMO comportamento (mesma persona) recebem o MESMO
tratamento, independentemente de aeroporto de origem, região, canal ou tier simulado?

Esses atributos não entram no agrupamento nem nos scores. A auditoria verifica se, mesmo
assim, o resultado final os favorece ou prejudica, por exemplo por correlação indireta.

Resultado favorável = estar entre os ``TOP_SHARE`` mais prioritários da carteira (os que
recebem atenção de retenção). Três lentes:

1. Bruta: taxa de seleção por grupo e regra dos 4/5 (menor taxa / maior taxa >= 0,8).
2. Controlada por persona: a mesma comparação DENTRO de cada persona. Diferença que some aqui
   é explicada por comportamento ("atenção"); a que persiste é tratamento desigual ("alerta").
   Se os grupos nunca dividem a mesma persona, não há como comparar ("confundido").
3. Qualidade do modelo por grupo: paridade de recall entre quem realmente saiu (oportunidade
   igual) e diferença entre risco previsto e churn observado (calibração).
"""

import hashlib
import json
import math
from collections import defaultdict

import numpy as np
from scipy.stats import chi2_contingency

from azul_crm.pipeline.personas import fingerprint

METHOD = "bias_audit_v1"
TOP_SHARE = 0.20  # fatia da carteira que recebe atenção de retenção
MIN_GROUP = 30  # grupo menor que isso não é comparado (amostra insuficiente)
MIN_WITHIN = 20  # mínimo por grupo dentro de uma persona
MIN_CHURNERS = 10  # mínimo de clientes que saíram para medir recall do grupo
FOUR_FIFTHS = 0.8
CALIBRATION_GAP = 0.10  # 10 pontos percentuais
ASSOCIATION_P = 0.01
ASSOCIATION_V = 0.20  # Cramér's V: efeito pelo menos moderado

ATTRIBUTES = {
    "home_airport": "Aeroporto de origem",
    "region": "Região do aeroporto de origem",
    "preferred_channel": "Canal preferido",
    "tier": "Tier de fidelidade (simulado)",
}

REGIONS = {
    "Nordeste": "REC SSA FOR NAT MCZ AJU JPA SLZ THE IOS BPS PNZ VDC",
    "Sudeste": "GRU CGH VCP GIG SDU CNF VIX SJK UDI RAO MOC",
    "Sul": "CWB POA FLN NVT IGU JOI LDB",
    "Centro-Oeste": "BSB GYN CGB CGR",
    "Norte": "MAO BEL PMW RBR PVH MCP BVB STM",
}
REGION_OF = {code: name for name, codes in REGIONS.items() for code in codes.split()}


def region_of(airport: str) -> str:
    return REGION_OF.get(airport, "Outra")


def _rate(selected: int, total: int):
    return selected / total if total else None


def _ratio(rates):
    """Menor taxa / maior taxa entre os grupos comparáveis. None se não houver o que comparar."""
    values = [r for r in rates if r is not None]
    if len(values) < 2 or max(values) == 0:
        return None
    return min(values) / max(values)


def select_top(records, share=TOP_SHARE):
    """Marca exatamente ceil(share * N) clientes, desempate estável por id."""
    ordered = sorted(records, key=lambda r: (-r["priority_score"], r["customer_id"]))
    chosen = {r["customer_id"] for r in ordered[: math.ceil(share * len(ordered))]}
    return chosen


def _association(rows, attribute, groups):
    """Qui-quadrado persona x grupo; V de Cramér mede o tamanho do efeito."""
    personas = sorted({r["persona"] for r in rows})
    if len(groups) < 2 or len(personas) < 2:
        return None
    table = np.array(
        [
            [sum(1 for r in rows if r[attribute] == g and r["persona"] == p) for p in personas]
            for g in groups
        ]
    )
    table = table[:, table.sum(axis=0) > 0]
    if table.shape[1] < 2:
        return None
    chi2, p_value, _, _ = chi2_contingency(table)
    v = math.sqrt(chi2 / (table.sum() * (min(table.shape) - 1)))
    return {
        "chi2": round(float(chi2), 3),
        "p_value": round(float(p_value), 6),
        "cramers_v": round(float(v), 4),
        "relevant": bool(p_value < ASSOCIATION_P and v >= ASSOCIATION_V),
    }


def _attribute_report(rows, chosen, attribute):
    by_group = defaultdict(list)
    for r in rows:
        by_group[r[attribute]].append(r)
    groups, skipped = [], []
    for name, members in sorted(by_group.items()):
        if len(members) < MIN_GROUP:
            skipped.append({"group": name, "customers": len(members)})
            continue
        selected = sum(r["customer_id"] in chosen for r in members)
        churners = [r for r in members if r["churn_observed"]]
        recall = (
            _rate(sum(r["customer_id"] in chosen for r in churners), len(churners))
            if len(churners) >= MIN_CHURNERS
            else None
        )
        mean_risk = float(np.mean([r["churn_risk"] for r in members]))
        observed = float(np.mean([r["churn_observed"] for r in members]))
        shares = {
            p: round(sum(1 for r in members if r["persona"] == p) / len(members), 4)
            for p in sorted({r["persona"] for r in rows})
        }
        groups.append(
            {
                "group": name,
                "customers": len(members),
                "selection_rate": round(selected / len(members), 4),
                "recall_among_churners": None if recall is None else round(recall, 4),
                "mean_predicted_risk": round(mean_risk, 4),
                "observed_churn": round(observed, 4),
                "calibration_gap": round(mean_risk - observed, 4),
                "persona_mix": shares,
            }
        )

    names = [g["group"] for g in groups]
    selection_ratio = _ratio([g["selection_rate"] for g in groups])
    recall_ratio = _ratio([g["recall_among_churners"] for g in groups])
    raw_flag = selection_ratio is not None and selection_ratio < FOUR_FIFTHS

    within = []
    for persona in sorted({r["persona"] for r in rows}):
        members_p = [r for r in rows if r["persona"] == persona]
        sub = []
        for name in names:
            members = [r for r in members_p if r[attribute] == name]
            if len(members) >= MIN_WITHIN:
                selected = sum(r["customer_id"] in chosen for r in members)
                sub.append(
                    {
                        "group": name,
                        "customers": len(members),
                        "selection_rate": round(selected / len(members), 4),
                    }
                )
        ratio = _ratio([s["selection_rate"] for s in sub])
        if len(sub) >= 2:
            within.append(
                {
                    "persona": persona,
                    "groups": sub,
                    "selection_ratio": None if ratio is None else round(ratio, 4),
                    "flag": ratio is not None and ratio < FOUR_FIFTHS,
                }
            )
    within_flag = any(w["flag"] for w in within)
    comparable = [w for w in within if w["selection_ratio"] is not None]

    if len(groups) < 2:
        verdict = "amostra_insuficiente"
    elif within_flag:
        verdict = "alerta"
    elif raw_flag and not comparable:
        verdict = "confundido"  # grupos nunca dividem a mesma persona: não há como separar
    elif raw_flag:
        verdict = "atencao"
    else:
        verdict = "ok"
    return {
        "label": ATTRIBUTES[attribute],
        "verdict": verdict,
        "groups": groups,
        "skipped_small_groups": skipped,
        "selection_ratio": None if selection_ratio is None else round(selection_ratio, 4),
        "selection_flag": raw_flag,
        "recall_ratio": None if recall_ratio is None else round(recall_ratio, 4),
        "recall_flag": recall_ratio is not None and recall_ratio < FOUR_FIFTHS,
        "calibration_flag": any(abs(g["calibration_gap"]) >= CALIBRATION_GAP for g in groups),
        "persona_association": _association(rows, attribute, names),
        "within_persona": within,
    }


VERDICT_TEXT = {
    "ok": "Sem disparidade relevante.",
    "atencao": (
        "Há diferença bruta entre grupos, mas ela some quando se compara clientes da mesma "
        "persona: é explicada pelo comportamento (mix de personas), não por tratamento desigual."
    ),
    "alerta": (
        "Clientes da mesma persona recebem tratamento diferente conforme o grupo. "
        "Investigar antes de qualquer uso."
    ),
    "confundido": (
        "Há diferença bruta e não existem clientes de grupos diferentes na mesma persona para "
        "comparar: o atributo praticamente determina a persona nesta base. Não dá para afirmar "
        "nem descartar tratamento desigual. Investigar a origem dos dados."
    ),
    "amostra_insuficiente": "Grupos pequenos demais para comparar com segurança.",
}


def run_audit(records: list[dict]) -> dict:
    """Função pura: recebe um registro por cliente e devolve o relatório."""
    needed = {
        "customer_id",
        "persona",
        "priority_score",
        "churn_risk",
        "churn_observed",
        *ATTRIBUTES,
    }
    if not records:
        raise ValueError("Sem clientes para auditar")
    missing = needed - set(records[0])
    if missing:
        raise ValueError("Registros sem campos: " + ", ".join(sorted(missing)))
    chosen = select_top(records)
    attributes = {a: _attribute_report(records, chosen, a) for a in ATTRIBUTES}
    for report in attributes.values():
        report["verdict_text"] = VERDICT_TEXT[report["verdict"]]
    counts = defaultdict(int)
    for report in attributes.values():
        counts[report["verdict"]] += 1
    return {
        "method": METHOD,
        "synthetic_only": True,
        "settings": {
            "favorable_outcome": f"estar entre os {TOP_SHARE:.0%} mais prioritários",
            "selected_customers": len(chosen),
            "customers": len(records),
            "min_group": MIN_GROUP,
            "min_within_persona": MIN_WITHIN,
            "four_fifths_rule": FOUR_FIFTHS,
            "calibration_gap_threshold": CALIBRATION_GAP,
        },
        "summary": {
            "alerts": counts["alerta"],
            "attention": counts["atencao"],
            "confounded": counts["confundido"],
            "ok": counts["ok"],
            "insufficient": counts["amostra_insuficiente"],
        },
        "attributes": attributes,
        "limitations": [
            "Dados sintéticos: o resultado descreve o gerador, não clientes reais.",
            "A regra dos 4/5 é um alarme, não prova de discriminação nem de ausência dela.",
            "Só os atributos existentes na base foram auditados. Gênero, idade e raça não "
            "existem aqui; com dados reais, auditar também esses atributos com base legal.",
            "Recall e calibração usam o desfecho simulado, não churn real.",
        ],
    }


def build_records(container, store) -> list[dict]:
    """Junta scores, cadastro, fidelidade e desfecho em um registro por cliente."""
    customers = {c.customer_id: c for c in container.crm.customers()}
    tiers = {r["customer_id"]: r.get("tier", "n/d") for r in store.read("loyalty")}
    outcomes = {r["customer_id"]: bool(r["churn"]) for r in store.read("outcomes")}
    scores = container.crm.priorities()
    if not outcomes or any(s.customer_id not in outcomes for s in scores):
        raise ValueError("Desfechos ausentes para a carteira atual. Execute: azul-crm demo")
    records = []
    for score in scores:
        c = customers[score.customer_id]
        records.append(
            {
                "customer_id": score.customer_id,
                "persona": score.segment,
                "priority_score": score.priority_score,
                "churn_risk": score.churn_risk,
                "churn_observed": outcomes[score.customer_id],
                "home_airport": c.home_airport,
                "region": region_of(c.home_airport),
                "preferred_channel": c.preferred_channel,
                "tier": tiers.get(score.customer_id, "n/d"),
            }
        )
    return records


def current_fingerprint(store) -> str:
    return fingerprint(sorted(store.read("features"), key=lambda r: r["customer_id"]))


def write_report(root, container, store) -> dict:
    report = run_audit(build_records(container, store))
    report["gold_fingerprint"] = current_fingerprint(store)
    report["segmenter"] = container.metadata.get("segmenter", "rules")
    digest = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    report["report_sha256"] = digest
    target = root / "artifacts"
    target.mkdir(exist_ok=True)
    (target / "bias_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def load_report(root, store=None) -> dict:
    """Lê o relatório; ``stale`` indica que a Gold mudou depois da auditoria."""
    path = root / "artifacts" / "bias_report.json"
    if not path.exists():
        return {"available": False}
    report = json.loads(path.read_text(encoding="utf-8"))
    stale = False
    if store is not None:
        stale = report.get("gold_fingerprint") != current_fingerprint(store)
    return {"available": True, "stale": stale, **report}
