"""Prepara a demonstração completa de forma idempotente (dados, modelo, personas e auditoria).

Pensado para a subida do app em qualquer hospedagem: se tudo já existe, não faz nada; se falta
algum artefato, refaz só o que falta; se artefatos e dados não combinam (por exemplo, um disco
com base antiga), regenera tudo uma vez em vez de subir uma demonstração inconsistente.
"""

from dataclasses import asdict

from azul_crm.infrastructure.store import Store


def prepare_demo(settings, customers=400, seed=42, force=False, _retry=True) -> dict:
    from azul_crm.bootstrap import build_container
    from azul_crm.pipeline.bias_audit import write_report
    from azul_crm.pipeline.clv_report import write_clv_report
    from azul_crm.pipeline.extended import generate
    from azul_crm.pipeline.modeling import train
    from azul_crm.pipeline.personas import train_personas

    root = settings.root
    store = Store(root)
    if store.backend != "sqlite":
        raise ValueError("prepare_demo gera dados sintéticos e só roda com CRM_STORAGE=sqlite")
    artifacts = root / "artifacts"
    steps = []

    if force or not store.read("manifest"):
        generate(settings, customers, seed)  # também apaga artefatos de uma base anterior
        steps.append("generate")
    if not (artifacts / "churn.json").exists():
        train(root, store, seed)
        steps.append("train")
    if not (artifacts / "personas.json").exists():
        train_personas(root, store, seed)
        steps.append("personas")
    try:
        container = build_container(settings)
    except ValueError:
        if not _retry:
            raise
        return prepare_demo(settings, customers, seed, force=True, _retry=False)
    if steps or not all((artifacts / n).exists() for n in ("bias_report.json", "clv_report.json")):
        store.publish({"scores": [(r.customer_id, asdict(r)) for r in container.crm.priorities()]})
        write_report(root, container, store)
        write_clv_report(root, container, store)
        steps.append("scores+bias")
    return {
        "steps": steps,
        "customers": container.metadata["customer_count"],
        "segmenter": container.metadata["segmenter"],
        "playbook": container.metadata["playbook"],
    }
