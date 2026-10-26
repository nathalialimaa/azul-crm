# Requisitos e evidências

| Capacidade | Implementação | Evidência |
|---|---|---|
| Alto valor, risco e CLV | domain/clv.py, domain/scoring.py, pipeline/modeling.py | test_clv.py, test_model_selection.py |
| Personas e ações | pipeline/personas.py, config/playbook.toml | test_personas.py, test_playbook.py |
| Dados públicos e carteira sintética | pipeline/public_data.py, pipeline/extended.py | test_public_demand.py, test_vra_delays.py, execução real do preparo ANAC |
| Lake e dicionário | infrastructure/lake.py | test_lake.py e exportação real em Parquet |
| Assistente com evidências | infrastructure/rag.py | test_big_knowledge.py, test_knowledge.py e smoke HTTP |
| Composição limitada opcional por LLM | infrastructure/message_agent.py | test_message_agent.py com HTTP simulado; sem inferência real |
| Sentimento explicável | application/sentiment.py, API/CLI/painel | test_sentiment.py, smoke HTTP e Streamlit; fixture sintética |
| Revisão humana e consentimento | application/recommendations.py, API/gateway | test_consent_checklist.py |
| Protótipo | frontend/app.py e FastAPI | oito páginas e servidores reais no smoke |

Todos os caminhos de código da tabela são relativos a `src/azul_crm`, exceto frontend/config/tests. A classificação completa e suas limitações estão em [CONSOLIDACAO.md](../CONSOLIDACAO.md). Esta lista não substitui a leitura dos documentos originais do desafio e da proposta, ainda pendentes de reenvio.
