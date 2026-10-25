"""Confere a base de conhecimento depois de importar um documento (por exemplo, o regulamento).

Uso, na pasta do projeto e com o ambiente virtual ativo:
    python scripts/verificar_base_conhecimento.py

Sai com código 1 se algo essencial falhar. Não altera nenhum arquivo.
"""

import sys
from collections import Counter

from azul_crm.infrastructure.rag import DocumentIndex
from azul_crm.infrastructure.settings import Settings

GOVERNANCE_QUERY = "relacionamento contato sem benefício"
GOVERNANCE_SOURCE = "internal://catalogo-acoes-mvp"
QUESTIONS = [
    "Como acumulo pontos?",
    "Quando os pontos expiram?",
    "Qual é a regra de upgrade?",
    "Quais são os níveis do programa?",
    "Posso prometer bônus de pontos ao cliente?",
    "O que é alto valor?",
    "xyzzy zqxw plasma",
]


def provenance_label(is_demo: bool) -> str:
    return "demonstração" if is_demo else "público/importado"


def ask(index, questions) -> None:
    for question in questions:
        answer = index.answer(question)
        ids = [e["document_id"] for e in answer["evidence"]]
        print(f"\nPERGUNTA: {question}\n  fontes: {ids or 'nenhuma (abstenção)'}")
        for line in answer["answer"].splitlines()[:6]:
            print("  " + line[:300])


def main() -> int:
    root = Settings.load().root
    index = DocumentIndex(root)
    failures = []
    if len(sys.argv) > 1:  # perguntas passadas na linha de comando: só responde e sai
        ask(index, sys.argv[1:])
        return 0

    print("== Documentos na base")
    per_document = Counter(c.document_id.split("#")[0] for c in index.chunks)
    sources = {c.document_id.split("#")[0]: (c.source, c.is_demo) for c in index.chunks}
    for name, count in per_document.items():
        source, demo = sources[name]
        print(
            f"  {name:<28} {count:>3} trechos | {provenance_label(demo)} | {source[:60]}"
        )
    print(f"  total: {len(index.chunks)} trechos")

    print("\n== Busca de governança (o que a recomendação usa)")
    found = index.retrieve(GOVERNANCE_QUERY)
    print("  devolve:", [e.document_id for e in found])
    if not found or found[0].source != GOVERNANCE_SOURCE:
        failures.append("o trecho do catálogo não é o primeiro da busca de governança")

    print("\n== Perguntas ao Assistente IA")
    for question in QUESTIONS:
        answer = index.answer(question)
        ids = [e["document_id"] for e in answer["evidence"]]
        first = answer["answer"].replace("\n", " ")[:110]
        print(f"  {question}\n     fontes: {ids or 'nenhuma (abstenção)'}\n     {first}")
    if index.answer(QUESTIONS[-1])["evidence"]:
        failures.append("a pergunta sem sentido deveria resultar em abstenção")

    try:
        from azul_crm.bootstrap import build_container

        container = build_container(Settings.load())
        customers = container.crm.customers()[:10]
        codes = [container.recommendations.recommend(c.customer_id).action.code for c in customers]
        print("\n== Recomendações de", len(codes), "clientes:", dict(Counter(codes)))
        if "NO_ACTION" in codes:
            failures.append("há recomendações sem ação (NO_ACTION)")
    except Exception as exc:  # base ainda não gerada, por exemplo
        print("\n== Recomendações puladas:", type(exc).__name__, str(exc)[:100])

    print("\nRESULTADO:", "FALHOU: " + "; ".join(failures) if failures else "OK")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
