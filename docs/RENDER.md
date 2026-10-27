# Publicar a interface web no Render

Este guia publica a aplicação responsiva em um **Web Service** do Render. O serviço usa FastAPI no
servidor e os arquivos de `web/public` no navegador. O arquivo `render.yaml`, na raiz do repositório,
guarda a configuração reproduzível do deploy.

## O que este deploy publica

- Interface responsiva e API em `web/`.
- Snapshot versionado com 400 clientes exclusivamente sintéticos.
- Login privado obrigatório em ambiente hospedado.
- Gemini opcional: sem chave, a aplicação usa a contingência estruturada e a identifica como tal.

O deploy **não** homologa dados reais da Azul, Snowflake, Ollama, corpus oficial, envio de campanhas
ou disponibilidade do Gemini.

## 1. Enviar a branch

A configuração aponta para a branch `deploy/render-web`. Confirme que ela existe no GitHub antes de
criar o serviço. Não publique diretamente de `main` enquanto este deploy estiver em validação.

## 2. Criar o serviço pelo Blueprint

1. Abra <https://dashboard.render.com/> e entre na sua conta.
2. Clique em **New +** e depois em **Blueprint**.
3. Conecte o repositório do Azul CRM e selecione a branch `deploy/render-web`.
4. O Render encontrará `render.yaml`. Revise o plano **Free** e o nome
   `azul-crm-intelligence`.
5. No campo protegido `CRM_APP_PASSWORD`, crie a senha privada de acesso diretamente no Render.
   Não coloque essa senha no GitHub, no código ou em mensagens.
6. Confirme a criação. `CRM_SESSION_SECRET` será gerado automaticamente pelo Render.

O Blueprint instala `web/requirements.txt`, inicia o Uvicorn em `0.0.0.0:$PORT` e verifica
`/api/health`.

## 3. Configurar o Gemini (opcional)

Em **Environment**, adicione `GEMINI_API_KEY` usando o campo protegido do Render. O modelo padrão é
`gemini-3.8-flash` e o limite interno inicial é de cinco solicitações por dia. A conta, cota e
disponibilidade são controladas pelo Google; a configuração não garante resposta real.

## 4. Persistência (opcional, mas recomendada)

Sem Redis, decisões e contadores ficam em SQLite no disco local do serviço. No plano gratuito do
Render esse disco é efêmero: reinícios ou novas publicações podem apagar esse estado. O snapshot de
leitura continua no Git.

Para persistência compartilhada, adicione em **Environment**, como valores protegidos:

- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`

As duas variáveis devem ser configuradas juntas. Não as registre no repositório.

## 5. Validar o resultado

1. Abra `https://SEU-SERVICO.onrender.com/api/health` e confirme `status: ok` e `snapshot: true`.
2. Abra a URL principal, entre com a senha cadastrada e confira Visão geral e Clientes.
3. Teste em uma janela estreita ou celular.
4. Gere uma pergunta no Assistente IA. Confira se o modo exibido é `gemini_grounded` ou
   `structured_fallback`; não trate a contingência como resposta do Gemini.
5. Revise os logs do Render. Nunca copie segredos para os logs ou para um chamado.

No plano gratuito, o primeiro acesso depois de um período ocioso pode demorar enquanto o serviço
acorda. Isso é comportamento da hospedagem, não falha do CRM.

## Diagnóstico rápido

- **Build falhou:** confirme que o Root Directory mostrado pelo Blueprint é `web` e que o comando é
  `pip install -r requirements.txt`.
- **Serviço não responde:** confirme o Start Command e procure no log a porta fornecida por `PORT`.
- **HTTP 503 ao entrar:** `CRM_APP_PASSWORD` ou `CRM_SESSION_SECRET` não foi configurado corretamente.
- **Estado sumiu após deploy:** configure o par Upstash; o SQLite local não é persistente no plano
  gratuito.
- **Gemini em contingência:** confira a chave, o modelo e a cota no provedor; não repita chamadas em
  ciclo.
