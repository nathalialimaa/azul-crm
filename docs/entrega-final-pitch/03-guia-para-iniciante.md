# Guia para iniciante

## Por que existe

Permite entender e demonstrar o MVP sem conhecer a arquitetura inteira ou assumir acesso a dados da empresa.

## Termos essenciais

- **MVP:** primeira versão funcional para validar uma ideia.
- **CLV:** valor estimado que um cliente gera ao longo de um período.
- **Churn:** evasão, ou risco de o cliente deixar de comprar/voar.
- **Persona:** grupo de clientes com características semelhantes.
- **API:** interface que permite a programas trocar dados.
- **Streamlit:** framework Python usado para a interface visual.
- **CI:** verificação automática do repositório.
- **RAG:** recuperação de trechos relevantes antes de responder.
- **Groundedness:** quanto uma resposta está apoiada em evidências, não em invenção.
- **Fail-closed:** bloquear quando falta consentimento ou evidência.

## Primeira demonstração local

Na raiz do repositório, com Python 3.11–3.13 e ambiente virtual:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

Abra `http://127.0.0.1:8501`. A primeira execução prepara uma base sintética. Mostre visão geral, cliente, fatores/evidências, checklist de revisão, segmentos e limitações. Nenhuma mensagem é enviada.

## Como testar com segurança

Use somente SQLite local, `127.0.0.1` e dados sintéticos. Não compartilhe `.env`, não cole credenciais, não exponha a API e não use a demonstração para afirmar Snowflake, Ollama real, corpus oficial ou dados reais. Para a explicação completa, consulte [`../../README.md`](../../README.md).
