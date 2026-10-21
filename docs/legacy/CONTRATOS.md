> Atualização Sprint 1: veja SCHEMA_GOLD.md e PREMISSAS.md; exemplos completos gerados em api/examples.json.

# Contratos v1 e dicionário de dados

## Modelo de dados canônico

Chaves são strings e não contêm identificadores pessoais. Datas usam ISO `YYYY-MM-DD`. Valores monetários estão em BRL. Os CSVs são UTF-8 com cabeçalho e separador vírgula; decimais usam ponto. Na API, datas são strings ISO e booleanos são JSON `true/false`.

| Tabela / campo | Tipo | Significado e restrição |
|---|---|---|
| customers.customer_id | string | PK fictícia `SYN-0001`; única e obrigatória |
| customers.home_airport | string | Código IATA de três letras maiúsculas |
| customers.preferred_channel | string | `email` ou `app`; preferência simulada |
| customers.loyalty_tier | string | `DEMO_UNVERIFIED`; não representa nível oficial |
| customers.is_synthetic | bool | `True` nos CSVs gerados; `true` na API |
| trips.trip_id | string | PK única |
| trips.customer_id | string | FK obrigatória de customers |
| trips.origin / destination | string | Rota fictícia em IATA; origem diferente do destino |
| trips.flight_date | date | Data da viagem na observação |
| trips.fare_amount | float | Tarifa BRL finita e não negativa |
| trips.delay_minutes | int | Minutos de atraso não negativos |
| features.customer_id | string | Uma linha por cliente |
| features.spend | float | Soma de tarifas dentro da observação |
| features.frequency | int | Quantidade de viagens dentro da observação |
| features.recency_days | int | Dias entre última viagem observada e corte; sem viagem, duração inclusiva da janela |
| features.incident_rate | float | Fração das viagens com atraso >= 60 min; zero se não há viagem |
| features.observation_end | date | Corte usado nas features |
| manifest.schema_version | string | `1.0` |
| manifest.mode | string | `demo_fixture` |
| manifest.seed | int | Semente reprodutível |
| manifest.observation_start/end | date | Janela inclusiva |
| manifest.calibrated_with_public_data | bool | `false` até a calibração real |

O repositório valida duplicidade de PK e integridade das FKs; objetos validam invariantes básicas. As regras completas de qualidade e calibração ainda serão implementadas por Larissa. Evitar `float` para lançamentos financeiros reais; este protótipo não realiza cobrança. Uma futura integração deve decidir precisão/escala monetária no contrato.

`features.csv` é uma saída para o time analítico. A API recalcula as mesmas features a partir das viagens usando `FeatureBuilder`, em vez de confiar em um segundo cálculo. Quando houver publicação de scores em lote, definir um snapshot/versionamento comum para features e scores.

## Endpoints existentes

Prefixo `/api/v1` para negócio; `/health` para saúde. A documentação completa e o JSON Schema estão em `/docs` e `/openapi.json`.

| Método | Caminho | Resposta / propósito |
|---|---|---|
| GET | `/health` | Status do processo |
| GET | `/api/v1/metadata` | Seed, modo, janela, limitações e contagens |
| GET | `/api/v1/customers?offset=0&limit=100` | `{items,total,offset,limit}`; limite máximo 500 |
| GET | `/api/v1/customers/{id}` | `{customer,trips,scores}` para visão 360 |
| GET | `/api/v1/customers/{id}/scores` | Um score |
| GET | `/api/v1/retention/priorities?limit=100&segment=...` | Lista ordenada; filtro exato de segmento; limite máximo 500 |
| GET | `/api/v1/segments` | Lista de `{segment,count}` |
| GET | `/api/v1/customers/{id}/recommendations` | Recomendação determinística de demonstração |
| POST | `/api/v1/agent/recommend` | Recomendação; corpo abaixo |

Requisição:

```json
{"customer_id": "SYN-0001"}
```

Formato de score (valores apenas ilustrativos):

```json
{
  "customer_id": "SYN-0001",
  "value_score": 77.4,
  "churn_risk": 0.73,
  "priority_score": 56.5,
  "estimated_value_at_risk": 12500.0,
  "segment": "Alto Valor em Risco",
  "drivers": ["Gasto observado: R$ 17123.00", "Recência: 160 dias"],
  "model_version": "value_baseline_v1+baseline_heuristic_v1",
  "evaluated_at": "2026-09-30"
}
```

Formato de recomendação:

```json
{
  "customer_id": "SYN-0001",
  "action": {
    "code": "CONTACT_SUPPORT",
    "title": "Contato de escuta",
    "reason": "Entender possíveis atritos, sem prometer benefícios."
  },
  "draft": "Rascunho de demonstração para revisão.",
  "evidence": [{
    "document_id": "demo-contact-v1",
    "title": "Catálogo fictício de contato de relacionamento",
    "text": "Conteúdo demonstrativo, sem benefícios oficiais.",
    "source": "fixture interna de demonstração; não é política da Azul",
    "version": "1.0",
    "is_demo": true
  }],
  "status": "DRAFT_REQUIRES_REVIEW",
  "mode": "demo_template"
}
```

Cliente inexistente retorna `404 {"detail":"Cliente não encontrado"}`. Payload ou paginação inválidos retornam 422, com erros de validação do FastAPI. Filtro sem resultados retorna 200 com lista vazia. O endpoint POST gera um rascunho em memória, sem persistência e sem efeito externo. GET de recomendações é aceitável somente enquanto for determinístico e sem custo/efeito; quando houver LLM e auditoria persistida, usar POST para gerar e GET para consultar a recomendação salva.

A UI carrega até 500 prioridades e calcula indicadores **sobre esse recorte**, não sobre toda uma base maior. Antes de aumentar o volume, implementar agregação no servidor, paginação das prioridades e limites de requisição. Esta versão busca viagens em memória e favorece legibilidade para uma amostra pequena; índices por cliente ou execução em lote serão necessários em escala.

## Contratos planejados — não implementados

Não existem campos ou tabelas vazios fingindo dados oficiais. A evolução deve adicionar schemas explícitos e testes compatíveis:

| Entidade futura | Campos mínimos propostos |
|---|---|
| Operação/experiência | trip_id, cancelled, connection_disruption, experience_score, complaint_indicator |
| Fidelidade | customer_id, points_balance, points_earned, points_redeemed, benefit_usage, loyalty_tier verificado |
| Interação CRM | interaction_id, customer_id, action_type, channel, sent_at, accepted, converted, incremental_value, is_synthetic |
| Churn label | customer_id, observation_end, outcome_start, outcome_end, churn_label, generator_version |
| Score publicado | customer_id, scores, drivers, model_version, schema_version, evaluated_at, data_snapshot_id |
| Decisão auditada | recommendation_id, customer_id, eligible_action_ids, selected_action, evidence_ids, source_versions, model_version, review_status |

`POST /simulations` e um chat livre não estão implementados. São tarefas futuras. A tela de recomendação recebe o cliente selecionado e usa saída estruturada; isso reduz a superfície inicial de integração.
