# Requisitos e evidências

## Por que existe

Dá ao revisor um mapa curto da matriz oficial sem duplicar sua tabela completa. A fonte de verdade é [`../VALIDACAO.md`](../VALIDACAO.md).

## Mapa de leitura

| Tema do enunciado | Onde olhar | Status honesto |
| --- | --- | --- |
| Alto valor, CLV e risco | `src/azul_crm/domain/`, `docs/CLV.md`, testes de CLV/modelagem | Parcial: dados e premissas são sintéticos. |
| Personas | `src/azul_crm/pipeline/personas.py`, `docs/PERSONAS.md` | Comprovado localmente na base sintética. |
| Retenção e recomendação | `config/playbook.toml`, `src/azul_crm/application/recommendations.py`, `docs/PLAYBOOK.md` | Parcial: ofertas são hipóteses e exigem revisão humana. |
| LLM/agente e regras públicas | `src/azul_crm/infrastructure/rag.py`, `docs/BASE_DE_CONHECIMENTO.md` | Não homologado: Ollama real/groundedness não foram avaliados. |
| Sentimento público | matriz e ausência de pipeline correspondente | Não homologado. |
| Data lake e continuidade | `src/azul_crm/infrastructure/lake.py`, `docs/DATA_LAKE.md` | Local comprovado; Snowflake real bloqueado externamente. |
| Protótipo | `streamlit_app.py`, `frontend/app.py`, testes de deploy/página | Comprovado localmente; hospedagem/acesso pendentes. |
| IA responsável/LGPD | `src/azul_crm/pipeline/bias_audit.py`, consentimento e proveniência | Parcial: auditoria é sintética. |
| Pitch e entrega | [`06-roteiro-pitch.md`](06-roteiro-pitch.md), vídeo/acesso/submissão | Entregáveis externos sem prova neste checkout. |

## Como testar com segurança

Para cada linha, siga a cadeia **requisito → implementação → evidência/teste → status** em [`../VALIDACAO.md`](../VALIDACAO.md). Um teste de contrato local não prova serviço real; documentação de uma integração não é execução dela.
