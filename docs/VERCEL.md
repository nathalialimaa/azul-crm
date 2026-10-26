# Publicação na Vercel

A interface principal fica em `web/`. Ela usa HTML/CSS/JavaScript nativos e FastAPI em uma função Python, com dados sintéticos pré-calculados. Não precisa de servidor Streamlit, Ollama, Node ou pipeline de treinamento no deploy.

## 1. Repositório e branch

1. Entre na Vercel com a conta que pode acessar o GitHub `nathalialimaa/azul-crm`.
2. Use **Add New → Project** e importe o repositório privado. Autorize somente o repositório necessário.
3. Selecione a branch **feat/vercel-azul-intelligence**. Para mantê-la como versão principal deste projeto da Vercel, ajuste **Settings → Environments → Production → Branch Tracking** (ou **Git → Production Branch**, conforme o painel). O `main` do GitHub não precisa mudar.
4. Em **Root Directory**, informe **web**. Essa configuração é essencial: a raiz analítica tem dependências e arquivos ANAC desnecessários para o deploy.
5. Selecione **Framework Preset: Other**. O `vercel.json` define a saída `public`, a função `api/index.py`, as rotas e duração máxima de 60 segundos. Deixe Build Command vazio. Não use `streamlit run` como comando de build.
6. Use Python 3.12; `web/.python-version` já registra a versão. As dependências leves estão em `web/requirements.txt`.

## 2. Persistência e controle compartilhado

1. No **Marketplace/Storage** da Vercel, conecte um banco **Upstash Redis** ao projeto, ou crie um Redis na conta Upstash e use suas credenciais REST.
2. Copie os valores REST para as variáveis abaixo. Não use a URL TCP `redis://` nem uma credencial somente leitura.
3. Use um banco exclusivo para esta aplicação. Preview e Production devem usar bancos diferentes se quiser separar cotas e histórico; o prefixo das chaves é `azul:`.

Redis guarda contador diário, intervalo entre chamadas, cache temporário, rascunhos e decisões. O limite é reservado atomicamente antes de chamar o Gemini. Se Redis estiver ausente ou indisponível, login com senha, geração e gravações falham de forma explícita. Não há substituição silenciosa por armazenamento em memória ou arquivos temporários na Vercel.

## 3. Variáveis de ambiente

Em **Settings → Environment Variables**, configure no servidor para o ambiente desejado (Production e/ou Preview):

| Nome | Valor / finalidade |
|---|---|
| `GEMINI_API_KEY` | Sua chave atual, copiada diretamente para a Vercel. Nunca em código ou variável pública |
| `GEMINI_MODEL` | `gemini-3.8-flash` (modelo atual; disponibilidade depende da conta Google) |
| `GEMINI_DAILY_LIMIT` | `5` para começar; limite global por dia UTC, incluindo tentativas que falham |
| `GEMINI_MAX_ATTEMPTS` | `1`; a API web também força uma única tentativa |
| `CRM_APP_PASSWORD` | Senha de acesso privada, forte e exclusiva |
| `CRM_SESSION_SECRET` | Segredo aleatório com pelo menos 32 caracteres, para assinar sessões |
| `UPSTASH_REDIS_REST_URL` | Endpoint HTTPS REST do banco Redis |
| `UPSTASH_REDIS_REST_TOKEN` | Token de leitura e escrita desse banco |

Para gerar um segredo no terminal local: `python -c "import secrets; print(secrets.token_hex(32))"`. Copie o resultado para `CRM_SESSION_SECRET`; não publique esse valor. A variável `VERCEL` é fornecida automaticamente pela plataforma. Não crie variáveis com prefixo `NEXT_PUBLIC_` ou `VITE_` para credenciais. As chaves não aparecem no frontend.

O `.env` local é ignorado e **não é enviado ao GitHub**. Portanto, as variáveis precisam ser cadastradas na Vercel mesmo que a aplicação já funcione no computador. Mudar uma variável requer um novo deploy/redeploy para os processos usarem o novo valor.

## 4. Deploy e conferência

1. Salve as variáveis e clique **Deploy**. Após alterações posteriores, use **Redeploy** ou publique um commit na branch vinculada.
2. Abra a URL gerada. Entre usando a senha configurada.
3. Confira a Visão geral: 400 clientes no snapshot, 80 de alto valor e 37 de alto valor em risco na carteira completa. CLV deve corresponder aos dados do snapshot, sem copiar os números ilustrativos da imagem de referência.
4. Navegue por Clientes, Segmentos e Dados e modelos. Isso não consome o Gemini.
5. Revise uma recomendação no modo prévia, confirme o checklist e registre uma decisão. Reabra o histórico após atualizar a página para conferir a persistência.
6. Faça **uma** pergunta curta no assistente. Se receber 503/429, não repita em sequência: a tela informa a contingência e o limite diário continua valendo. O cache de sucesso dura 20 minutos; solicitações diferentes precisam aguardar 20 segundos.

A verificação automatizada local usa respostas simuladas e não exige chaves. O deploy na conta Vercel e o Redis real precisam ser configurados nessa conta; a validação local não é uma confirmação de deploy publicado.

## 5. Atualizar os dados

O snapshot está versionado e contém apenas dados sintéticos e evidências do corpus, sem os documentos confidenciais originais do desafio. Após alterar o motor analítico:

```powershell
python scripts/preparar_anac.py
python scripts/export_web.py
python -m pytest tests/test_web.py -q
```

O preparo recria a carteira analítica local; faça-o somente quando desejar atualizar essa base. `export_web.py` não chama LLM e recusa clientes não sintéticos. Os módulos Gemini e sentimento em `web/crm_runtime` são gerados a partir dos arquivos canônicos; um teste impede divergência. Revise o snapshot e publique um novo commit. Redis não é apagado pelo deploy.

## 6. Executar a mesma versão no computador

Na raiz do repositório:

```powershell
python -m pip install -r web/requirements.txt
python -m uvicorn web.api.index:app --host 127.0.0.1 --port 8503
```

Abra http://127.0.0.1:8503. A versão local lê o `.env` da raiz e usa `.runtime/web.sqlite3` para estado durável quando Redis não está configurado. Sem senha local, o navegador obtém uma sessão automaticamente; na Vercel a senha e o segredo são obrigatórios. F5 no VS Code inicia a versão web na porta 8504 para não conflitar com a instância já aberta.

## Diagnóstico

| Sintoma | Verificação |
|---|---|
| Página sem API / 404 | Root Directory deve ser `web`; confira `vercel.json` e logs de build |
| 503 ao entrar | Configure senha, segredo de sessão e Redis REST de escrita |
| Gemini 404 | Confira `GEMINI_MODEL` e disponibilidade para sua conta |
| Gemini 429 | Cota do Google; aguarde ou revise o plano na conta Google |
| Gemini 503 | Indisponibilidade externa; a chave nova não garante disponibilidade |
| Limite diário interno | Cinco reservas por dia UTC por padrão; não limpe o contador para repetir tentativas |
| Revisão expirada | Rascunhos expiram em 24 horas e pertencem à sessão que os criou |

Referências: [Python Functions](https://vercel.com/docs/functions/runtimes/python), [vercel.json](https://vercel.com/docs/project-configuration/vercel-json), [Upstash REST](https://upstash.com/docs/redis/features/restapi).
