"""Análise lexical explicável de avaliações; não infere sentimento de clientes."""

import csv
import io
import re
import unicodedata
from collections import Counter
from urllib.parse import urlparse

METHOD = "lexicon_pt_v2_topics_not_validated"
POSITIVE = {
    "bom",
    "boa",
    "otimo",
    "otima",
    "excelente",
    "rapido",
    "rapida",
    "atencioso",
    "atenciosa",
    "pontual",
    "confortavel",
    "satisfeito",
    "satisfeita",
    "recomendo",
    "adorei",
}
NEGATIVE = {
    "ruim",
    "pessimo",
    "pessima",
    "atraso",
    "atrasou",
    "cancelamento",
    "cancelado",
    "cancelada",
    "perdida",
    "extraviada",
    "demora",
    "demorado",
    "insatisfeito",
    "insatisfeita",
    "desrespeito",
    "horrivel",
}
NEGATORS = {"nao", "nunca", "nem", "sem"}
TOPICS = {
    "atraso": ({"atraso", "atrasou", "atrasado", "atrasada"}, "embarque e voo"),
    "cancelamento": (
        {"cancelamento", "cancelado", "cancelada", "cancelaram"},
        "planejamento e operação",
    ),
    "bagagem": ({"bagagem", "mala", "malas", "extraviada", "extravio"}, "despacho e desembarque"),
    "atendimento": (
        {"atendimento", "atendente", "atencioso", "atenciosa", "desrespeito"},
        "atendimento",
    ),
    "check-in": ({"check-in", "checkin", "check in"}, "check-in e embarque"),
    "aplicativo": ({"aplicativo", "app", "aplicacao"}, "compra e autoatendimento digital"),
    "fidelidade": ({"fidelidade", "pontos", "milhas", "resgate"}, "relacionamento e fidelidade"),
}


def analyze_text(text):
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
        raise ValueError("Texto deve conter entre 1 e 4000 caracteres")
    normalized = "".join(
        c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c)
    )
    # Pontuação encerra o escopo da negação.
    evidence = []
    for clause in re.split(r"[.!?;,\n]", normalized):
        words = re.findall(r"[a-z]+", clause)
        for i, word in enumerate(words):
            polarity = 1 if word in POSITIVE else -1 if word in NEGATIVE else 0
            if not polarity:
                continue
            negated = sum(w in NEGATORS for w in words[max(0, i - 3) : i]) % 2 == 1
            polarity *= -1 if negated else 1
            evidence.append({"term": word, "negated": negated, "polarity": polarity})
    positive = sum(e["polarity"] > 0 for e in evidence)
    negative = len(evidence) - positive
    label = (
        "inconclusivo"
        if not evidence
        else "misto"
        if positive and negative
        else "positivo"
        if positive
        else "negativo"
    )
    topics = []
    for name, (keywords, stage) in TOPICS.items():
        matches = sorted(
            word for word in keywords if re.search(r"\b" + re.escape(word) + r"\b", normalized)
        )
        if matches:
            topics.append({"subject": name, "journey_stage": stage, "matched_terms": matches})
    # Intensidade lexical não é confiança estatística nem severidade comprovada.
    intensifiers = {"pessimo", "pessima", "horrivel", "excelente", "adorei"}
    intensity = (
        "inconclusiva"
        if not evidence
        else "alta"
        if any(e["term"] in intensifiers for e in evidence) or len(evidence) >= 3
        else "moderada"
        if len(evidence) == 2
        else "baixa"
    )
    friction = [t["subject"] for t in topics] if negative else []
    return {
        "label": label,
        "topics": topics,
        "intensity": intensity,
        "friction_causes": friction,
        "friction_is_hypothesis": True,
        "score": round((positive - negative) / len(evidence), 3) if evidence else None,
        "evidence": evidence,
    }


def analyze_reviews(reviews):
    if not isinstance(reviews, list) or not 1 <= len(reviews) <= 1000:
        raise ValueError("Informe de 1 a 1000 avaliações")
    rows, seen = [], set()
    for review in reviews:
        review_id = review.get("review_id", "")
        if (
            not isinstance(review_id, str)
            or not review_id.strip()
            or len(review_id) > 100
            or review_id in seen
        ):
            raise ValueError("review_id ausente, duplicado ou maior que 100 caracteres")
        seen.add(review_id)
        synthetic = review.get("is_synthetic")
        if type(synthetic) is not bool:
            raise ValueError("is_synthetic deve ser explicitamente true ou false")
        source = review.get("source_url", "")
        url = urlparse(source)
        if not synthetic and (
            url.scheme != "https" or not url.hostname or url.username or url.password
        ):
            raise ValueError("Avaliação pública exige source_url HTTPS sem credenciais")
        if len(source) > 2000:
            raise ValueError("source_url excede 2000 caracteres")
        rows.append(
            {
                "review_id": review_id,
                "source_url": source,
                "is_synthetic": synthetic,
                **analyze_text(review.get("text")),
            }
        )
    return {
        "method": METHOD,
        "validated_on_real_labels": False,
        "counts": dict(Counter(r["label"] for r in rows)),
        "topic_counts": dict(Counter(t["subject"] for r in rows for t in r["topics"])),
        "friction_counts": dict(Counter(t for r in rows for t in r["friction_causes"])),
        "total": len(rows),
        "synthetic": sum(r["is_synthetic"] for r in rows),
        "reviews": rows,
        "limitations": "Regra lexical em português, sem validação em corpus rotulado. Ironia e contexto podem causar erros. Intensidade é lexical; causas de atrito são hipóteses temáticas, não causalidade ou sentimento por aspecto. Não vincula avaliações a clientes nem altera scores de churn.",
    }


def analyze_csv(content):
    if len(content) > 2 * 1024 * 1024:
        raise ValueError("CSV excede 2 MiB")
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        required = {"review_id", "text", "source_url", "is_synthetic"}
        if not required <= set(reader.fieldnames or []):
            raise ValueError("CSV exige colunas: " + ", ".join(sorted(required)))
        rows = []
        for row in reader:
            if len(rows) >= 1000:
                raise ValueError("CSV excede 1000 avaliações")
            flag = row["is_synthetic"].strip().lower()
            if flag not in {"true", "false"}:
                raise ValueError("is_synthetic deve ser true ou false")
            rows.append({**row, "is_synthetic": flag == "true"})
        return analyze_reviews(rows)
    except (UnicodeError, csv.Error, AttributeError, TypeError) as exc:
        raise ValueError("CSV inválido; use UTF-8 e os campos obrigatórios") from exc
