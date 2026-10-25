"""Página Clientes: a fidelidade simulada precisa fechar a conta e seguir a regra pública de acúmulo."""

import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.demo import prepare_demo

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def base(tmp_path, monkeypatch):
    for name in ["config", "data/fixtures", "data/knowledge", "frontend"]:
        shutil.copytree(REPO / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(REPO / "streamlit_app.py", tmp_path / "streamlit_app.py")
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    prepare_demo(Settings(tmp_path), customers=120)
    return tmp_path, Store(tmp_path)


def test_points_accrue_one_per_real_and_the_balance_adds_up(base):
    _, store = base
    spend = {f["customer_id"]: f["spend"] for f in store.read("features")}
    for row in store.read("loyalty"):
        assert row["earned"] == round(spend[row["customer_id"]])  # 1 ponto por R$ 1,00 (item 5.5.3)
        assert row["balance"] == row["opening_points"] + row["earned"] - row["redeemed"]


def test_customer_page_shows_the_opening_balance_and_lists_the_factors(base):
    import streamlit as st

    root, store = base
    st.cache_resource.clear()
    at = AppTest.from_file(str(root / "streamlit_app.py"), default_timeout=180).run()
    at.sidebar.radio[0].set_value("Clientes").run()
    assert not at.exception, [e.value for e in at.exception]

    labels = {m.label for m in at.metric}
    assert {"Saldo inicial (simulado)", "Pontos acumulados", "Pontos resgatados", "Saldo"} <= labels
    captions = " ".join(c.value for c in at.caption)
    assert "5.5.3" in captions and "saldo inicial simulado" in captions
    items = [m.value for m in at.markdown if m.value.startswith("- ")]
    assert len(items) >= 3 and any(
        "Gasto observado" in item for item in items
    )  # lista, e não uma tupla
