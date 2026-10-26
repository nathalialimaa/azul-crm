"""Smoke real de Uvicorn, Streamlit e fluxo de sentimento. Execute após preparar_anac.py."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for(url, process):
    for _ in range(90):
        if process.poll() is not None:
            raise RuntimeError("Servidor encerrou antes da verificação")
        try:
            response = httpx.get(url, timeout=2)
            if response.status_code == 200:
                return response
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError("Servidor não respondeu no tempo esperado")


def main():
    os.chdir(ROOT)
    os.environ["CRM_PROJECT_ROOT"] = str(ROOT)
    os.environ["CRM_STORAGE"] = "sqlite"
    os.environ["CRM_UI_MODE"] = "local"
    os.environ["CRM_LLM_PROVIDER"] = "local"
    os.environ["CRM_MESSAGE_PROVIDER"] = "template"
    api_port, ui_port = free_port(), free_port()
    processes = []
    flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    report = {}
    try:
        for args, url, key in [
            (
                [
                    "uvicorn",
                    "azul_crm.api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                ],
                f"http://127.0.0.1:{api_port}/health",
                "uvicorn_health",
            ),
            (
                [
                    "streamlit",
                    "run",
                    "streamlit_app.py",
                    "--server.address",
                    "127.0.0.1",
                    "--server.port",
                    str(ui_port),
                    "--server.headless",
                    "true",
                    "--browser.gatherUsageStats",
                    "false",
                ],
                f"http://127.0.0.1:{ui_port}/_stcore/health",
                "streamlit_health",
            ),
        ]:
            proc = subprocess.Popen(
                [sys.executable, "-m", *args],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **flags,
            )
            processes.append(proc)
            report[key] = wait_for(url, proc).status_code
        base = f"http://127.0.0.1:{api_port}/api/v1"
        with httpx.Client(timeout=60) as client:
            dashboard = client.get(base + "/dashboard")
            dashboard.raise_for_status()
            report["customers"] = len(dashboard.json()["rows"])
            cid = dashboard.json()["rows"][0]["customer_id"]
            rec = client.post(base + "/agent/recommend", json={"customer_id": cid})
            rec.raise_for_status()
            assert rec.json()["status"] == "DRAFT_REQUIRES_REVIEW"
            report["recommendation_mode"] = rec.json()["mode"]
            question = client.post(
                base + "/agent/ask", json={"question": "Como funciona o score de valor?"}
            )
            question.raise_for_status()
            assert question.json()["evidence"]
            report["assistant_evidence"] = len(question.json()["evidence"])
        os.environ["CRM_UI_MODE"] = "http"
        os.environ["CRM_API_URL"] = f"http://127.0.0.1:{api_port}"
        from frontend.gateway import Gateway

        result = Gateway().sentiment((ROOT / "data/fixtures/reviews.csv").read_bytes())
        assert result["total"] == 5 and result["counts"]["negativo"] == 2
        report["sentiment_http_gateway"] = result["counts"]
        os.environ["CRM_UI_MODE"] = "local"
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=180).run()
        assert not app.exception and not app.error, "Erro ao abrir a interface"
        pages = list(app.sidebar.radio[0].options)
        for page in pages:
            app.sidebar.radio[0].set_value(page).run()
            assert not app.exception and not app.error, f"Erro na página {page}"
        app.sidebar.radio[0].set_value("Sentimento").run()
        button = next(b for b in app.button if b.label == "Analisar avaliações")
        button.click().run()
        assert not app.exception and not app.error and app.json, "Sentimento não executou na UI"
        report["streamlit_pages"] = pages
        report["sentiment_ui"] = "ok"
        report["status"] = "ok"
        output = ROOT / "docs/evidencias/integracao/smoke.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        for process in processes:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
