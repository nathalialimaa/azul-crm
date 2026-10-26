"""Teste real opcional; exige GEMINI_API_KEY no .env. Não imprime credenciais."""

import json

from azul_crm.application.assistant import answer_question
from azul_crm.bootstrap import build_container
from azul_crm.infrastructure.settings import Settings


def main():
    settings = Settings.load()
    container = build_container(settings)
    cid = container.crm.priorities()[0].customer_id
    answer = answer_question(
        container,
        settings.root,
        "Quais são as principais oportunidades de retenção desta carteira e por onde começar?",
        cid,
    )
    rec = container.recommendations.recommend(cid)
    report = {
        "assistant": answer,
        "message": {"customer_id": cid, "mode": rec.mode, "draft": rec.draft},
        "real_assistant_passed": answer["mode"] == "gemini_grounded",
        "real_message_passed": "Gerado por Gemini" in rec.draft,
    }
    out = settings.root / "docs/evidencias/gemini"
    out.mkdir(parents=True, exist_ok=True)
    (out / "validacao-real.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: report[k] for k in ("real_assistant_passed", "real_message_passed")}, indent=2
        )
    )
    if not report["real_assistant_passed"] or not report["real_message_passed"]:
        raise SystemExit("Verificação real incompleta; veja a evidência sanitizada.")


if __name__ == "__main__":
    main()
