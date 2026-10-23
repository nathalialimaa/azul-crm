# Playbook de retenção por persona

Define a **próxima melhor ação** de cada persona. Substitui as duas ações genéricas de antes
(contato de escuta e de relacionamento) por um catálogo em `config/playbook.toml`.

## Como funciona

1. A persona do cliente tem três características, calculadas no treino: **valor alto**,
   **esfriando** (média ≥ 90 dias sem voar) e **atrasos frequentes** (≥ 50% das viagens com
   atraso de 60 min ou mais).
2. As regras do playbook casam essas características. **A primeira regra que casa vence**, então
   a ordem é a prioridade. O playbook precisa cobrir as 8 combinações; senão a aplicação não inicia.
3. Cada regra aponta uma **ação principal** e uma **oferta sugerida**.

| Persona (exemplo) | Ação principal | Oferta sugerida (hipótese) |
|---|---|---|
| Atrasos frequentes | Recuperação de serviço | Gesto de reconhecimento pelo atraso |
| Alto valor esfriando | Reativação personalizada | Bônus de pontos condicionado a nova viagem |
| Alto valor ativo (fiéis) | Reconhecimento e relacionamento | Cortesia de upgrade ou benefício de status |
| Baixo volume esfriando | Reativação de baixo custo | Oferta na rota favorita |
| Baixo volume ativo | Incentivo à próxima viagem | Oferta na rota favorita |

## Guardrails (o que impede o agente de prometer o que não pode)

- **A mensagem só contém a ação principal**, com fatos reais do cliente (dias desde a última
  viagem, viagens com atraso, rota mais usada). A oferta **nunca entra no texto**. Um teste
  automático varre todos os rascunhos atrás de palavras como bônus, upgrade, desconto e pontos.
- **Ofertas são hipóteses** (`hypothesis_unverified`). Só podem virar `verified` registrando a
  fonte oficial; o playbook recusa carregar uma oferta verificada sem fonte.
- Sem a evidência de governança, nenhuma ação é liberada (`NO_ACTION`).
- Se faltar um fato para o texto (por exemplo, nenhuma viagem com atraso), usa-se um texto
  genérico em vez de inventar um número.
- Todo rascunho exige revisão humana e nada é enviado.

## O que mudou na tela

- **Ações de CRM**: tabela de estratégia por persona (ação, oferta, custo e valor protegido
  hipotéticos), e abaixo a recomendação do cliente com persona, canal sugerido, rascunho, oferta
  em destaque como hipótese e as evidências.
- API: `GET /api/v1/playbook` e novos campos `persona`, `channel` e `offer` em
  `POST /api/v1/agent/recommend`.

## Premissas (todas hipóteses)

Custo por contato e retenção assumida de cada ação ficam em `config/playbook.toml`. O cenário da
tela usa o **CLV em risco** (margem, ver `docs/CLV.md`) vezes a retenção assumida, menos o
custo. **Não estima ganho real**; precisa de teste A/B antes de qualquer uso.

## Para evoluir com regras reais

1. Coletar o regulamento vigente do Azul Fidelidade e registrar fonte e versão.
2. Marcar a oferta correspondente como `verified` com `source`.
3. Só então decidir, com a área dona, se ela pode aparecer em um texto aprovado.
