# Deploy do protótipo

O protótipo é **confidencial**: repositório privado, acesso só para avaliadores. Antes de
publicar em qualquer plataforma de terceiros, **confirme com a organização do desafio** se isso
é permitido e qual forma de acesso eles preferem para a avaliação.

## O que o app faz sozinho ao subir

`streamlit_app.py` chama `prepare_demo` uma vez por processo. Se a base não existe, gera 400
clientes sintéticos (seed 42), treina churn e personas, publica os scores e roda a auditoria de
viés. Se tudo já existe, não faz nada. Se modelos e dados não combinam, retreina modelos e atualiza relatórios, preservando a Gold,
a calibração pública e as decisões. Erros de configuração não geram uma nova base automaticamente.
Os dados são determinísticos, então reiniciar não muda os números.

Manualmente: `python -m azul_crm.cli prepare` (só com `CRM_STORAGE=sqlite`).

## Senha (camada extra)

Defina `CRM_APP_PASSWORD` no ambiente da hospedagem e o app só abre depois da senha. **Nunca**
coloque a senha no Git, no Dockerfile ou no README. Sem a variável, o app abre direto. Isso não
substitui o controle de acesso da plataforma.

## Opção A: Docker (qualquer hospedagem que rode contêiner)

```bash
docker build -t azul-crm .
docker run -p 8501:8501 -e CRM_APP_PASSWORD='defina-uma-senha' azul-crm
```

A imagem roda sem root, prepara os dados no build e tem verificação de saúde. O
`.dockerignore` deixa de fora `.env`, bancos locais, `artifacts/` e segredos. HTTPS e domínio
vêm da hospedagem. O Dockerfile não foi construído em um daemon Docker; a instalação não editável
e o `prepare` foram validados fora dele.

## Opção B: Streamlit Community Cloud

Conferido na documentação em 22/10/2026:

- Um app implantado de repositório privado fica **privado por padrão**; o acesso é por convite de
  e-mail (botão Share), não por domínio.
- A conta gratuita permite **um app privado por vez**.
- A plataforma precisa de acesso ao repositório privado, então quem faz o deploy precisa ser
  dona ou colaboradora dele.
- O arquivo principal é `streamlit_app.py`, e o `requirements.txt` já aponta para o pacote.
- O disco é efêmero: as aprovações feitas no app somem ao reiniciar. Para a avaliação isso não
  importa; os números voltam iguais.

## Sobre dados reais no futuro

`CRM_STORAGE=snowflake` troca a persistência. O `prepare_demo` se recusa a gerar dados
sintéticos dentro do Snowflake. Para dados reais, ver `docs/DEPENDENCIAS.md`.
