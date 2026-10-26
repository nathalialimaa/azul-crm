# Roteiro de pitch — até 5 minutos

## Por que existe

Converte a documentação em uma narrativa curta, demonstrável e honesta. O pitch é apresentação; não substitui teste técnico nem homologação.

## Roteiro sugerido

### 0:00–0:35 — Problema e proposta

“O Azul CRM é um MVP privado para ajudar a priorizar clientes de alto valor e risco de evasão. Ele organiza evidências, sugere uma próxima ação e mantém a decisão sob revisão humana.”

### 0:35–1:20 — Dados e premissas

“A demonstração usa clientes e comportamento sintéticos. Tarifas, demanda e atrasos podem ser calibrados com arquivos públicos da ANAC quando ingeridos. Margem, desconto e ofertas são hipóteses explicitadas. Nenhum dado interno real foi usado.”

### 1:20–2:25 — Painel e explicabilidade

Mostrar visão geral, corte de alto valor, risco, CLV de 12 meses, personas e fatores. Explicar que CLV é valor potencial sob premissas, não receita observada de clientes reais.

### 2:25–3:25 — Próxima ação com proteção

Selecionar cliente sintético, abrir evidências, mostrar playbook e rascunho. Mostrar consentimento, revisão humana e bloqueio sem evidência. Reforçar que o sistema não envia mensagens.

### 3:25–4:15 — Arquitetura e validação

Mostrar rapidamente pipeline, SQLite/Parquet, API/FastAPI e Streamlit. Citar CI e testes registrados, sem alegar execução nesta apresentação. Mostrar a matriz requisito → implementação → evidência → status.

### 4:15–5:00 — Impacto e limites

“O fluxo local é um ponto de partida explicável. Ainda faltam homologar Snowflake real, Ollama real e groundedness, corpus oficial/vigência, publicação privada, acesso, vídeo e submissão. Esses limites são parte do plano de evolução, não resultados já entregues.”

## Como testar com segurança antes de apresentar

Faça o smoke visual de [`04-testes-e-validacao.md`](04-testes-e-validacao.md) em `127.0.0.1`, com dados sintéticos e sem credenciais. Não invente métricas, não mostre dados privados e não apresente documentação como prova de uma integração que não foi executada.
