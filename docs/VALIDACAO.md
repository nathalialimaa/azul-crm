# Verificação da entrega

Executada em 14/10/2026, Linux, Python 3.12.14.

| Dependência | Versão disponível e usada |
|---|---|
| fastapi | 0.143.1 |
| uvicorn | 0.54.0 |
| pydantic | 2.13.5 |
| httpx | 0.28.1 |
| streamlit | 1.66.0 |
| pandas | 2.2.3 |
| pytest | 9.1.1 |
| ruff | 0.17.0 |

## Resultado

- Instalação editável do pacote local concluída, utilizando dependências já presentes no ambiente (`--no-deps --no-build-isolation`). A instalação do zero pela internet não foi executada.
- Pipeline de demonstração: 40 clientes, 589 viagens, seed 42; Bronze, Silver, Gold, features e manifest gerados.
- `python -m pytest -q`: **5 testes passaram**.
- `python -m ruff check .`: passou.
- `python -m ruff format --check .`: passou.
- API real com Uvicorn: saúde e listagem de 40 prioridades confirmadas via HTTP local.
- Streamlit AppTest conectado à API real: renderização sem exceções, três indicadores, tabela de prioridades, histórico de viagens, filtro de segmento e geração do rascunho confirmados.

Os testes automatizados cobrem contrato e fluxo da API, ordenação da prioridade, 404/422, filtro sem resultados, paginação, determinismo do gerador, isolamento temporal das features e bloqueio de ação sem evidência.

O ambiente emitiu uma advertência de depreciação da combinação TestClient/HTTPX do Starlette. Ela não impediu os testes. Rever compatibilidade e fixar versões ao preparar a entrega final do time.

Não foram executados coleta pública, treinamento, SHAP, indexação semântica, chamada a LLM, deploy remoto, criação do GitHub ou execução no Windows. O workflow CI é fornecido para rodar no repositório; não foi acionado no GitHub nesta entrega. A versão 3.11 é o alvo de CI, e a execução local deste relatório usou 3.12.

## Conteúdo do ZIP

Código-fonte, configurações sem segredos, fixtures pequenas, testes, CI, README e documentação. As saídas geradas em Bronze/Silver/Gold, caches, ambientes virtuais e arquivos de instalação foram excluídos. Execute o pipeline na primeira utilização.
