"""Entrada de deploy privado; inicializa apenas a demonstração SQLite ausente."""

import os
import runpy

from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store

settings = Settings.load()
if os.getenv("CRM_STORAGE", "sqlite") == "sqlite" and not Store(settings.root).read("manifest"):
    from azul_crm.pipeline.extended import generate

    generate(settings, 400, 42)
runpy.run_path(str(settings.root / "frontend/app.py"), run_name="__main__")
