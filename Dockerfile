FROM python:3.12-slim

ENV CRM_PROJECT_ROOT=/app \
    CRM_STORAGE=sqlite \
    RAG_PROVIDER=local \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 app \
    && python -m azul_crm.cli prepare > /dev/null \
    && chown -R app:app /app
USER app

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')"

# Defina CRM_APP_PASSWORD no ambiente da hospedagem (nunca no Dockerfile nem no Git).
CMD ["python", "-m", "streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
