# Validação e lacunas — 21/10/2026

## Validado localmente

- `python -m pytest -q`: **24 testes passaram**, incluindo os 15 testes preservados da base original. Um aviso de depreciação Starlette/httpx, sem falhas; não suprimido.
- `python -m ruff check src frontend tests`: passou.
- `python -m azul_crm.cli demo --customers 400 --seed 42`: 400 clientes, 6.046 viagens.
- `python -m azul_crm.cli validate`: Gold SQL válida; clientes/viagens/features/desfechos/fidelidade consistentes.
- `python -m azul_crm.cli train`: regressão logística treinada, seleção por validação e relatório de teste produzido. Baseline mantido.
- `python -m azul_crm.cli index`: corpus local indexado em dois fragmentos; resposta com fonte e abstenção testadas.
- `python -m azul_crm.cli sync-scores`: 400 scores publicados na Gold SQL.
- API: contratos, paginação, ausências, filtros, simulação e revisão testados via TestClient. Inicialização real Uvicorn e HTTP local também verificadas.
- Streamlit AppTest: seis páginas executadas sem erros/exceções; geração de rascunho e consulta de fatores executadas. Não é equivalente a captura visual em navegador.
- Importação de documento TXT, recuperação e rejeição de identificador inválido verificadas. PDF usa pypdf, mas não há teste de OCR (não implementado).
- Ingestão ANAC/VRA testada com amostras construídas: idempotência, período inválido, NaN, preservação de ausências e aeroportos desconhecidos.
- Integridade do cache HTTP testada com transporte simulado; não é prova de acesso aos endpoints ANAC.

## Validado com serviço externo real

- Download OurAirports HTTPS respondeu 200. Recorte real de dez aeroportos gravado em `data/fixtures/airports_reference.csv`, com fonte/hash integral em JSON adjacente.
- Consulta da documentação oficial de Snowflake, MLflow, Streamlit, Render, ANAC/VRA e Ollama. Consulta documental não equivale a testar seus serviços.

## Implementado, mas sem homologação externa

| Integração | O que existe | O que falta comprovar |
|---|---|---|
| Snowflake | Conector, autenticação, SQL, roles, transações, MERGE em lotes e consultas | Executar com conta real e conferir permissões/contagens |
| Ollama | Embeddings, índice, geração JSON, citações, timeout | Baixar modelos, executar inferência e avaliar qualidade |
| MLflow | Registro de parâmetros, métricas e artefato JSON | Executar com extra tracking instalado |
| Download ANAC | Downloader, limite, retentativas e descoberta limitada de links | Portal retornou 503; validar arquivo mensal real |
| VRA | Parser de colunas oficiais e persistência Bronze/Silver | Validar CSV real e variantes de schema |
| Docker e hospedagem | Dockerfile e entrada Streamlit para deploy privado | Construção/deploy e acesso dos avaliadores |
| Windows | Scripts PowerShell e comandos preparados | Execução nativa Windows; ambiente de testes foi Linux/Python 3.12 |

## Pendências reais de implementação/escopo

- Coletor/canonizador da base separada de demanda.
- Calibração do gerador por frequência de rotas, sazonalidade, demanda e operações; atualmente `--public` usa apenas médias tarifárias por rota.
- Regulamento oficial de fidelidade no corpus e regras verificadas de benefícios específicos. Corpus entregue é interno e demonstrativo.
- RAG com LLM avaliado por groundedness/conformidade em perguntas reais; integração não basta para comprovar qualidade.
- CLV preditivo treinado, SHAP, segmentação por clustering e análise de sentimento público.
- Controle de acesso/auditoria de produção e autenticação da API. MVP local/host privado apenas.
- Teste visual pixel a pixel: navegador de teste não pôde ser instalado (download inválido). AppTest validou execução/controles, não fidelidade visual final.
- Pitch, ensaio, publicação privada e submissão.

## Resultados do treino entregue

Seed 42; 240 registros de treino, 80 validação, 80 teste. ROC-AUC da logística no teste: aproximadamente 0,614; baseline: 0,623. Brier da logística: 0,235; baseline: 0,244. O critério de promoção usa **validação**, não teste: AUC maior e Brier menor simultaneamente. Não foi atendido. Valores completos em `artifacts/metrics.json`.

Esses resultados não foram otimizados por busca de seed nem apresentados como performance real. Desfechos e clientes são sintéticos. As explicações da regressão são contribuições lineares, não SHAP.

## Critério honesto de conclusão

O núcleo local executável foi integrado e testado. Não se declara o escopo inteiro do guia funcional concluído nem Snowflake/RAG oficiais funcionando. A equipe pode executar o MVP e ativar as integrações documentadas, mas as pendências acima precisam ser consideradas na apresentação.
