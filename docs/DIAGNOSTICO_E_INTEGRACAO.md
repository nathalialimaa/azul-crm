# Diagnóstico inicial e integração

O diagnóstico foi apresentado antes das alterações. Esta cópia registra o estado encontrado e as decisões, não substitui o relatório final de validação.

## Fontes efetivamente examinadas

| Fonte | Uso |
|---|---|
| ZIP de Nathália | Base de código, contratos v1, qualidade Gold e testes |
| ZIP de Larissa | Ingestor ANAC, schema e procedência Bronze |
| Imagem Inteligência de CRM | Paleta, sidebar, filtros, cards, matriz e painel de ação |
| Plataforma de Inteligência de CRM.md | Fluxo analítico, RAG, explicabilidade, simulação e guardrails |
| Sugestão de Sprints.md | Matriz de responsabilidades e entregas históricas |
| Análise de Concorrência.pdf | Posicionamento e cuidado com alegações ainda não implementadas |
| Instruções Hackathon.pdf | Regras prioritárias, privacidade, sintéticos e prazo de submissão |

A imagem estava disponível e foi aberta, apesar da mensagem inicial de arquivo ausente.

## Estado inicial e evidências

| Tarefas correlatas do planejamento | Responsável previsto no plano | Estado inicial | Evidência |
|---|---|---|---|
| Arquitetura, portas, separação e contratos | Luan/Davi | Implementado; homologação parcial | domain/ports.py, api/schemas.py, docs/CONTRATOS.md |
| Backlog, reuniões, revisão coletiva | Luan/equipe | Não comprovado pelo código | Documentação não demonstra realização |
| ETL, Bronze/Silver/Gold | Nathália | Parcial, fixtures | pipeline/stages.py |
| Base sintética e reprodutibilidade | Nathália/Larissa | Implementada para demo | DemoSyntheticGenerator e teste de seed |
| Regras de limpeza/validação/duplicidades | Larissa/Nathália | Implementadas para Gold v1 | gold_validation.py, test_sprint1.py |
| ANAC Bronze local | Larissa | Parcial | pipeline/anac.py |
| Download e integração pública Silver/Gold | Nathália/Larissa | Pendente | Ausente |
| Valor, risco, segmentos e prioridade | Nathália | Baselines implementados | scoring.py |
| Features e explicações | Nathália/Larissa | Implementadas para heurística | features.py, crm.py |
| ML, rótulos futuros, avaliação e SHAP | Nathália | Pendente | Manifesto planned_not_generated |
| API, indicadores e detalhes | Davi | Implementados | routes.py |
| Dashboard, filtros, priorização e 360 | Ingrid | Parcial | frontend/app.py simples |
| Consulta ao backend | Ingrid/Davi | Implementada | api_client.py |
| Corpus público e RAG semântico | Davi | Pendente | Somente knowledge.json fictício e busca lexical |
| Agente e fontes | Davi | Parcial | TemplateMessageGenerator, RecommendationService |
| Testes/regressão | Larissa/equipe | Parcial | 15 testes da base de Nathália |
| Homologação externa | Equipe | Não comprovada | Nenhuma credencial/resultado externo |
| Simulação e sentimento (extras) | Equipe | Pendentes | Ausentes |
| Pitch, ensaio, acesso e submissão | Equipe | Dependentes de ação humana | Fora do repositório |

A atribuição acima é a do plano; não afirma autoria individual de cada arquivo ou que reuniões ocorreram.

## Divergências encontradas

1. Stack real: FastAPI + Streamlit, não Django/React.
2. “RAG” existente é recuperação lexical de fixture com template.
3. Risco é índice heurístico, não modelo treinado/calibrado.
4. PDF de concorrência fala em SHAP, treino e calibração como capacidades; não havia código correspondente.
5. Gold v1 aceita apenas demo_fixture e rejeita alegação de calibração. A v2 precisa contrato separado para SQL.
6. Ingestor ANAC original tem cabeçalho exato, extrai período da primeira linha e copia por nome. Não há download, mapeamento, idempotência robusta nem validação linha a linha.
7. A imagem sugere CLV e “probabilidade”; isso precisou ser rotulado como proxy/índice até existir validação.
8. Planejamento 09–16/10 é histórico. Instruções oficiais exigem entrega em 26/10 e repositório privado.

## O que foi reaproveitado

De Nathália: entidades e portas, serviços CRM/features/recomendações, regras de pontuação e elegibilidade, rotas e schemas v1, validação CSV, configuração de janelas, gerador e publicador v1, fixtures, testes e documentação histórica.

De Larissa: `pipeline/anac.py` foi preservado, incluindo ingestor local, SHA-256 e procedência. O parser novo importa seus `EXPECTED_COLUMNS` e `SOURCE_PAGE`; a operação v2 estende a abordagem com download, armazenamento por hash, validação completa de período, normalização e publicação SQL. O ingestor antigo continua acessível para compatibilidade, mas os comandos v2 são recomendados.

Alterações principais: Store SQLite/Snowflake, repositório SQL, Gold v2, fidelidade e desfechos simulados, treinamento/avaliação, índice RAG, consultas estruturadas, UI, revisão humana, simulador, SQL e instruções de execução. Não houve reescrita do núcleo de domínio nem alteração da semântica dos campos v1.

## Decisões que não exigiram interrupção

Manter a stack, usar SQLite como demonstração explícita, não inventar política de fidelidade, não publicar externamente, não promover modelo inferior ao baseline e não copiar segredos/ambientes virtuais são decisões coerentes com o pedido.

Conta Snowflake, instalação de modelos, revisão do corpus e acesso dos avaliadores são dependências de ativação/homologação. Não exigem que Nathália reprograme o RAG. Passos em DEPENDENCIAS.md.
