# Matriz de requisitos e validação — `develop@5d7fafc`

Atualizado em 25/10/2026. Fonte oficial dos requisitos: `IntrucoesHackathonAzul.pdf`, páginas 2–9.

## Critério de leitura

`Comprovado localmente` significa que há implementação e evidência reproduzível no repositório/CI. `Parcialmente comprovado` significa que o caminho existe, mas depende de premissa sintética, cobertura limitada ou serviço não exercitado. `Não homologado` significa que não há evidência suficiente para declarar a capacidade. `Bloqueado externamente` significa que a prova depende de conta, acesso, publicação ou dado fora do repositório.

## Matriz requisito → implementação → evidência/teste → status

| Requisito oficial | Implementação no commit | Evidência/teste reproduzível | Status |
|---|---|---|---|
| MVP que identifica clientes de alto valor e propõe retenção (PDF, p. 2–3) | Score de valor, risco, CLV de 12 meses, personas e playbook por persona em `src/azul_crm/application/`, `src/azul_crm/domain/` e `config/playbook.toml`; UI em `frontend/app.py` | `tests/test_clv.py`, `tests/test_personas.py`, `tests/test_playbook.py`, `tests/test_integrated.py`; `python -m azul_crm.pipeline.cli demo` | **Parcialmente comprovado**: a base é sintética e ofertas são hipóteses, não estratégia homologada com clientes reais |
| Base sintética calibrada por padrões públicos de rota, tarifa e demanda; nenhum dado real de cliente (PDF, p. 3–4) | Geração sintética em `src/azul_crm/pipeline/extended.py`; ingestão ANAC em `src/azul_crm/pipeline/public_data.py` e `src/azul_crm/pipeline/delays.py`; campo `is_synthetic` | `tests/test_public_demand.py`, `tests/test_vra_delays.py`, `tests/test_integrated.py::test_training_and_future_leakage`, `tests/test_bias_audit.py`; `python -m azul_crm.pipeline.cli validate` | **Parcialmente comprovado**: há evidência de arquivos públicos ANAC usados anteriormente e de geração sintética; não é prova de dado interno Azul |
| Modelos de valor/CLV e risco de evasão com explicabilidade (PDF, p. 3 e 7) | `src/azul_crm/domain/clv.py`, `src/azul_crm/pipeline/modeling.py`, `src/azul_crm/application/features.py`; explicações lineares/drivers na API e UI | `tests/test_clv.py`, `tests/test_model_selection.py`, `tests/test_knowledge.py`; resultados em `artifacts/metrics.json` quando gerados | **Parcialmente comprovado**: métricas são de dados sintéticos e a explicação não é SHAP |
| Segmentação orientada por dados, com perfis distintos (PDF, p. 3 e 7) | K-means em `src/azul_crm/pipeline/personas.py`, artefatos e endpoint `/api/v1/personas` | `tests/test_personas.py`, `tests/test_deploy.py`, `tests/test_lake.py` | **Comprovado localmente** para a base sintética e quatro personas; não equivale a validação em clientes reais |
| Agente/LLM que recomende e redija ações apoiado em regras públicas do Azul Fidelidade (PDF, p. 3) | Contrato e adaptador em `src/azul_crm/infrastructure/rag.py`; recomendações atuais usam templates/playbook em `src/azul_crm/application/recommendations.py` | `tests/test_flow.py`, `tests/test_big_knowledge.py`, `tests/test_knowledge.py`, `tests/test_integrated.py::test_ollama_rejects_invalid_grounded_answer` | **Não homologado**: Ollama real não foi executado, o rascunho é template e groundedness não foi avaliado |
| Análise de sentimento em avaliações públicas (PDF, p. 3) | Não há pipeline de sentimento implementado; fontes públicas de reclamações/redes não são ingeridas | Ausência de implementação/teste correspondente; não declarar como entregue | **Não homologado** |
| Arquitetura adaptável a uma implementação real, com decisões e premissas documentadas (PDF, p. 4) | Portas/adaptadores, configuração, esquemas e premissas em `src/azul_crm/`, `docs/ARQUITETURA.md`, `docs/DATA_LAKE.md` e `docs/DEPENDENCIAS.md` | `tests/test_deploy.py`, `tests/test_lake.py`; comandos de CI em `.github/workflows/ci.yml` | **Parcialmente comprovado**: a separação é executável localmente, mas integrações produtivas não foram homologadas |
| Data lake em camadas, formatos abertos, esquemas, dicionário e pipelines reproduzíveis (PDF, p. 5) | Bronze/silver/gold em `src/azul_crm/infrastructure/lake.py`, Parquet, registro de schema e DDL | `tests/test_lake.py::test_schema_registry_is_consistent`, `test_dictionary_describes_every_table_and_column`, `test_export_is_deterministic_and_reflects_the_data`; `python -m azul_crm.cli prepare --customers 120` | **Comprovado localmente** para SQLite/Parquet e dados sintéticos |
| Snowflake como caminho de continuidade (PDF, p. 5) | DDL/conector em `src/azul_crm/infrastructure/lake.py` e configurações em `src/azul_crm/infrastructure/settings.py` | `tests/test_lake.py::test_snowflake_ddl_is_typed_and_explicit_about_being_untested`; não há conta/execução real | **Bloqueado externamente**: Snowflake real não está homologado |
| Uso inteligente de fontes públicas sugeridas, incluindo ANAC e Azul Fidelidade (PDF, p. 6 e 8) | Ingestão ANAC em `src/azul_crm/pipeline/public_data.py`; conhecimento em `data/knowledge/`; rótulos de demonstração/proveniência em `scripts/verificar_base_conhecimento.py` | `tests/test_public_demand.py`, `tests/test_vra_delays.py`, `tests/test_verificar_base_conhecimento.py`, `scripts/verificar_base_conhecimento.py` | **Parcialmente comprovado**: ANAC pública foi usada; o corpus Azul Fidelidade é público/importado, mas sua vigência, autorização e homologação não foram confirmadas |
| Protótipo funcional (PDF, p. 7–8) | Streamlit em `streamlit_app.py`/`frontend/app.py`, API FastAPI em `src/azul_crm/api/` e gateway local | `tests/test_deploy.py`, `tests/test_customer_page.py`, `tests/test_integrated.py`; CI executa demo, validação e preparo | **Comprovado localmente**; hospedagem e acesso de avaliadores continuam pendentes |
| IA responsável/LGPD: dados sintéticos, transparência e ausência de vieses (PDF, p. 8) | Auditoria em `src/azul_crm/pipeline/bias_audit.py`, consentimento fail-closed, evidências e rótulos `is_demo` | `tests/test_bias_audit.py`, `tests/test_consent_checklist.py`, `tests/test_big_knowledge.py`, `tests/test_verificar_base_conhecimento.py` | **Parcialmente comprovado**: controles e auditoria sintética existem; não substituem avaliação de produção ou dados reais |
| Entrega: vídeo, protótipo acessível e repositório privado (PDF, p. 9) | Código e documentação no repositório privado; deploy descrito em `docs/DEPLOY.md` | CI comprova o código, não publicação, vídeo ou acesso externo | **Bloqueado externamente**: hospedagem, acesso dos avaliadores, vídeo e submissão não têm evidência neste checkout |

## O que não está homologado

Sem evidência adicional, não declarar como realizado: **Snowflake real**, **Ollama real e groundedness**, **corpus oficial/homologado do Azul Fidelidade**, **dados internos reais da Azul** ou **hospedagem privada/acesso dos avaliadores**. O PDF afirma que não haverá dados reais de clientes; o repositório usa dados sintéticos e fontes públicas, conforme `README.md` e os testes de proveniência.

## Comandos e CI

Os comandos de validação reproduzíveis são `python -m ruff check .`, `python -m pytest -q`, `python -m azul_crm.pipeline.cli demo`, `python -m azul_crm.pipeline.cli validate`, `python scripts/export_contracts.py` e `python -m azul_crm.cli prepare --customers 120`. Nesta atualização documental eles **não foram executados**; o CI de `develop@5d7fafc` passou com Gitleaks, Ruff, 191 testes, demo, validação, exportação de contratos e preparo de 120 clientes. Workflow: `.github/workflows/ci.yml`.

## Evidência histórica de validação local/CI

Ambientes: Windows com Python 3.11 (máquina da equipe) e Linux com Python 3.12.

- `python -m pytest -q`: **191 testes passaram** no CI de `develop@5d7fafc`. Um aviso de depreciação Starlette/httpx, sem falhas; não suprimido. Nesta atualização documental a suíte não foi executada localmente.
- `python -m ruff check .`: passou. O CI do GitHub passou no pull request da integração.
- `python -m azul_crm.cli prepare` e `demo`: base de demonstração com 400 clientes sintéticos. `validate`: Gold SQL válida; clientes, viagens, features, desfechos e fidelidade consistentes.
- **Dados reais da ANAC, arquivos oficiais baixados manualmente:** tarifas de setembro de 2026 (892.505 registros; 45 sem aeroporto reconhecido) e VRA de agosto de 2026 (88.064 linhas; 24 rejeitadas por estarem fora do mês). Testadas também idempotência, período inválido, NaN, preservação de ausências e aeroportos desconhecidos.
- `train`: a escolha entre a regra e a regressão logística usa validação cruzada com teste estatístico. Na base calibrada com a ANAC a regra foi mantida.
- Personas por agrupamento, CLV de 12 meses, auditoria de viés (taxa de falso alarme e poder de detecção medidos por simulação) e playbook de ações, todos com testes.
- Exportação do lake em Parquet: 17 tabelas, com 980 mil linhas na bronze quando a ANAC está ingerida, em cerca de 40 segundos e 550 MB de memória.
- API: contratos, paginação, ausências, filtros, simulação e revisão testados via TestClient. Inicialização real do Uvicorn e HTTP local verificadas.
- Streamlit AppTest: todas as páginas executadas sem erros; geração de rascunho e consulta de fatores executadas. Não é equivalente a captura visual em navegador.
- Importação de documento TXT, recuperação e rejeição de identificador inválido. O regulamento do Azul Fidelidade foi importado (48 trechos), e a busca de governança continua devolvendo o catálogo interno primeiro. PDF usa pypdf, mas não há teste de OCR (não implementado).
- Contrato do adaptador Ollama testado com resposta HTTP simulada: respostas vazias, sem citação permitida ou com citação inválida são rejeitadas. Isso não é inferência Ollama real.
- Integridade do cache HTTP testada com transporte simulado; não é prova de acesso aos endpoints da ANAC.

## Validado com serviço ou arquivo externo real

- OurAirports: download HTTPS e carga de 86 mil aeroportos na máquina da equipe.
- Arquivos mensais reais da ANAC (tarifas e VRA), baixados à mão do portal oficial.
- Consulta da documentação oficial de Snowflake, MLflow, Streamlit, ANAC/VRA e Ollama. Consulta documental não equivale a testar seus serviços.

## Implementado, mas sem homologação externa

| Integração | O que existe | O que falta comprovar |
|---|---|---|
| Snowflake | Conector, autenticação, SQL, roles, transações, MERGE em lotes e DDL tipado do lake | Executar com conta real e conferir permissões e contagens |
| Ollama | Embeddings, índice, geração JSON, citações, timeout | Baixar modelos, executar inferência e avaliar qualidade |
| MLflow | Registro de parâmetros, métricas e artefato JSON | Executar com o extra de tracking instalado |
| Download automático da ANAC | Downloader, limite, retentativas e descoberta limitada de links | Os arquivos usados foram baixados à mão; o portal já retornou 503 ao downloader |
| Docker e hospedagem | Dockerfile e entrada Streamlit para deploy privado | Construção, deploy e acesso dos avaliadores |

## Pendências reais de implementação e escopo

- **Agente com LLM:** o rascunho da mensagem vem de template. O assistente documental é extrativo (sem LLM) e busca por semelhança de palavras, sem entender sinônimos.
- **Benefícios específicos do Azul Fidelidade:** o regulamento está no corpus, mas não fixa valores de bônus nem de upgrade. Por isso as ofertas são hipóteses a validar, e a vigência da versão importada não foi confirmada.
- **Calibração:** o comportamento individual do cliente (frequência, sazonalidade, resgate, fidelidade) continua sintético. Tarifas (setembro) e VRA (agosto) são de meses diferentes, e o VRA cobre um mês só.
- **SHAP e análise de sentimento público:** não implementados. As explicações são contribuições lineares.
- Controle de acesso e auditoria de produção e autenticação da API. MVP local ou host privado apenas.
- Teste visual pixel a pixel: o navegador de teste não pôde ser instalado. O AppTest validou execução e controles, não fidelidade visual final.
- Vídeo, publicação privada e submissão.

## Resultados do treino (base calibrada com a ANAC)

Seed 42; 240 registros de treino, 80 de validação e 80 de teste. No conjunto de teste, a ROC-AUC da logística foi 0,562 e a da regra 0,616 (Brier 0,249 nos dois). A decisão usa validação cruzada em treino mais validação, com teste t pareado corrigido: o ganho de AUC da logística foi de −0,006 (t = −0,23; o mínimo é 1,65). A regra anterior, que comparava só a validação de 80 clientes, teria adotado o modelo, e foi trocada por isso. Veja `docs/MODELO_CHURN.md` e `artifacts/metrics.json`.

Esses resultados não foram otimizados por busca de seed nem apresentados como desempenho real. Desfechos e clientes são sintéticos. As explicações da regressão são contribuições lineares, não SHAP.

## Critério honesto de conclusão

O núcleo local executável foi integrado e testado, inclusive com dados reais da ANAC. Não se declara o escopo inteiro do desafio concluído, nem Snowflake ou LLM funcionando. A equipe pode executar o MVP e ativar as integrações documentadas, mas as pendências acima precisam ser consideradas na apresentação.
