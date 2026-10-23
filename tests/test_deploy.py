import json
import shutil
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from azul_crm.bootstrap import build_container
from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store
from azul_crm.pipeline.demo import prepare_demo

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def root(tmp_path, monkeypatch):
    for name in ["config", "data/fixtures", "data/knowledge", "frontend"]:
        shutil.copytree(REPO / name, tmp_path / name)
    shutil.copy(REPO / "streamlit_app.py", tmp_path / "streamlit_app.py")
    monkeypatch.setenv("CRM_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CRM_STORAGE", "sqlite")
    monkeypatch.setenv("RAG_PROVIDER", "local")
    monkeypatch.delenv("CRM_APP_PASSWORD", raising=False)
    return tmp_path


def test_prepare_builds_everything_once_and_is_idempotent(root):
    result = prepare_demo(Settings(root), customers=120)
    assert result["steps"] == ["generate", "train", "personas", "scores+bias"]
    assert result["segmenter"] == "kmeans_personas_v1" and result["playbook"] == "playbook_v1"
    for name in [
        "churn.json",
        "metrics.json",
        "personas.json",
        "bias_report.json",
        "clv_report.json",
    ]:
        assert (root / "artifacts" / name).exists()
    assert len(Store(root).read("scores")) == 120
    assert prepare_demo(Settings(root), customers=120)["steps"] == []


def test_prepare_repairs_only_what_is_missing(root):
    prepare_demo(Settings(root), customers=120)
    (root / "artifacts/personas.json").unlink()
    (root / "artifacts/bias_report.json").unlink()
    assert prepare_demo(Settings(root), customers=120)["steps"] == ["personas", "scores+bias"]
    assert build_container(Settings(root)).metadata["segmenter"] == "kmeans_personas_v1"


def test_prepare_regenerates_when_artifacts_do_not_match_the_data(root):
    prepare_demo(Settings(root), customers=120)
    path = root / "artifacts/personas.json"
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["gold_fingerprint"] = "0" * 64
    path.write_text(json.dumps(artifact), encoding="utf-8")
    result = prepare_demo(Settings(root), customers=120)
    assert "generate" in result["steps"] and result["segmenter"] == "kmeans_personas_v1"


def test_prepare_refuses_to_generate_synthetic_data_into_snowflake(root, monkeypatch):
    monkeypatch.setenv("CRM_STORAGE", "snowflake")
    with pytest.raises(ValueError, match="sqlite"):
        prepare_demo(Settings(root))


def test_cli_prepare_command(root, monkeypatch, capsys):
    from azul_crm import cli

    monkeypatch.setattr(sys, "argv", ["azul-crm", "prepare", "--customers", "120"])
    cli.main()
    assert json.loads(capsys.readouterr().out)["customers"] == 120


def run_app(root, password=None, monkeypatch=None):
    import streamlit as st

    st.cache_resource.clear()
    if password is not None:
        monkeypatch.setenv("CRM_APP_PASSWORD", password)
    return AppTest.from_file(str(root / "streamlit_app.py"), default_timeout=180).run()


def test_app_opens_directly_when_no_password_is_configured(root):
    at = run_app(root)
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.sidebar.radio) == 1  # navegação do app
    assert (root / "artifacts/personas.json").exists()  # preparou sozinho


def test_password_gate_blocks_wrong_and_accepts_right_password(root, monkeypatch):
    at = run_app(root, "segredo-de-teste", monkeypatch)
    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value == "Acesso restrito" and len(at.sidebar.radio) == 0

    at.text_input[0].set_value("errada").run()
    at.button[0].click().run()
    assert at.error[0].value == "Senha incorreta." and len(at.sidebar.radio) == 0

    at.text_input[0].set_value("segredo-de-teste").run()
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["crm_authenticated"] is True and len(at.sidebar.radio) == 1


def test_dockerignore_keeps_data_and_secrets_out_of_the_image():
    ignored = set((REPO / ".dockerignore").read_text(encoding="utf-8").split())
    for pattern in [".env", "data/*.sqlite3", "artifacts", "data/gold", ".streamlit/secrets.toml"]:
        assert pattern in ignored, pattern
