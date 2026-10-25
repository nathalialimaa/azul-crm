# Validação e lacunas — atualizado em 23/10/2026

## Validado localmente

Ambientes: Windows com Python 3.11 (máquina da equipe) e Linux com Python 3.12.

- `python -m pytest -q`: **180 testes passaram** nos dois ambientes. Um aviso de depreciação Starlette/httpx, sem falhas; não suprimido.
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
