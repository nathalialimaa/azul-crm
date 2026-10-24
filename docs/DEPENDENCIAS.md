# Dependências, ativação e escolhas

Consulta à documentação oficial em 21/10/2026. Não envie credenciais no chat nem as inclua no Git.

## 1. Snowflake — bloqueia integração real, não desenvolvimento local

Necessário: conta acessível, usuário, warehouse e autorização para preparar o banco. A conta trial dura até 30 dias ou até esgotar o saldo. Não é gratuidade permanente. O MVP não depende de Cortex. A confirmação da oferta/saldo deve ser feita no cadastro; não há promessa de créditos específicos.

1. Cadastre-se pelo [Snowflake](https://signup.snowflake.com/), confirme o e-mail e entre no Snowsight.
2. Copie o identificador de conta mostrado nas configurações de conexão. Não use uma URL de console inteira em `SNOWFLAKE_ACCOUNT`.
3. Em uma worksheet SQL, com administrador autorizado, execute `sql/01_setup.sql` e `sql/02_roles.sql`.
4. Substitua `SEU_USUARIO` nas duas linhas comentadas do segundo script e execute os `GRANT ROLE` necessários. Use `CRM_LOADER` para preparar dados e `CRM_APP` para a aplicação.
5. Na pasta do projeto, instale o extra:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[snowflake]"
```

6. Edite `.env`:

```dotenv
CRM_STORAGE=snowflake
SNOWFLAKE_ACCOUNT=SEU_IDENTIFICADOR_DE_CONTA
SNOWFLAKE_USER=SEU_USUARIO
SNOWFLAKE_ROLE=CRM_LOADER
SNOWFLAKE_DATABASE=AZUL_CRM
SNOWFLAKE_WAREHOUSE=CRM_WH
SNOWFLAKE_AUTHENTICATOR=externalbrowser
```

7. Execute `python -m azul_crm.cli check` usando o Python da `.venv`. O navegador abre para autenticação; a conta pode exigir MFA. Resultado esperado: `backend=snowflake, connected=true`.
8. Execute `demo`, `validate`, `train` e `sync-scores`. Para fontes públicas, carregue dimensão/tarifas antes de `demo --public`.
9. Execute `sql/03_verify.sql`: confira 400 clientes, contagens coerentes, zero IDs duplicados e visão de scores preenchida.
10. Troque `SNOWFLAKE_ROLE=CRM_APP`, inicie a aplicação e confira em **Dados e modelos** que a persistência é Snowflake.

O carregador usa transações e MERGE em lotes de 500. Rode **um escritor por vez**: tabelas standard não oferecem unicidade enforced como SQLite. A aplicação carrega um snapshot e reduz acessos repetidos. O warehouse X-Small tem auto-suspend de 60 segundos e consultas têm timeout de 60 segundos. Monitore consumo no Snowsight; esses controles não garantem custo zero.

Para agendamento ou nuvem sem navegador: peça ao administrador configuração de autenticação por chave. Registre a chave pública do usuário no Snowflake e mantenha a privada PKCS#8 fora do repositório. Configure `SNOWFLAKE_PRIVATE_KEY_FILE` e, se criptografada, `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`. Não copie `.env` ou a chave para o ZIP/Git. A conexão passa a usar `SNOWFLAKE_JWT`. A montagem segura do arquivo da chave no host é responsabilidade da implantação.

Alternativa sem conta: `CRM_STORAGE=sqlite`. Nunca interprete um teste SQLite como homologação Snowflake.

Fonte: [Trial accounts](https://docs.snowflake.com/en/user-guide/admin-trial-account).

## 2. RAG — você configura modelos e corpus; não precisa reimplementar o código

Há dois caminhos:

| Componente | Modo local padrão | Modo Ollama |
|---|---|---|
| Fragmentação | 200 palavras com avanço de 150 | Igual |
| Representação | TF-IDF lexical | Embeddings do modelo configurado |
| Índice | Reconstruído em memória; fingerprint gravado | Vetores e fingerprint em JSON |
| Recuperação | Similaridade cosseno, top 3 e limiar | Igual, limiar específico |
| Resposta | Trechos extrativos identificados | Geração JSON com referências validadas |
| Cálculos de clientes | Serviços Python | Serviços Python |

A busca pode falhar mesmo quando um texto relevante existe; o limiar não prova groundedness. Validação de IDs não garante correção de cada frase do LLM. Recomendações comerciais continuam limitadas ao catálogo seguro e exigem revisão.

O adaptador bloqueia respostas Ollama sem texto ou sem uma lista de citações permitidas. Esse contrato é testável offline; não substitui a execução do Ollama nem a avaliação humana do conteúdo.

**Ativação Ollama (bloqueia apenas embeddings/geração reais):**

1. Instale [Ollama](https://ollama.com/) no computador e confirme espaço/memória disponíveis.
2. Em um terminal:

```powershell
ollama pull embeddinggemma
ollama pull qwen2.5:3b
ollama list
```

Os downloads são grandes e não estão incluídos no ZIP. Não foram executados aqui. Se a máquina não comportar os modelos, mantenha `RAG_PROVIDER=local`; não há exigência de pagar API.

3. Mantenha o serviço Ollama ativo. Normalmente o instalador inicia o serviço; se necessário use `ollama serve` em terminal próprio.
4. No `.env`, configure:

```dotenv
RAG_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=embeddinggemma
OLLAMA_MODEL=qwen2.5:3b
```

5. Execute `python -m azul_crm.cli index` com o Python da `.venv`.
6. Reinicie o aplicativo. Pergunte “Como o score combina gasto, frequência e recência?”. Confira referências e trechos.
7. Pergunte algo ausente. Verifique abstenção; para o LLM, revise também conteúdo e citações. Se trocar o corpus/modelo de embeddings, gere o índice novamente.

**Corpus oficial (bloqueia benefícios específicos):**

1. O regulamento público (versão "novo-2024") foi copiado manualmente e importado em 23/10/2026 como `fidelidade-regulamento`. Para benefícios específicos, abra os documentos de benefícios autorizados e repita o procedimento.
2. Copie o texto pertinente para um JSON UTF-8 em `data/knowledge`, no formato dos exemplos existentes:

```json
{
  "document_id": "regulamento-fidelidade-versao-confirmada",
  "title": "Título real do documento",
  "text": "Texto verificado da regra pública, sem instruções inventadas.",
  "source": "URL_OFICIAL_VERIFICADA",
  "version": "DATA_OU_VERSAO_REAL",
  "is_demo": false
}
```

3. Registre no controle da equipe a data de consulta e a regra de elegibilidade que será usada. Não marque textos inventados como oficiais.
4. Execute `index`. Consulte perguntas de teste cujas respostas estejam e não estejam no corpus.
5. O catálogo atual só permite contato sem benefício. Adicionar documentos **não habilita automaticamente** bônus ou upgrade: será necessário implementar/testar a respectiva regra de elegibilidade antes de ampliar `EligibilityPolicy`.

Fontes técnicas: [Embeddings](https://docs.ollama.com/api/embed), [Geração](https://docs.ollama.com/api/generate).

## 3. Dados públicos — bloqueiam validação externa/calibração completa

Conta não é necessária para OurAirports nem, normalmente, para os downloads públicos ANAC. É necessário acesso de rede e os arquivos corretos para o período.

- Tarifas: mês de venda, valor e quantidade de assentos por combinação publicada. Não há identificação individual. A documentação tradicional exclui milhagens/descontos restritos; ausência não vira zero.
- VRA: etapas previstas/realizadas e situação do voo. Não é histórico de cliente.
- OurAirports: dimensão pública, sem garantia de exatidão. Revise códigos históricos/ambíguos.

Passos: importe aeroportos; baixe/carregue tarifas; confira manifesto e relatório `unmatched.json`; resolva correspondências a partir de fonte verificável; valide; gere a carteira com `--public`; treine novamente; atualize scores e a UI.

O esquema de tarifas aceito corresponde às sete colunas do código original de Larissa. Colunas extras ficam na Bronze; mudança de significado não é deduzida. Formatos novos/incompatíveis são rejeitados e exigem revisão do parser. O VRA tem seu próprio parser. Não existe coletor/canonizador da base separada de demanda nesta versão.

**Agendamento Windows:** abra o Agendador de Tarefas → Criar Tarefa Básica → frequência mensal → ação “Iniciar programa” → programa `powershell.exe` → argumentos `-File "C:\CAMINHO\azul-crm\scripts\ingest_month.ps1" -Period "2026-06" -Url "URL_OFICIAL"`. Defina o diretório do projeto em “Iniciar em”. Execute manualmente uma vez e confira histórico/saída. O período é explícito: atualize-o para cada competência; não há descoberta automática garantida da última publicação. Não agende Snowflake com login interativo.

Alternativa local: use a demo de fixtures. O pacote não apresenta uma amostra fabricada como extração ANAC real.

Fontes: [Metadados tarifas](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/tarifas-aereas-domesticas/46-tarifas-aereas-domesticas), [VRA](https://www.anac.gov.br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/voo-regular-ativo-vra/62-voo-regular-ativo-vra), [OurAirports](https://ourairports.com/data/).

## 4. MLflow — opcional, não bloqueia o MVP

A sugestão “mflow” foi interpretada como MLflow; não é confirmação da fala do mentor. MLflow acompanha experimentos, métricas e artefatos. A inferência é feita pelo serviço Python/FastAPI, carregando coeficientes JSON; não é necessário um servidor de modelos separado.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[tracking]"
$env:MLFLOW_ENABLED="true"
$env:MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
.\.venv\Scripts\python.exe -m azul_crm.cli train
.\.venv\Scripts\python.exe -m mlflow ui --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Abra `http://127.0.0.1:5000`, localize `azul-crm-synthetic` e confira métricas e artefatos. O comando da UI ocupa outro terminal. Banco e artefatos ficam no disco local, que precisa de backup se for importante. Registro remoto, armazenamento compartilhado e credenciais são configurações adicionais, não fornecidas gratuitamente pelo MLflow.

Fonte: [Self-hosting MLflow](https://mlflow.org/docs/latest/self-hosting/).

## 5. Hospedagem privada — bloqueia acesso remoto, não execução local

| Opção | Avaliação para este MVP |
|---|---|
| Computador local | Menos configuração, mantém privacidade e permite Ollama; depende da máquina disponível |
| Streamlit Community Cloud | Escolha de menor trabalho para demonstrar remotamente sem LLM local; suporta um app privado e hiberna por inatividade; tratar disco local como descartável |
| Render Free | Exige mais cuidado de acesso; suspende após 15 minutos sem tráfego, perde arquivos locais em reinícios e não oferece disco persistente no plano gratuito |

**Escolha:** Streamlit privado para o fluxo leve; computador local como plano de demonstração com Ollama. Não há solução integral, permanentemente gratuita e com disponibilidade/persistência garantidas para todos os componentes.

1. Coloque o projeto em repositório **privado**. Não publique os materiais do desafio.
2. Crie/acesse sua conta no Streamlit Community Cloud e autorize acesso ao repositório privado. É necessária permissão administrativa no repositório para esse vínculo.
3. Selecione `streamlit_app.py` como entrada e Python 3.12.
4. Mantenha modo local de serviços, SQLite e recuperação extrativa para a primeira demonstração. Em deploy, o snapshot é regenerável; decisões locais podem se perder. Snowflake evita essa dependência do disco, mas requer autenticação não interativa configurada.
5. Nas configurações de compartilhamento, selecione acesso somente a pessoas específicas. Você deve conceder acesso aos avaliadores autorizados.
6. Teste com uma conta autorizada e uma sem acesso. Não confunda repositório privado com uma prova de que a configuração final do aplicativo está correta.
7. Abra a aplicação antes da apresentação para verificar estado de hibernação e dados. Não conte com o host gratuito para rodar os modelos Ollama.

Foi incluído Dockerfile para execução reproduzível, mas a imagem não foi construída/testada neste ambiente. Publicação e envio de convites não foram executados.

Fontes: [Compartilhamento privado](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app), [Hibernação](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app), [Permissões e limites](https://docs.streamlit.io/deploy/streamlit-community-cloud/status), [Render Free](https://render.com/docs/free).

## 6. Submissão e decisões da equipe

O enunciado anexado fixa **26/10/2026**, pitch de até cinco minutos, acesso ao protótipo e repositório privado. O planejamento antigo 09–16/10 é histórico, não prazo oficial.

A equipe precisa decidir quem gravará o pitch, quais avaliadores terão acesso, se apresentará a demo local ou Snowflake e se ativará modelos Ollama na máquina disponível. Nenhuma dessas respostas impedia a implementação local realizada. Elas afetam homologação/apresentação. Não houve inscrição, publicação, convite ou submissão automática.

## Importação assistida de documentos

Além do JSON manual, o código importa PDF textual, TXT e Markdown local:

```powershell
.\.venv\Scripts\python.exe -m azul_crm.cli document --file "C:\dados\regulamento.pdf" --document-id regulamento-verificado --title "Regulamento conferido pela equipe" --url "URL_HTTPS_OFICIAL"
.\.venv\Scripts\python.exe -m azul_crm.cli index
```

O arquivo deve ter no máximo 20 MiB. O importador registra hash, fonte e data; PDF escaneado sem texto requer OCR externo. Use `--demo-doc` para conteúdo fictício. A importação não certifica autenticidade/vigência e não ativa benefícios automaticamente.
