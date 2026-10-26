# Data lake em camadas (Parquet) e dicionário de dados

O enunciado pede uma estrutura de dados organizada, em camadas e com formato aberto, para que os
dados sintéticos possam ser trocados por reais sem reconstruir a solução. Este é o desenho.

## Camadas

| Camada | O que guarda | Tabelas |
|---|---|---|
| **bronze** (bruta) | O que chegou, sem alterar, com procedência | `sources`, `raw_rows` |
| **silver** (tratada) | Padronizado e validado | `airports`, `fares`, `operations` |
| **gold** (analítica) | Consumido pelos modelos e pelo protótipo | `customers`, `trips`, `features`, `loyalty`, `loyalty_transactions`, `outcomes`, `scores`, `personas`, `bias_audit_groups`, `manifest`, `decisions` |

Bronze e silver só têm dados quando se ingere arquivo público (`azul-crm fares`, `vra`, `airports`).
Com a base sintética pura, só a gold é preenchida.

## Como gerar

```bash
python -m azul_crm.cli export-lake            # saída em data/lake (ou --out outra-pasta)
```

Gera:

- `<camada>/<tabela>.parquet`: tabelas tipadas, com a descrição de cada coluna dentro do arquivo;
- `data_dictionary.json` e `DATA_DICTIONARY.md`: dicionário de dados completo, tipos, chaves,
  origem, contagem de linhas e hash do conteúdo;
- `snowflake_typed.sql`: DDL das mesmas tabelas para o Snowflake, com comentários nas colunas.

A saída é reproduzível por código: mesma base e mesma semente produzem o mesmo conteúdo (o hash do
conteúdo no dicionário prova isso). A pasta `data/lake` não vai para o Git nem para a imagem Docker.

## O esquema é um contrato

O esquema de cada tabela fica em `src/azul_crm/infrastructure/lake.py` e é a **única fonte** do
dicionário, do DDL e da validação. O exportador **recusa** coluna fora do esquema, coluna
obrigatória ausente, valor de tipo errado e data e hora sem fuso, e nesse caso não grava nada.

## Trocar sintético por real

1. Alimentar as tabelas silver e gold com as **mesmas colunas e tipos** do dicionário.
2. Rodar `export-lake`: se algo divergir, o erro aponta tabela, coluna e valor.
3. `customers.is_synthetic = false` só para dados autorizados; o dicionário passa a avisar que há
   clientes não sintéticos e que a LGPD se aplica.
4. Retreinar churn e personas com os dados reais (`train`, `personas`). Os pesos sintéticos não
   valem para clientes reais.

## Snowflake

O adaptador atual do app guarda JSON em colunas `VARIANT` nos schemas `BRONZE`, `SILVER` e
`GOLD` (`sql/01_setup.sql`). O arquivo `snowflake_typed.sql` cria as tabelas **tipadas** em schemas
`LAKE_BRONZE`, `LAKE_SILVER` e `LAKE_GOLD`, para não colidir com elas. Para BI e para os modelos, as
tabelas tipadas são as indicadas. Migrar o app para lê-las é trabalho futuro.

**Não testado em conta Snowflake.** O DDL e o exemplo de `COPY INTO` a partir de Parquet são
gerados e revisados, mas nunca foram executados. Em especial, a carga de colunas de lista (`ARRAY`)
deve ser conferida na primeira execução.

## Escala (arquivos grandes da ANAC)

O arquivo mensal de tarifas da ANAC tem cerca de 25 MB (centenas de milhares de linhas). Foi
medido com um arquivo **simulado** do mesmo formato, de 800 mil linhas, em Linux. Ainda **não**
foi medido com o arquivo real nem no Windows, então trate os números como ordem de grandeza.

| Etapa | Tempo | Memória no pico |
|---|---|---|
| `fares` (ingestão, 800 mil linhas) | ~35 s | ~2 GB |
| `demo --public` (lê as tarifas em lotes) | ~8 s | ~160 MB |
| `export-lake` (em lotes de 20 mil linhas) | ~25 s | ~250 MB |

- A ingestão (`fares`) é a etapa mais pesada: mantém as linhas na memória antes de gravar. Feche
  outros programas e ingira **um mês por vez**.
- O banco local (`data/crm.sqlite3`) passa de ~900 MB com um mês de dados da ANAC. Ele não vai
  para o Git nem para a imagem Docker.
- O `export-lake` grava numa pasta temporária e só troca os arquivos no fim. Se qualquer tabela
  falhar, a saída anterior fica intacta e nada novo é criado.

## Limitações

- Dados sintéticos: o lake descreve o gerador, não clientes reais.
- `demand` (demanda) não tem produtor ainda e por isso não entra no lake.
- Em `silver.airports` só as colunas do dicionário são mantidas; as demais da OurAirports são
  ignoradas.
- O dicionário da gold reflete o que o código grava hoje. Se um campo novo for criado, o export
  falha até o esquema ser atualizado, e isso é intencional.
