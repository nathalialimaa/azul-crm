# Azul CRM — MVP integrado v0.2

Aplicação privada de inteligência de CRM com **FastAPI + Streamlit**, SQL como persistência da aplicação, pontuações explicáveis, treinamento demonstrativo e assistente documental.

**Leia primeiro:** esta entrega roda localmente, mas não é uma solução inteiramente homologada no Snowflake nem um RAG validado contra o regulamento oficial do Azul Fidelidade. As pendências estão em `docs/DEPENDENCIAS.md` e `docs/VALIDACAO.md`. O repositório e o protótipo devem permanecer privados conforme o enunciado.

## Demonstração rápida no Windows / PowerShell

1. Instale Python **3.12** (incluindo Python Launcher). Extraia este ZIP.
2. Abra o PowerShell na pasta `azul-crm`, onde está `pyproject.toml`.
3. Execute, sem precisar ativar o ambiente virtual:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Abra `http://localhost:8501`. **É só um terminal.** O Streamlit usa os mesmos serviços de negócio da API diretamente. Se a base SQLite estiver ausente, a entrada `streamlit_app.py` gera 400 clientes com seed 42. O ZIP inclui um snapshot demonstrativo já preparado. Não é necessário instalar Node, React ou Django.

Se preferir, execute `powershell -ExecutionPolicy Bypass -File .\scripts\start_demo.ps1`. Essa opção aplica a política somente a esse processo, instala dependências e força o modo SQLite local. Não use esse script para demonstrar Snowflake.

Se o comando `py -3.12` falhar, confirme a instalação com `py --list`. Se a porta estiver ocupada, acrescente `--server.port 8502` ao comando Streamlit. Não copie ambientes virtuais de outras máquinas.

## O que demonstrar em cinco minutos

1. **Visão geral:** clientes de alto valor, risco, proxy de receita futura e fila de prioridade.
2. Escolha um cliente no menu lateral. A matriz destaca o cliente selecionado.
3. Confira fatores e clique em **Gerar mensagem para revisão**. Abra as evidências.
4. Em **Clientes**, veja viagens e fidelidade sintética, inclusive resgates e pagamentos restritos simulados.
5. Em **Ações de CRM**, aprove ou rejeite o rascunho. A decisão é registrada; nenhuma mensagem é enviada. Compare uma hipótese de custo e retenção no simulador.
6. Em **Assistente IA**, consulte a metodologia; uma pergunta sem correspondência deve produzir abstenção.
7. Em **Dados e modelos**, mostre método ativo, métricas e limitações. Exporte o recorte no rodapé.

A aparência segue a hierarquia e a paleta da imagem fornecida. A matriz usa score 0–100 no eixo vertical, evitando apresentar gasto passado como CLV validado. O resultado não é uma cópia pixel a pixel da imagem.

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
.\.venv\Scripts\python.exe -m azul_crm.cli export-lake
.\.venv\Scripts\python.exe -m azul_crm.cli index
.\.venv\Scripts\python.exe -m azul_crm.cli sync-scores
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src frontend tests
```

Após mudar a Gold/modelo, reinicie a API e clique **Atualizar dados** no Streamlit. O snapshot evita consultas repetidas ao warehouse; não há atualização automática em tempo real.

`train` usa 60% treino, 20% validação e 20% teste, com estratificação e seed. A promoção exige ROC-AUC maior e Brier menor que o baseline na validação. No snapshot entregue, a logística **não foi promovida**. Métricas reais da execução estão em `artifacts/metrics.json`; elas medem apenas dados simulados.

O baseline de valor e os segmentos continuam sendo regras. A explicação da logística é aditiva em log-odds, **não SHAP**. Não há previsão de CLV treinada: o card representa um proxy explícito de receita.

O catálogo de ações por persona está em `config/playbook.toml`; veja `docs/PLAYBOOK.md`.

Para publicar o protótipo (Docker, senha e Streamlit Cloud), veja `docs/DEPLOY.md`.

Data lake em Parquet, dicionário de dados e DDL do Snowflake (`azul-crm export-lake`): `docs/DATA_LAKE.md`.

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

O parser VRA registra horários com fuso de Brasília, atraso calculável e cancelamento; horário ausente permanece `null`. O formato deve ter as colunas descritas em `docs/ARQUITETURA.md`. Schemas divergentes falham explicitamente. A carga VRA foi testada com amostra construída; não foi validada contra download real.

Para gerar uma carteira com médias tarifárias da Silver pública:

```powershell
.\.venv\Scripts\python.exe -m azul_crm.cli demo --public --customers 400 --seed 42
.\.venv\Scripts\python.exe -m azul_crm.cli train
.\.venv\Scripts\python.exe -m azul_crm.cli sync-scores
```

Essa calibração usa médias de tarifas AZU ponderadas por assentos, por rota, e distribui os clientes pelas rotas na proporção dos assentos comercializados (sorteio com semente fixa). Não calibra frequência individual de viagens, resgate, fidelidade ou atraso. O VRA é persistido na Silver, mas ainda não condiciona o gerador. Essas limitações são expostas no manifesto.

Os CSVs de tarifas não identificam clientes nem comprovam fidelidade. `period` representa mês de venda. Tarifas restritas e milhas são simulações separadas, sem alegação de cobertura pública.

## Snowflake, RAG, MLflow e hospedagem

Siga `docs/DEPENDENCIAS.md`: contas, permissões, variáveis, comandos e verificações. Em resumo:

- Snowflake é o destino principal planejado/configurável. `CRM_STORAGE=snowflake` escolhe o adaptador; não há fallback silencioso para SQLite se a conexão falhar.
- A demonstração entregue usa `CRM_STORAGE=sqlite` explicitamente.
- `RAG_PROVIDER=local` usa TF-IDF e resposta extrativa, sem LLM.
- `RAG_PROVIDER=ollama` usa embeddings e geração locais. É preciso instalar os modelos e construir o índice. Integração implementada, não executada com modelos reais nesta entrega.
- O corpus entregue contém metodologia e regras internas do MVP. **Não contém regulamento oficial de fidelidade validado.**
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

Integração Snowflake real, execução Ollama/MLflow, corpus oficial de fidelidade, coleta real de tarifas/VRA, calibração por demanda e operação, SHAP, sentimento público e publicação privada permanecem sem homologação ou pendentes, conforme a matriz de validação. Não alegue que todos os requisitos analíticos do hackathon estão concluídos. A entrega fornece um fluxo local executável e os adaptadores/configurações possíveis, com evidências e lacunas explícitas.
