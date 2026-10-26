# Relatório de progresso

## Por que existe

Oferece uma leitura rápida do estado da entrega sem esconder o que ainda depende de prova externa.

## Estado comprovado

O commit de referência é `develop@e4fea87`. O contexto registra PRs integrados para qualidade de dados, contratos fail-closed, secret scanning, consentimento, ajustes visuais e matriz de requisitos. O CI pós-merge passou com Gitleaks, Ruff, 191 testes, demo, validação, exportação de contratos e preparo de clientes.

O smoke interno registrado cobre health 200, dashboard, pipeline sintético, prioridades e RAG local com evidência e abstenção. Isso não equivale a homologação externa.

## Estimativa operacional

**90%** é uma estimativa operacional de prontidão do pacote local/documental para apresentação. Ela não é nota, cobertura de testes, percentual de requisitos oficiais cumpridos nem prova de integração.

## O que está pronto

- Fluxo local executável com SQLite e Streamlit/FastAPI.
- Base sintética calibrável com fontes públicas ANAC quando ingeridas.
- CLV de 12 meses, risco, personas, priorização e playbook documentados.
- Data lake local em Parquet, esquemas e dicionário.
- Revisão humana e consentimento fail-closed.
- Matriz de requisitos com evidências e status em [`../VALIDACAO.md`](../VALIDACAO.md).

## O que não está pronto/homologado

Snowflake real, Ollama real e avaliação de groundedness, vigência/homologação do corpus do Azul Fidelidade, dados internos reais, sentimento público, publicação privada, acesso de avaliadores, vídeo e submissão. O projeto usa clientes, fidelidade, resgates, comportamento e desfechos sintéticos.

## Como conferir com segurança

Leia a matriz, confira os caminhos indicados e use o roteiro de validação em [`04-testes-e-validacao.md`](04-testes-e-validacao.md). Não repita a suíte, Ruff ou Docker nesta etapa.
