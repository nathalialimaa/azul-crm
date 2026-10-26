# Consolidação das três versões — 26/10/2026

## Fontes e comparação

| Pacote | Resultado da comparação | Decisão |
|---|---|---|
| develop de Luan | Base funcional: API, Streamlit, personas, CLV, lake e revisão humana | Preservada pela integração do histórico |
| docs/entrega-final-pitch de Luan | Mesmo código de develop, com nove documentos adicionais | Organização do pitch incorporada |
| chore/dados-publicos-anac de Nathália | Dados ANAC empacotados, preparo offline, correções de calibração, decisões e reparo dos artefatos | Base funcional mantida |

As branches chore e docs tinham históricos sem ancestral comum. A integração conserva os dois históricos, resolve os arquivos comuns com a versão corrigida do chore e incorpora o pacote documental do pitch. Os arquivos ZIP originais não foram modificados.

## Correções e funcionalidades desta consolidação

- Configuração `.gitattributes` preserva os bytes dos dados públicos. O clone no Windows convertia o CSV de aeroportos, invalidava o SHA-256 e impedia `preparar_anac.py`.
- Análise lexical de sentimento em português com negação, evidências, resultados positivos/negativos/mistos/inconclusivos, fonte pública obrigatória e identificação explícita de dados sintéticos.
- Sentimento integrado à API, CLI, gateway local/HTTP e navegação Streamlit. Não associa opiniões públicas a clientes sintéticos e não altera churn.
- Composição opcional por Ollama com abertura/encerramento de catálogo e conteúdo factual do playbook. Validação de IDs/citações e fallback para template. Não equivale à redação livre por LLM ou à homologação semântica.
- Documentação de entrega e pitch integrada; resultados anteriores são históricos e não substituem os logs desta execução.

## Execução

Na raiz do projeto, usando Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts/preparar_anac.py
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

O preparo ANAC recria somente a base desta cópia de demonstração e limpa decisões anteriores. Na inicialização normal, o app preserva a base e repara artefatos incompatíveis.

Sentimento:

```powershell
.\.venv\Scripts\python.exe -m azul_crm.cli sentiment --file data/fixtures/reviews.csv
```

CSV UTF-8 com `review_id,text,source_url,is_synthetic`. Limites: 2 MiB, 1000 avaliações, 4000 caracteres por texto. `is_synthetic` aceita `true` ou `false`; fonte pública exige URL HTTPS. A URL é registrada, sem download ou comprovação de autenticidade. O relatório não armazena o texto integral, somente identificadores e termos explicativos. O classificador é heurístico, sem avaliação em corpus real rotulado; sarcasmo e contexto exigem revisão.

API: `POST /api/v1/sentiment/analyze`, corpo `{"reviews": [{"review_id": "demo", "text": "Atendimento excelente", "source_url": "", "is_synthetic": true}]}`.

Para a composição opcional de mensagens, configure `CRM_MESSAGE_PROVIDER=ollama`, `OLLAMA_BASE_URL` e `OLLAMA_MODEL`. A busca pode continuar local com `RAG_PROVIDER=local`. Para busca semântica também por Ollama, use `RAG_PROVIDER=ollama` e reconstrua o índice com `azul-crm index`. A configuração padrão segue local e não depende do serviço externo.

## Requisitos e pendências

Os dois documentos originais enviados via Drive foram lidos integralmente em 26/10/2026: enunciado com quatro páginas e proposta com 25 seções. A matriz `VALIDACAO.md` foi reescrita com referências corretas, distinguindo o núcleo obrigatório dos diferenciais. A versão anterior apontava páginas inexistentes. Os originais ficam fora do repositório; hashes registram a proveniência.

| Item | Estado |
|---|---|
| Integração develop + chore + pitch | Implementada |
| ANAC offline reproduzível | Validado com 892.505 tarifas, VRA e 400 clientes sintéticos |
| CLV, churn, personas, lake, revisão humana | Preservados; 213 testes passaram |
| Sentimento | Implementado como baseline explicável; exemplo sintético, sem corpus público real validado |
| LLM em mensagens | Adaptador limitado implementado; serviço/modelo real indisponível nesta máquina |
| Snowflake | Conector existente; conta e homologação externa pendentes |
| Benefícios/vigência do Azul Fidelidade | Documento importado para consulta; não habilita benefícios oficiais |
| Shapley/SHAP com referência única | Implementado por enumeração exata para os scores ativos; API e visão 360 |
| Hospedagem, avaliadores, vídeo e submissão | Entregas externas sem evidência de execução |
| Regulamento CRM e proposta original | Ambos lidos; matriz final corrigida e lacunas classificadas |

## Resultados desta execução

- Python 3.12.10 no Windows, dependências em ambiente virtual isolado.
- `pytest -q --tb=short`: **213 testes passaram em 368,43 segundos**. Um aviso de depreciação Starlette/httpx; sem falhas.
- `ruff check .`: passou.
- Exportação de contratos OpenAPI/exemplos: passou após a geração da Gold.
- Pipeline ANAC completo: **status ok**. 86.281 aeroportos, 892.505 tarifas (45 sem aeroporto correspondente), 88.040 registros VRA dentro do período, 24 rejeitados fora do período, 87.996 linhas Silver de operações.
- Carteira: **400 clientes sintéticos e 6.046 viagens**, calibradas com dados públicos. Validação SQL válida.
- Churn: regra heurística mantida pelo critério estatístico. Nenhuma alegação de previsão real.
- Personas: quatro grupos, com 173, 103, 26 e 98 clientes.
- CLV: 80 clientes de alto valor, 37 em risco; métricas de demonstração sob hipóteses de margem/desconto.
- Lake: **17 tabelas exportadas**, decisões vazias nesta execução.
- Servidores Uvicorn e Streamlit: **HTTP 200** em localhost.
- API de recomendações: rascunho revisável; assistente retorna evidência.
- Gateway HTTP de sentimento e **oito páginas do Streamlit**: passaram, incluindo executar a análise sintética no painel.
- Testes novos de sentimento e composição limitada: **18 passaram**; Ollama testado com respostas simuladas, sem modelo real instalado.

Evidências: `docs/evidencias/integracao/pytest.log`, `pipeline-anac.log`, `smoke.json`, `novas-funcionalidades.log`, `ruff.log`, `dependencias.txt` e `comparacao-pacotes.json`. A primeira tentativa do smoke falhou por caminho de importação do script; o script foi corrigido e a execução subsequente está comprovada por `smoke.json`.

Branch de entrega: `integracao/consolidacao-crm-2026-10-26`. Privacidade do repositório e permissão de push verificadas pela API do GitHub antes da publicação.


## Ajustes após a leitura dos originais

- Sentimento agora informa os sete assuntos da proposta, etapa da jornada, intensidade lexical e hipóteses de atrito; apresenta contagens agregadas e continua sem vincular opiniões a clientes.
- Recomendações recuperam contexto público de comunicação do regulamento do Azul Fidelidade, além da governança e do playbook. Isso não habilita benefícios ou comprova consentimento individual.
- A explicação exata de Shapley foi implementada para os scores ativos, com referência única explícita, testes de aditividade e API/visão 360.
- A matriz final identifica como parciais o agente LLM completo, validação de sentimento com corpus real e homologações externas. Nenhuma dessas lacunas foi escondida como “100% entregue”.
- O PDF exige repositório privado, acesso ao protótipo, vídeo e submissão; o código não realiza essas duas últimas entregas pela equipe.


## Validação final após os dois documentos originais

- Suíte completa final: **225 testes passaram em 392,88 segundos**, com um aviso de depreciação Starlette/httpx e nenhuma falha (`pytest-final.log`).
- Testes direcionados de requisitos: 72 passaram; explicações/visão Clientes: 5 passaram; consistência documental: 6 passaram.
- Lint final passou (`ruff-final.log`). Contratos reexportados.
- Smoke final: Uvicorn e Streamlit HTTP 200, 400 clientes, recomendações revisáveis, assistente com evidência, sentimento por gateway HTTP e oito páginas sem erro (`smoke.json`).
- O pipeline ANAC completo já havia passado e não foi repetido, pois seus dados e ingestores não mudaram.
- Documentos originais não foram incluídos no repositório; apenas a análise e seus hashes.
- Repositório privado confirmado antes do push. Branch: `integracao/consolidacao-crm-2026-10-26`.


## Evolução Flight Deck e Gemini

Branch `feat/gemini-experiencia-azul`: tema responsivo Azul Flight Deck, fonte local, README reorganizado, tarefas/depuração VS Code, Gemini para copiloto e mensagens originais com citações, preview sem geração remota, rascunhos identificados para revisão e contingência explícita. A chave permanece somente no `.env` local ignorado pelo Git.

Regressão: 243 testes passaram. Após os últimos ajustes, 43 testes direcionados passaram, e uma conferência final de documentação/Gemini passou em 27 testes (conjuntos parcialmente sobrepostos; não somar as contagens). API e oito páginas verificadas. A API Google apresentou sobrecarga HTTP 503 em chamadas completas; esta dependência externa continua registrada, sem alegação de LLM sempre disponível. Guias atuais: `GEMINI.md`, `DESIGN.md` e README.
