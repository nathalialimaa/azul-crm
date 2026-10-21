FROM python:3.12-slim
WORKDIR /app
ENV CRM_PROJECT_ROOT=/app
COPY . .
RUN pip install --no-cache-dir .
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
