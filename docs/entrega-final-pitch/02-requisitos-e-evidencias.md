> Integração Gemini/Flight Deck: veja [GEMINI.md](../GEMINI.md), [DESIGN.md](../DESIGN.md) e o [README atualizado](../../README.md). Os estados e limites mais recentes estão nesses guias.

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
| Shapley exato | application/explanations.py | test_explanations.py e visão 360 |
| Protótipo | frontend/app.py e FastAPI | oito páginas e servidores reais no smoke |

Todos os caminhos de código da tabela são relativos a `src/azul_crm`, exceto frontend/config/tests. A classificação completa e suas limitações estão em [CONSOLIDACAO.md](../CONSOLIDACAO.md). A leitura dos dois originais está registrada na matriz final em [VALIDACAO.md](../VALIDACAO.md).
