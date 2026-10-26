# Entrega Final e Pitch — Plano documental

> **For agentic workers:** Esta execução é documental; não exige subagentes, suíte, Ruff, Docker, PR ou merge.

**Goal:** Criar um pacote Markdown versionado para explicar, demonstrar e validar com segurança o estado local do Azul CRM.

**Architecture:** Um índice em `docs/entrega-final-pitch/README.md` aponta para relatórios focados. Cada relatório usa links relativos para a documentação existente e separa evidência local de dependências externas.

**Tech Stack:** Markdown, links relativos, comandos já documentados no repositório e validações textuais/read-only.

**Spec:** Pedido da sessão e `docs/VALIDACAO.md`.

## Global Constraints

- Documentar apenas o estado comprovado e marcar estimativas e lacunas.
- Não declarar Snowflake, Ollama real/groundedness, corpus oficial, dados internos ou hospedagem homologados.
- Não gerar PDF nem executar suíte, Ruff ou Docker.
- Validar `git diff --check` e links/caminhos sem alterar código.

### Tasks

- [x] Mapear contexto, fonte oficial, matriz e arquivos técnicos necessários.
- [x] Criar índice e relatórios de progresso, arquitetura, requisitos, iniciante, validação, limitações e pitch.
- [ ] Validar diff, links e caminhos; fazer commits pequenos e push.
- [ ] Atualizar o handoff do piso e reportar ao Orbe antes da revisão Prisma.
