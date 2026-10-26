# Azul CRM — Entrega Final e Pitch

## Por que este pacote existe

Este pacote reúne a explicação final do MVP local, suas evidências e suas limitações em documentos pequenos. Ele serve para revisão humana, preparação do pitch e execução segura da demonstração. A matriz completa permanece em [`../VALIDACAO.md`](../VALIDACAO.md); os documentos abaixo não a substituem.

## Estado e escopo

- Base documental: `develop@e4fea87`.
- Produto: MVP privado de CRM explicável com clientes sintéticos, CLV, risco de evasão, personas, priorização, recomendações com evidências e revisão humana.
- Estimativa operacional: **90%** de prontidão documental/local para a entrega. Não é percentual oficial de conclusão, cobertura de testes ou homologação.
- Sem alegação de Snowflake real, Ollama real/groundedness, corpus oficial do Azul Fidelidade, dados internos reais ou hospedagem homologada.

## Índice

| Documento | Por que existe | Como usar/testar com segurança |
| --- | --- | --- |
| [`00-progresso.md`](00-progresso.md) | Resume o que está integrado e o que falta. | Compare cada item com a evidência indicada; trate 90% como estimativa. |
| [`01-arquitetura-e-fluxos.md`](01-arquitetura-e-fluxos.md) | Explica camadas, contratos e fluxo da demonstração. | Leia os caminhos de código e use somente o modo local/sintético. |
| [`02-requisitos-e-evidencias.md`](02-requisitos-e-evidencias.md) | Guia a leitura requisito → implementação → evidência → status. | Abra a matriz e não transforme hipótese em requisito comprovado. |
| [`03-guia-para-iniciante.md`](03-guia-para-iniciante.md) | Ensina os termos e a demonstração sem pressupor contexto. | Execute só os comandos locais, na raiz, sem credenciais. |
| [`04-testes-e-validacao.md`](04-testes-e-validacao.md) | Lista validações reproduzíveis e smoke visual. | Nesta etapa, apenas conferir; os comandos não foram executados. |
| [`05-limitacoes-e-proximos-passos.md`](05-limitacoes-e-proximos-passos.md) | Mantém riscos e dependências externas explícitos. | Use-o para preparar perguntas e próximos handoffs. |
| [`06-roteiro-pitch.md`](06-roteiro-pitch.md) | Organiza um pitch de até cinco minutos. | Apresente somente evidências locais e ressalvas. |

## Fontes de detalhe

- [README técnico](../../README.md)
- [Índice e premissas](../INDICE.md)
- [Arquitetura](../ARQUITETURA.md)
- [Data lake](../DATA_LAKE.md)
- [Dependências externas](../DEPENDENCIAS.md)
- [Deploy e acesso](../DEPLOY.md)
- [Validação completa](../VALIDACAO.md)
- [CI](../../.github/workflows/ci.yml)

## Regra de segurança

Comece na raiz do worktree. Use dados sintéticos e `127.0.0.1`; não copie credenciais, não exponha a API e não configure integrações externas para a demonstração local. Teste somente o escopo autorizado no relatório de validação.
