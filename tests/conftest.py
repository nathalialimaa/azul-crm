from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from azul_crm.api.main import create_app
from azul_crm.bootstrap import build_container
from azul_crm.infrastructure.settings import Settings
from azul_crm.pipeline.stages import DemoSyntheticGenerator, GoldPublisher


@pytest.fixture
def root(tmp_path):
    import shutil

    source = Path(__file__).resolve().parents[1]
    shutil.copytree(source / "config", tmp_path / "config")
    shutil.copytree(source / "data/fixtures", tmp_path / "data/fixtures")
    customers, trips = DemoSyntheticGenerator().generate(
        [{"origin": "REC", "destination": "GRU", "mean_fare": 950}],
        12,
        42,
        date(2025, 10, 1),
        date(2026, 9, 30),
    )
    GoldPublisher().publish(
        tmp_path / "data/gold", customers, trips, 42, date(2025, 10, 1), date(2026, 9, 30)
    )
    return tmp_path


@pytest.fixture
def client(root):
    with TestClient(create_app(build_container(Settings(root)))) as client:
        yield client


@pytest.fixture(autouse=True)
def isolate_external_llm(monkeypatch):
    """A suíte nunca usa a chave local nem chama provedores externos implicitamente."""
    monkeypatch.setenv("CRM_LLM_PROVIDER", "local")
    monkeypatch.setenv("CRM_MESSAGE_PROVIDER", "template")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
