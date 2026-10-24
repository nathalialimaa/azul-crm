# Azul CRM — CRM de Alto Valor (Hacka Business 2026)

Painel de inteligência de CRM que encontra clientes de alto valor, mostra quem corre risco de sair e sugere a próxima ação, sempre com revisão humana. **FastAPI + Streamlit**, dados em SQLite (ou Snowflake) e um lake em Parquet com dicionário de dados.

**Os clientes são sintéticos.** Tarifas, demanda por rota e atrasos podem ser calibrados com dados públicos da ANAC (veja "Calibração com dados da ANAC"). Nenhum dado real da empresa foi usado.

**Leia primeiro:** esta entrega roda localmente, mas não está homologada no Snowflake, o assistente não usa LLM (o rascunho da mensagem vem de template) e o regulamento público do Azul Fidelidade está na base apenas para consulta (o assistente busca por semelhança de palavras e não valida a vigência nem benefícios específicos). O repositório e o protótipo devem permanecer privados conforme o enunciado. Índice dos documentos e premissas: `docs/INDICE.md`. Pendências: `docs/DEPENDENCIAS.md` e `docs/VALIDACAO.md`.

## Em três comandos (Windows / PowerShell)

```powershell
py -3.12 -m venv .venv          # ou py -3.11 / py -3.13
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

Na primeira execução o app gera sozinho a base de demonstração (400 clientes sintéticos, seed 42), treina o churn e as personas e roda a auditoria. Leva alguns segundos. Abra `http://127.0.0.1:8501`. Para rodar os testes: `.\.venv\Scripts\python.exe -m pytest -q` (180 testes).

## O que a base de demonstração mostra

Valores de referência com a seed 42. Podem variar levemente com a versão das bibliotecas.

| Resultado | Valor |
| --- | --- |
| Personas | 4 grupos: Baixo Volume Ativo (119), Alto Valor Esfriando (102), Fiéis de Alto Valor (98) e Baixo Volume Ativo com Atrasos Frequentes (81) |
| Alto valor | 80 clientes, os 20% de maior valor potencial (corte de R$ 3.252 de margem por ano). Concentram 41,5% do valor, e 46 estão em risco |
| CLV de 12 meses | R$ 370.979 esperados e R$ 341.667 em risco, com margem de 15% e desconto de 10% ao ano, que são **hipóteses** |
| Churn | A regra heurística é mantida: o modelo logístico não passa no teste estatístico (t = −0,40; mínimo de 1,65) |
| Auditoria de viés | 0 alertas. Aeroporto e região aparecem como "confundido" porque o gerador sem calibração define o comportamento pela posição do cliente; com rotas reais isso deixa de acontecer |

Com a calibração da ANAC os números mudam (por exemplo, 173, 103, 98 e 26 clientes nas personas, e 37 clientes de alto valor em risco). Veja `docs/CALIBRACAO_PUBLICA.md`.

## Calibração com dados da ANAC

Os arquivos públicos **não estão no repositório** (uns 40 MB). Fontes oficiais:

- **Tarifas aéreas domésticas** (mensal): DataSAS da ANAC, `https://sistemas.anac.gov.br/sas/downloads/`, tema "Tarifas Transporte Aéreo Passageiros Domésticos".
- **VRA, Voo Regular Ativo** (mensal): `https://sistemas.anac.gov.br/dadosabertos/`, pasta "Voos e operações aéreas / Voo Regular Ativo (VRA)".
- **Aeroportos:** o comando `airports` baixa a lista do OurAirports.

```powershell
$dados = "C:\caminho\da\pasta"   # TROCAR pelo caminho real dos arquivos baixados
.\.venv\Scripts\python.exe -m azul_crm.cli airports
.\.venv\Scripts\python.exe -m azul_crm.cli fares --file "$dados\ARQUIVO-DE-TARIFAS.zip" --period 2026-09
.\.venv\Scripts\python.exe -m azul_crm.cli vra --file "$dados\VRA_20268.csv" --period 2026-08
.\.venv\Scripts\python.exe -m azul_crm.cli demo --public --customers 400 --seed 42
```

Depois rode, na ordem: `train`, `personas`, `sync-scores`, `bias-audit`, `clv-report` e `export-lake`. O passo `fares` é o mais pesado (de 1 a 3 minutos e uns 2 GB de memória).


## Demonstração rápida no Windows / PowerShell

1. Instale Python **3.11 a 3.13** (incluindo o Python Launcher). Clone ou extraia o repositório.
2. Abra o PowerShell na pasta `azul-crm`, onde está `pyproject.toml`.
3. Execute, sem precisar ativar o ambiente virtual:

```powershell
py -3.12 -m venv .venv          # ou py -3.11 / py -3.13
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Abra `http://localhost:8501`. **É só um terminal.** O Streamlit usa os mesmos serviços de negócio da API diretamente. Se a base SQLite estiver ausente, a entrada `streamlit_app.py` gera 400 clientes com seed 42. O app gera a base de demonstração sozinho na primeira execução. Não é necessário instalar Node, React ou Django.

Se preferir, execute `powershell -ExecutionPolicy Bypass -File .\scripts\start_demo.ps1`. Essa opção aplica a política somente a esse processo, instala dependências e força o modo SQLite local. Não use esse script para demonstrar Snowflake.

Se o comando `py -3.12` falhar, confirme a instalação com `py --list`. Se a porta estiver ocupada, acrescente `--server.port 8502` ao comando Streamlit. Não copie ambientes virtuais de outras máquinas.

## O que demonstrar em cinco minutos

1. **Visão geral:** clientes de alto valor (top 20% por CLV), risco, CLV de 12 meses e fila de prioridade.
2. Escolha um cliente no menu lateral. A matriz destaca o cliente selecionado.
3. Confira fatores e clique em **Gerar mensagem para revisão**. Abra as evidências.
4. Em **Clientes**, veja viagens e fidelidade sintética, inclusive resgates e pagamentos restritos simulados.
5. Em **Ações de CRM**, aprove ou rejeite o rascunho. A decisão é registrada; nenhuma mensagem é enviada. Compare uma hipótese de custo e retenção no simulador.
6. Em **Assistente IA**, consulte a metodologia; uma pergunta sem correspondência deve produzir abstenção.
7. Em **Dados e modelos**, mostre método ativo, métricas e limitações. Exporte o recorte no rodapé.

Também vale mostrar **Segmentos** (as personas e a definição de alto valor, com a tabela de sensibilidade) e **Auditoria de viés** (o alerta exige significância estatística).

A aparência segue a hierarquia e a paleta da imagem fornecida. A matriz usa o valor potencial de 12 meses (margem, em reais) no eixo vertical e o risco de evasão no horizontal; a divisória marca o corte do alto valor (top 20%). Margem e desconto são hipóteses, com tabela de sensibilidade (`docs/CLV.md`). O resultado não é uma cópia pixel a pixel da imagem.

## Usar FastAPI em processo separado

Terminal 1, na mesma pasta:

```powershell
.\.venv\Scripts\python.exe -m uvicorn azul_crm.api.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
$env:CRM_UI_MODE="http"
$env:CRM_API_URL="http://127.0.0.1:8000"
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py
```

Documentação interativa: `http://127.0.0.1:8000/docs`. Saúde: `http://127.0.0.1:8000/health`.

Para voltar a um terminal: feche os processos, remova a variável com `Remove-Item Env:CRM_UI_MODE -ErrorAction SilentlyContinue` e use `streamlit_app.py`.

A API não implementa autenticação de produção. Mantenha-a vinculada a `127.0.0.1`; a hospedagem recomendada usa o modo local de serviços e o controle de acesso do Streamlit privado. Não exponha a API diretamente à internet.

## Reproduzir dados, treinamento e validação

```powershell
# Substitui o snapshot sintético atual, incluindo decisões de demonstração.
.\.venv\Scripts\python.exe -m azul_crm.cli demo --customers 400 --seed 42
.\.venv\Scripts\python.exe -m azul_crm.cli validate
.\.venv\Scripts\python.exe -m azul_crm.cli train
.\.venv\Scripts\python.exe -m azul_crm.cli personas
.\.venv\Scripts\python.exe -m azul_crm.cli bias-audit
.\.venv\Scripts\python.exe -m azul_crm.cli clv-report
.\.venv\Scripts\python.exe -m azul_crm.cli export-lake
.\.venv\Scripts\python.exe -m azul_crm.cli index
.\.venv\Scripts\python.exe -m azul_crm.cli sync-scores
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src frontend tests
```

Após mudar a Gold/modelo, reinicie a API e clique **Atualizar dados** no Streamlit. O snapshot evita consultas repetidas ao warehouse; não há atualização automática em tempo real.

`train` usa 60% treino, 20% validação e 20% teste, com estratificação e seed. A escolha entre a logística e a regra usa **validação cruzada** (5×3, em treino + validação, sem o teste): a logística só entra se o ganho de AUC for distinguível de ruído (teste t pareado com correção de Nadeau e Bengio, t > 1,65) e o Brier for menor; veja `docs/MODELO_CHURN.md`. Na base de demonstração, a logística **não é promovida**. Métricas reais da execução estão em `artifacts/metrics.json`; elas medem apenas dados simulados.

O baseline de valor e os segmentos continuam sendo regras. A explicação da logística é aditiva em log-odds, **não SHAP**. O CLV de 12 meses é calculado com premissas explícitas e configuráveis (margem e desconto, que são hipóteses), não treinado com dados reais; veja `docs/CLV.md`.

O catálogo de ações por persona está em `config/playbook.toml`; veja `docs/PLAYBOOK.md`.

Para publicar o protótipo (Docker, senha e Streamlit Cloud), veja `docs/DEPLOY.md`.

Data lake em Parquet, dicionário de dados e DDL do Snowflake (`azul-crm export-lake`): `docs/DATA_LAKE.md`.

CLV de 12 meses e definição de alto valor (`azul-crm clv-report`): `docs/CLV.md`.

## ANAC e aeroportos

Importe a referência pequena já verificada, ou baixe a dimensão completa:

```powershell
.\.venv\Scripts\python.exe -m azul_crm.cli airports --file data/fixtures/airports_reference.csv
# Alternativa: download real OurAirports, limite 50 MiB
.\.venv\Scripts\python.exe -m azul_crm.cli airports
```

Tarifas, com arquivo oficial obtido no portal:

```powershell
.\.venv\Scripts\python.exe -m azul_crm.cli fares --file "C:\dados\202606.CSV" --period 2026-06
```

Download automático a partir de um link oficial:

```powershell
# Substitua o endereço pelo link HTTPS do arquivo, não pela página HTML.
.\.venv\Scripts\python.exe -m azul_crm.cli fares --url "COLE_A_URL_HTTPS_OFICIAL" --period 2026-06 --max-mb 50
# Tenta descobrir um link mensal único publicado pelo portal:
.\.venv\Scripts\python.exe -m azul_crm.cli fares --period 2026-06
```

A descoberta não inventa caminhos e pode falhar se o portal exigir interação, estiver indisponível ou apresentar múltiplos arquivos. Foi observado HTTP 503 no ambiente desta entrega. Use `--file` nesses casos.

VRA, com as colunas publicadas pela ANAC:

```powershell
.\.venv\Scripts\python.exe -m azul_crm.cli vra --file "C:\dados\VRA_202606.csv" --period 2026-06
# Também aceita --url HTTPS de domínio ANAC.
```

O parser VRA lê o arquivo oficial mensal (CSV do portal de dados abertos da ANAC, "Voo Regular Ativo"): pula a linha de aviso do topo, trata `null` e `N/A` como ausência, lê horários em **UTC** e calcula atraso e cancelamento. Linhas sem data ou fora do período são **rejeitadas e contadas** (`rejected_reasons`); se mais de 5% forem rejeitadas, a carga é recusada. Schemas divergentes falham explicitamente. Foi validado com o arquivo real de agosto de 2026 (88 mil linhas). Veja `docs/CALIBRACAO_PUBLICA.md`.

Para gerar uma carteira com médias tarifárias da Silver pública:

```powershell
# Ingerir antes: airports, fares (tarifas) e vra (atrasos)
.\.venv\Scripts\python.exe -m azul_crm.cli demo --public --customers 400 --seed 42
.\.venv\Scripts\python.exe -m azul_crm.cli train
.\.venv\Scripts\python.exe -m azul_crm.cli sync-scores
```

Essa calibração usa médias de tarifas AZU ponderadas por assentos, por rota, e distribui os clientes pelas rotas na proporção dos assentos comercializados (sorteio com semente fixa). Se o VRA tiver sido ingerido, os **atrasos** também são sorteados da distribuição real da Azul (doméstico, por aeroporto de origem quando há voos suficientes); sem ele, vale o padrão antigo. Não calibra frequência individual de viagens, resgate nem fidelidade. O que foi calibrado fica registrado no manifesto (`calibration_scope` e `delay_calibration`).

Os CSVs de tarifas não identificam clientes nem comprovam fidelidade. `period` representa mês de venda. Tarifas restritas e milhas são simulações separadas, sem alegação de cobertura pública.

## Snowflake, RAG, MLflow e hospedagem

Siga `docs/DEPENDENCIAS.md`: contas, permissões, variáveis, comandos e verificações. Em resumo:

- Snowflake é o destino principal planejado/configurável. `CRM_STORAGE=snowflake` escolhe o adaptador; não há fallback silencioso para SQLite se a conexão falhar.
- A demonstração entregue usa `CRM_STORAGE=sqlite` explicitamente.
- `RAG_PROVIDER=local` usa TF-IDF e resposta extrativa, sem LLM.
- `RAG_PROVIDER=ollama` usa embeddings e geração locais. É preciso instalar os modelos e construir o índice. Integração implementada, não executada com modelos reais nesta entrega.
- O corpus contém a metodologia e o catálogo internos do MVP e o **regulamento público do Azul Fidelidade** (versão "novo-2024", copiada manualmente em 23/10/2026; último aditamento registrado em 28/02/2024). A importação **não certifica a vigência**, e o regulamento não fixa valores de bônus nem de upgrade. Veja `docs/BASE_DE_CONHECIMENTO.md`.
- MLflow registra métricas e o artefato JSON se habilitado; não fornece infraestrutura gratuita.
- Hospedagem externa, autenticação dos avaliadores e submissão não foram realizadas.

## Estrutura

```text
src/azul_crm/domain/           entidades, portas, pontuações e elegibilidade originais
src/azul_crm/application/      casos de uso, consulta do dashboard e simulação
src/azul_crm/infrastructure/   SQLite/Snowflake, configuração, índice e validação
src/azul_crm/pipeline/         geração, ingestão, normalização e treinamento
src/azul_crm/api/              contratos v1 preservados e endpoints adicionais
frontend/                     interface Streamlit e gateway local/HTTP
sql/                          estruturas, roles e consultas Snowflake
scripts/                      execução Windows e ingestão agendável
artifacts/                    modelo JSON, métricas e índice
 data/                        fixtures, snapshots, Bronze/Silver/Gold e corpus
 docs/                        diagnóstico, arquitetura, dependências e validação
```

Os documentos anteriores foram preservados em `docs/legacy`; descrevem o estado anterior e não prevalecem sobre esta documentação. Os comandos antigos `python -m azul_crm.pipeline.cli demo/validate` continuam destinados à exportação CSV v1; para atualizar a aplicação v2, use `python -m azul_crm.cli ...`.

## Limites que permanecem

**Feito:** coleta real das tarifas (setembro de 2026) e do VRA (agosto de 2026), com calibração de tarifa média, demanda por rota e atrasos; regulamento público do Azul Fidelidade na base do assistente; CLV de 12 meses com premissas explícitas; personas; auditoria de viés com taxa de erro medida; lake em Parquet com dicionário de dados.

**Pendente ou sem homologação:** integração Snowflake real (o DDL tipado foi gerado, mas nunca executado), execução do Ollama e do MLflow, validação da vigência e dos benefícios específicos do Azul Fidelidade, agente com LLM (o rascunho vem de template), SHAP (as explicações são lineares), análise de sentimento público e a publicação privada do protótipo.

Clientes, fidelidade, resgates, comportamento e desfechos são sintéticos, e a margem e o desconto do CLV são hipóteses. Não alegue que todos os requisitos analíticos do hackathon estão concluídos: a entrega fornece um fluxo local executável, com evidências e lacunas explícitas.
