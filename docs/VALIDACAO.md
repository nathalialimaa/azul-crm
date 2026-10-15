# Validação da atualização Sprint 1 — 15/10/2026

Ambiente Linux, Python 3.12.14. Instalação editável com dependências via pip concluída neste ambiente. Windows não foi executado aqui; comandos PowerShell fornecidos no README.

## Evidências

- Pipeline seed 42: 40 clientes, 589 viagens e 40 features.
- Validador Gold: aprovado, schema 1.0.
- pytest: 15 testes aprovados. Inclui fluxo HTTP TestClient, paginação/erros, determinismo, isolamento temporal, corrupção de features/FKs/flags, janelas e metadata.
- Ruff check e format --check: aprovados.
- OpenAPI e exemplos exportados da aplicação real em docs/api.
- API Uvicorn por HTTP local + Streamlit AppTest: métricas, seleção de cliente, geração de rascunho e filtro aprovados, sem exceções da interface.

Advertência de depreciação Starlette/TestClient com HTTPX: não impediu os testes; revisar compatibilidade das dependências antes da entrega final. Os testes de UI verificam execução e elementos, não revisão visual por screenshot.

## Dependências usadas

- fastapi: 0.143.2
- uvicorn: 0.54.0
- pydantic: 2.13.5
- httpx: 0.28.1
- streamlit: 1.66.0
- pandas: 2.2.3
- pytest: 9.1.1
- ruff: 0.17.1

## Limites

Não foram executados coleta integral de documentos oficiais, ingestão ANAC, calibração, treino ML, SHAP, LLM, deploy ou alteração no GitHub/Linear. As fontes de fidelidade foram localizadas, mas a abertura não forneceu corpo textual completo. Repositório privado, acesso e execução prévia no Windows foram informados por Nathália.

O projeto inclui código, fixtures, contratos, exemplos, guias, CI e testes. Exclui venv, caches e saídas Bronze/Silver/Gold. Execute o pipeline antes de iniciar a API. A CI foi atualizada, mas não acionada no GitHub nesta execução.
