# Schema Gold v1 — HAC-6

Contrato físico atual: CSV UTF-8, cabeçalho obrigatório na ordem abaixo, vírgula, ponto decimal, datas YYYY-MM-DD. Todos os campos obrigatórios e não nulos. Não inserir dados pessoais reais neste modo demo. Uma publicação contém um único corte; a chave lógica para armazenamento histórico será (customer_id, observation_end). O manifesto identifica a janela comum; `is_synthetic=true` é herdado pelas viagens e features via cliente.

| Entidade proposta | Implementação atual | Cardinalidade |
|---|---|---|
| gold_customer | customers.csv | Um registro por cliente |
| gold_customer_trip | trips.csv | Muitos trechos para um cliente |
| gold_customer_feature | features.csv | Uma linha por cliente/corte |
| gold_customer_score | Calculado por CrmService e exposto na API | Uma resposta por cliente/corte; não persistido |
| gold_customer_segment | Campo segment na resposta de scores | Um segmento por score; não há tabela separada |
| gold_customer_recommendation | Resposta da API em memória | Gerada sob consulta; sem histórico persistido |
| gold_campaign_simulation | Planejado, extra HAC-45 | Não existe tabela ou endpoint |

## customers.csv

| Campo | Tipo | Significado/regra |
|---|---|---|
| customer_id | string | PK não vazia; gerador usa SYN-0001 etc. |
| home_airport | string | Código IATA, 3 letras maiúsculas; existência no cadastro IATA não verificada |
| preferred_channel | enum | email ou app; preferência simulada |
| loyalty_tier | string | DEMO_UNVERIFIED no gerador; sem status oficial |
| is_synthetic | boolean | true obrigatório no validador demo; CSV aceita True/true |

## trips.csv

| Campo | Tipo | Significado/regra |
|---|---|---|
| trip_id | string | PK não vazia, única |
| customer_id | string | FK customers.customer_id |
| origin | string | IATA com 3 letras maiúsculas |
| destination | string | IATA, diferente da origem |
| flight_date | date | Dentro da observação inclusiva; futuros ficam em dataset separado |
| fare_amount | float | BRL >=0, finito; gerador arredonda a 2 casas |
| delay_minutes | integer | Atraso em minutos >=0 |

## features.csv

| Campo | Tipo | Significado/regra |
|---|---|---|
| customer_id | string | PK e FK; cobertura exata de customers |
| spend | float | Soma BRL de tarifas na observação, arredondada a 2 casas |
| frequency | integer | Número de trechos observados >=0 |
| recency_days | integer | Dias desde última viagem; sem histórico usa duração inclusiva da janela |
| incident_rate | float | Fração de trechos com atraso >=60min, [0,1]; sem histórico=0 |
| observation_end | date | Igual ao corte do manifesto |

## manifest.json

schema_version:string=1.0; mode:string=demo_fixture; seed:int; observation_start/end:date; customer_count/trip_count:int; calibrated_with_public_data:bool=false; notes:string. Gerador/fixture ainda não calibrados. A API acrescenta scoring_policy, planned_outcome_window e churn_label_status=planned_not_generated; estes são metadados de execução, não novas colunas CSV.

## Scores e recomendações

`docs/api/openapi.json` descreve tipos e limites executáveis de todas as respostas; `docs/api/examples.json` contém exemplos extraídos do aplicativo com seed 42. `docs/CONTRATOS.md` mapeia endpoints, paginação e erros.

Scores: customer_id FK, value_score [0,100], churn_risk [0,1], priority_score [0,100], estimated_value_at_risk BRL >=0, segment string, drivers lista de textos, model_version string, evaluated_at date. Fórmulas em PREMISSAS.md.
Recomendação: customer_id FK, action {code,title,reason}, draft string, evidence lista de {document_id,title,text,source,version,is_demo}, status DRAFT_REQUIRES_REVIEW, mode demo_template. Não existe recommendation_id persistido ainda.

## Contratos reservados, sem tabelas artificiais

Labels planejados: customer_id:string FK, observation_end:date, outcome_start/end:date, future_trip_count:int>=0, churn_label:int em {0,1}, generator_version:string; PK (customer_id, observation_end), somente população elegível com janela completa. Validação de labels será adicionada junto ao gerador futuro.
Scores persistidos deverão incluir snapshot, hash/configuração do modelo e chave cliente/corte. Simulação permanece fora do aceite HAC-6 do fluxo atual; seu schema deve ser definido antes de HAC-45, quando premissas de custo e retenção estiverem disponíveis.

## Validação executável

`infrastructure/gold_validation.py` verifica cabeçalhos, campos presentes, IDs únicos, FKs, marcação sintética, contagens, janela e igualdade das features com o recálculo. É chamada pelo pipeline e na inicialização da API. Qualquer falha interrompe o processo. `python -m azul_crm.pipeline.cli validate` valida uma Gold existente sem gerar dados.

O validador é para o contrato demo v1: não substitui perfilamento, calibração ANAC, auditoria de viés ou validação estatística de Larissa. Valores monetários usam float apenas para análise demonstrativa; finanças reais exigem precisão decimal acordada. A publicação atual não é atômica: pare a API antes de regenerar dados; snapshots transacionais são evolução futura.
