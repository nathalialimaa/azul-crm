# Revisão final — 25/10/2026

## Fontes e escopo

Base de implementação: `azul-crm-develop (1).zip`. As versões antigas de Nathália/Larissa
não substituíram o código atual. Conferidos os dados do ZIP ANAC e o documento de pendências
da Larissa; comparados o briefing `IntrucoesHackathonAzul.pdf`, a proposta
`Plataforma_de_Inteligência_de_CRM.md`, o planejamento de sprints, a análise de concorrência
e a referência visual. O documento da Avanade que define o desafio é o briefing; a análise
de concorrência é material da equipe, não regulamento de entrega.

O levantamento da Larissa diz que o núcleo está pronto e recomenda congelamento, com ajustes
pequenos. Não foram incluídos SHAP, sentimento, mudança de busca por cláusulas ou geração de
mensagens comerciais por LLM. Não foram executados merges, publicação, vídeo ou submissão.

## Correções e acréscimos

1. **Preparação automática sem perda de dados.** Um modelo/persona incompatível anteriormente
   levava a `generate()` e apagava decisões, trocando inclusive a calibração pública por fixtures.
   Agora uma exceção específica identifica a incompatibilidade e apenas os modelos são retreinados;
   scores e relatórios são atualizados. Erros de configuração não provocam regeneração automática.
   A geração explícita por `demo` ou pelo roteiro ANAC continua substituindo a Gold por definição.
2. **VRA idempotente com período conferido.** Reimportar o mesmo arquivo com mês errado agora falha
   antes de gravar, em vez de responder sucesso por causa do hash já conhecido.
3. **Decisões locais.** O gateway Streamlit recusa status diferentes de APPROVED/REJECTED, alinhando
   esse comportamento à API. Checklist, registro da recomendação e ausência de envio preservados.
4. **Diagnóstico Ollama.** `scripts/verificar_ollama.py` testa serviço, embeddings, indexação,
   recuperação e geração com referências. Não muda o `.env` nem instala modelos automaticamente.
5. **Reprodução ANAC.** `scripts/preparar_anac.py` encadeia os comandos já existentes, validando
   hashes e entradas antes da ingestão. Os arquivos completos acompanham este ZIP privado.
   Não foi alterado o mecanismo de inicialização para carregar calibração em hospedagem pública.
6. **Documentação de ofertas.** A matriz em `BASE_REGULATORIA_OFERTAS.md` relaciona ofertas a
   cláusulas ou declara a ausência de fundamento específico. Corrigida a afirmação de que não há
   requisitos de qualificação de nível: esses requisitos existem no texto importado, mas não
   autorizam automaticamente as ofertas do MVP. Todas continuam `hypothesis_unverified`.

## Como o sistema funciona nesta entrega

ANAC bruta e procedência → normalização na Silver → clientes e viagens sintéticos calibrados →
Gold no SQLite → CLV, churn, personas e prioridade → playbook → mensagem por template, evidências
e checklist → aprovação/rejeição registrada, sem disparo. FastAPI e Streamlit mantêm suas rotas,
telas e modos local/HTTP. O lake exporta 17 tabelas em Parquet, com dicionário.

A demonstração continua distinguindo risco e valor. A regressão logística é treinada e avaliada,
mas, nesta base, a heurística permanece selecionada porque o modelo não satisfaz o critério de
promoção. Isso é o comportamento esperado, não uma falha a esconder.

## Confronto com o desafio e a proposta

| Aspecto | Situação verificada e limite |
|---|---|
| Dados sintéticos e públicos | Atendido no MVP; não há cadastro real de passageiros. |
| Calibração ANAC | Tarifas médias e distribuição por rota com assentos vendidos como proxy de demanda; atrasos pelo VRA. Não é uma base independente de toda a demanda de passageiros. |
| Bronze/Silver/Gold e formatos abertos | Implementados; exportação Parquet executada. SQLite local; adaptador Snowflake não validado em conta real. |
| Identificação de alto valor | CLV proxy de 12 meses e top 20%, com premissas de margem/desconto. Não é CLV supervisionado validado em clientes reais. |
| Churn com comparação | Treino, baseline, métricas e seleção existentes; heurística selecionada nesta execução. Índice heurístico não deve ser apresentado como probabilidade calibrada real. |
| Segmentação | Quatro grupos treinados e acionáveis. |
| Explicabilidade | Fatores e coeficientes existentes; SHAP não implementado. A afirmação “usamos SHAP” na análise de concorrência não corresponde ao código e não deve ser repetida. |
| Agente LLM que recomenda/redige | Parcial: regras/templates geram recomendação e mensagem. Ollama opcional responde perguntas, mas serviço real indisponível neste ambiente. Não alegar que o LLM escreveu as mensagens de CRM. |
| Regras de fidelidade | Corpus público importado, busca com evidências e checklist. Vigência atual ainda precisa de conferência humana. Ofertas comerciais não estão autorizadas automaticamente. |
| Sentimento em avaliações públicas | Não implementado; permanece lacuna explícita. |
| Simulador | Implementado com hipóteses, não estima efeito causal comprovado. |
| Protótipo e integração | Streamlit/FastAPI executados com base calibrada; sistemas reais não conectados. |
| IA responsável | Identificação sintética, consentimento por revisão humana e ausência de envio. Auditoria gerou 0 alertas e 2 itens de atenção; isso não prova ausência de viés. |
| Entrega e confidencialidade | Repositório privado e vídeo até 5 min exigidos pelo briefing; gestão de acesso, vídeo e submissão permanecem com a equipe. |

O briefing apresenta ML, agente LLM e sentimento entre os caminhos esperados; SHAP aparece na
proposta/análise da equipe, não como biblioteca obrigatória do regulamento. Portanto não declarar
aderência integral à proposta ampla nem transformar essas lacunas em certificação de conformidade.
A restrição de repositório privado e o prazo de 26/10 vêm do briefing fornecido, sem verificação
de eventual comunicado posterior da organização.

## Dados e resultados efetivamente executados

- Tarifas: hash idêntico ao informado; 892.505 linhas brutas e Silver, 45 ocorrências sem mapeamento.
- VRA: hash idêntico ao informado; 88.040 linhas aceitas antes de deduplicação; 87.996 na Silver;
  24 rejeitadas por estarem fora do período. O total lido é 88.064. São 101 ocorrências sem mapeamento.
- `airports.csv` faltava no anexo. Obtido do endereço OurAirports já configurado: 86.281 registros,
  hash `fe7f0d9dc2646e41b0cc520f1733d99b9c76a6b26a3e6a55f66fa89e62083ad5`.
  Não é a captura anterior de Larissa. O snapshot usado e sua procedência acompanham a entrega.
- Pipeline com seed 42: 400 clientes e 6.046 viagens; quatro personas; 80 clientes de alto valor,
  37 deles em risco; concentração de 45,47% do valor potencial nos 20% de maior valor.
- Churn selecionado: `heuristic`. Auditoria: 0 alertas, 2 itens de atenção.
- Ollama: tentativa real retornou `ConnectError / Connection refused`; não validado com modelo real.
- Suíte original: 191 testes passaram. Suíte final: **195 testes passaram**, com um aviso
  de depreciação Starlette/httpx, sem falhas. Ruff passou. A validação final e logs estão em `docs/evidencias/`.
  A suíte inclui testes de API, checklist e telas com Streamlit AppTest. Todas as páginas também
  foram percorridas com a base ANAC; endpoints principais e bloqueio de aprovação sem checklist
  passaram. Não equivale a revisão visual pixel a pixel no navegador.
- Execução em Python 3.12/Linux. O roteiro Windows usa o mesmo código, mas não foi executado em
  uma máquina Windows nesta revisão. Docker e Snowflake não foram executados em ambiente real.

As bibliotecas instaladas nesta validação estão registradas em
`docs/evidencias/versoes-validacao.json`; `requirements-tested.txt` anterior foi preservado.
O banco SQLite volumoso, ambientes virtuais, caches e os Parquets gerados não vão no ZIP.
As entradas e o roteiro permitem recriá-los; os resultados não dependem de baixar a ANAC novamente.
