"""Data lake em camadas (bronze, silver, gold) em Parquet, com esquema e dicionário de dados.

O app guarda os dados como JSON no SQLite (ou VARIANT no Snowflake). Este módulo publica os
mesmos dados como **tabelas tipadas em formato aberto**, que servem de contrato:

* o esquema de cada tabela vive no código (``TABLES``) e é a única fonte do dicionário de dados,
  do DDL do Snowflake e da validação;
* dado fora do esquema (coluna extra, ausente ou valor inválido) **falha** em vez de ser gravado;
* para trocar os dados sintéticos por reais, basta alimentar as mesmas tabelas com as mesmas
  colunas, sem reconstruir modelos nem app.

Execução: ``python -m azul_crm.cli export-lake`` (saída em ``data/lake``).
"""

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

LAYERS = ("bronze", "silver", "gold")
BATCH_SIZE = 20000  # linhas por lote: a memória não cresce com o tamanho da tabela

ARROW_TYPES = {
    "string": pa.string(),
    "int64": pa.int64(),
    "float64": pa.float64(),
    "bool": pa.bool_(),
    "date": pa.date32(),
    "timestamp": pa.timestamp("us", tz="UTC"),
    "list_string": pa.list_(pa.string()),
    "list_date": pa.list_(pa.date32()),
    "json": pa.string(),  # texto JSON; vira VARIANT no Snowflake
}
SNOWFLAKE_TYPES = {
    "string": "VARCHAR",
    "int64": "NUMBER(38,0)",
    "float64": "FLOAT",
    "bool": "BOOLEAN",
    "date": "DATE",
    "timestamp": "TIMESTAMP_TZ",
    "list_string": "ARRAY",
    "list_date": "ARRAY",
    "json": "VARIANT",
}


@dataclass(frozen=True)
class Col:
    name: str
    dtype: str
    description: str
    nullable: bool = False
    source: str = ""  # chave no registro de origem, quando difere do nome da coluna

    @property
    def key(self) -> str:
        return self.source or self.name


@dataclass(frozen=True)
class Table:
    layer: str
    name: str
    description: str
    origin: str
    columns: tuple[Col, ...]
    primary_key: tuple[str, ...] = ()
    strict: bool = True  # coluna extra na origem é erro
    ignore_keys: tuple[str, ...] = ()  # chaves já aproveitadas em outra tabela derivada

    @property
    def qualified(self) -> str:
        return f"{self.layer}.{self.name}"


def _t(layer, name, description, origin, columns, **kwargs):
    return Table(layer, name, description, origin, tuple(columns), **kwargs)


TABLES = (
    # ---- bronze: o que chegou, com procedência ----
    _t(
        "bronze",
        "sources",
        "Um registro por arquivo público ingerido, com endereço, período e checksum.",
        "store.sources (ingestão ANAC tarifas e VRA)",
        [
            Col("sha256", "string", "SHA-256 do arquivo original; identifica a fonte."),
            Col("dataset", "string", "Conjunto de dados: fares (tarifas) ou vra (voos)."),
            Col("period", "string", "Mês de referência no formato AAAA-MM."),
            Col("source_url", "string", "Endereço oficial de origem ou official_local_file."),
            Col("rows", "int64", "Linhas lidas do arquivo."),
            Col("silver_rows", "int64", "Linhas que chegaram à silver após deduplicação."),
            Col("unmatched", "int64", "Linhas com aeroporto não resolvido para IATA."),
            Col("ingested_at", "timestamp", "Momento da ingestão (UTC)."),
        ],
        primary_key=("sha256",),
    ),
    _t(
        "bronze",
        "raw_rows",
        "Linhas originais dos arquivos públicos, sem alteração, como JSON.",
        "store.raw_rows",
        [
            Col("source_sha256", "string", "SHA-256 do arquivo de origem.", source="sha256"),
            Col("line", "int64", "Número da linha no arquivo original (cabeçalho = 1)."),
            Col(
                "row_json",
                "json",
                "Linha original, coluna a coluna, como texto JSON.",
                source="row",
            ),
        ],
        primary_key=("source_sha256", "line"),
    ),
    # ---- silver: padronizado e validado ----
    _t(
        "silver",
        "airports",
        "Dimensão de aeroportos (OurAirports) usada para converter ICAO em IATA.",
        "store.airports (OurAirports; colunas fora desta lista são ignoradas)",
        [
            Col("id", "string", "Identificador do aeroporto na OurAirports.", nullable=True),
            Col("ident", "string", "Código do aeroporto (ICAO para os brasileiros)."),
            Col("icao_code", "string", "Código ICAO de 4 letras.", nullable=True),
            Col("iata_code", "string", "Código IATA de 3 letras.", nullable=True),
            Col("name", "string", "Nome do aeroporto.", nullable=True),
            Col("latitude_deg", "float64", "Latitude em graus.", nullable=True),
            Col("longitude_deg", "float64", "Longitude em graus.", nullable=True),
            Col("iso_country", "string", "País (ISO 3166-1).", nullable=True),
            Col("municipality", "string", "Município.", nullable=True),
            Col("mapping_sha256", "string", "SHA-256 da dimensão usada no mapeamento."),
            Col("source", "string", "Endereço de origem da dimensão."),
        ],
        primary_key=("ident",),
        strict=False,
    ),
    _t(
        "silver",
        "fares",
        "Tarifas aéreas domésticas comercializadas (ANAC), padronizadas por rota e mês de venda.",
        "store.fares (microdados de tarifas da ANAC)",
        [
            Col("period", "string", "Mês de venda no formato AAAA-MM."),
            Col("airline", "string", "Empresa aérea (ICAO), por exemplo AZU."),
            Col("origin_icao", "string", "Aeroporto de origem (ICAO)."),
            Col("destination_icao", "string", "Aeroporto de destino (ICAO)."),
            Col("origin", "string", "Origem em IATA; nulo se não resolvida.", nullable=True),
            Col("destination", "string", "Destino em IATA; nulo se não resolvido.", nullable=True),
            Col("origin_status", "string", "Resultado do mapeamento da origem."),
            Col("destination_status", "string", "Resultado do mapeamento do destino."),
            Col("fare", "float64", "Tarifa média comercializada (BRL)."),
            Col("seats", "int64", "Assentos comercializados na tarifa."),
            Col("source_sha256", "string", "SHA-256 do arquivo de origem."),
            Col("mapping_version", "string", "Versão da dimensão de aeroportos usada."),
            Col("is_synthetic", "bool", "Falso: dado público real."),
            Col("period_kind", "string", "Significado do período: sale_month (mês de venda)."),
        ],
    ),
    _t(
        "silver",
        "operations",
        "Voos realizados e cancelados (VRA da ANAC), com atraso calculado.",
        "store.operations (VRA)",
        [
            Col("period", "string", "Mês de referência (AAAA-MM)."),
            Col("airline", "string", "Empresa aérea (ICAO)."),
            Col("flight_number", "string", "Número do voo."),
            Col("origin_icao", "string", "Aeroporto de origem (ICAO)."),
            Col("destination_icao", "string", "Aeroporto de destino (ICAO)."),
            Col("origin", "string", "Origem em IATA.", nullable=True),
            Col("destination", "string", "Destino em IATA.", nullable=True),
            Col("origin_status", "string", "Resultado do mapeamento da origem."),
            Col("destination_status", "string", "Resultado do mapeamento do destino."),
            Col("scheduled_departure", "timestamp", "Partida prevista (UTC).", nullable=True),
            Col("actual_departure", "timestamp", "Partida real (UTC).", nullable=True),
            Col("delay_minutes", "float64", "Atraso na partida; nulo se faltou horário.", True),
            Col("cancelled", "bool", "Verdadeiro se cancelado; nulo se não informado.", True),
            Col("source_sha256", "string", "SHA-256 do arquivo de origem."),
            Col("mapping_version", "string", "Versão da dimensão de aeroportos usada."),
            Col("is_synthetic", "bool", "Falso: dado público real."),
        ],
    ),
    # ---- gold: consumido por modelos e protótipo ----
    _t(
        "gold",
        "customers",
        "Clientes (sintéticos). Chave pseudonimizada, sem dado pessoal.",
        "pipeline.extended.generate",
        [
            Col("customer_id", "string", "Identificador pseudonimizado do cliente (SYN-nnnn)."),
            Col("home_airport", "string", "Aeroporto de origem do cliente (IATA)."),
            Col(
                "preferred_channel",
                "string",
                "Canal preferido de contato: email ou app (simulado).",
            ),
            Col(
                "loyalty_tier",
                "string",
                "Placeholder do cadastro; o tier simulado fica em loyalty.",
            ),
            Col("is_synthetic", "bool", "Verdadeiro para clientes sintéticos."),
        ],
        primary_key=("customer_id",),
    ),
    _t(
        "gold",
        "trips",
        "Viagens dos clientes na janela de observação.",
        "pipeline.extended.generate",
        [
            Col("trip_id", "string", "Identificador da viagem."),
            Col("customer_id", "string", "Cliente (chave estrangeira de customers)."),
            Col("origin", "string", "Origem (IATA)."),
            Col("destination", "string", "Destino (IATA)."),
            Col("flight_date", "date", "Data do voo."),
            Col("fare_amount", "float64", "Valor pago em dinheiro (BRL); zero se pago com pontos."),
            Col("delay_minutes", "int64", "Minutos de atraso, não negativo."),
        ],
        primary_key=("trip_id",),
    ),
    _t(
        "gold",
        "features",
        "Variáveis por cliente, calculadas só com dados da janela de observação.",
        "application.features.FeatureBuilder",
        [
            Col("customer_id", "string", "Cliente (chave estrangeira de customers)."),
            Col("spend", "float64", "Soma paga em dinheiro na janela de observação (BRL)."),
            Col("frequency", "int64", "Quantidade de viagens na janela."),
            Col(
                "recency_days",
                "int64",
                "Dias da última viagem ao fim da janela; sem viagem, janela + 1.",
            ),
            Col("incident_rate", "float64", "Fração das viagens com atraso de 60 min ou mais."),
            Col("observation_end", "date", "Último dia da janela de observação."),
        ],
        primary_key=("customer_id",),
    ),
    _t(
        "gold",
        "loyalty",
        "Programa de fidelidade simulado, por cliente. Não representa regras oficiais.",
        "pipeline.extended.generate",
        [
            Col("customer_id", "string", "Cliente (chave estrangeira de customers)."),
            Col("opening_points", "int64", "Saldo inicial de pontos."),
            Col("earned", "int64", "Pontos acumulados no período."),
            Col("redeemed", "int64", "Pontos resgatados no período."),
            Col("balance", "int64", "Saldo final = inicial + acumulado - resgatado."),
            Col("tier", "string", "Tier simulado (SIMULADO_*); não é o nível oficial."),
            Col("is_synthetic", "bool", "Verdadeiro: dado sintético."),
            Col("official_eligibility", "bool", "Sempre falso: nenhuma elegibilidade oficial."),
        ],
        primary_key=("customer_id",),
        ignore_keys=("transactions",),
    ),
    _t(
        "gold",
        "loyalty_transactions",
        "Forma de pagamento de cada viagem (dinheiro, tarifa restrita ou pontos).",
        "derivada de loyalty.transactions",
        [
            Col("trip_id", "string", "Viagem (chave estrangeira de trips)."),
            Col("customer_id", "string", "Cliente (chave estrangeira de customers)."),
            Col("payment_type", "string", "cash, restricted_cash ou points."),
            Col("cash_revenue", "float64", "Receita em dinheiro (BRL)."),
            Col("reference_fare", "float64", "Tarifa de referência antes de desconto ou pontos."),
            Col("points_redeemed", "int64", "Pontos usados na viagem."),
            Col("is_synthetic", "bool", "Verdadeiro: dado sintético."),
        ],
        primary_key=("trip_id",),
    ),
    _t(
        "gold",
        "outcomes",
        "Desfecho futuro simulado, usado como rótulo de churn. Nunca vira feature.",
        "pipeline.extended.generate",
        [
            Col("customer_id", "string", "Cliente (chave estrangeira de customers)."),
            Col("outcome_start", "date", "Início da janela de desfecho."),
            Col("outcome_end", "date", "Fim da janela de desfecho."),
            Col("future_trip_dates", "list_date", "Datas das viagens simuladas na janela."),
            Col("future_trip_count", "int64", "Quantidade de viagens na janela de desfecho."),
            Col("churn", "bool", "Verdadeiro se não houve viagem na janela (rótulo sintético)."),
            Col("is_synthetic", "bool", "Verdadeiro: dado sintético."),
        ],
        primary_key=("customer_id",),
    ),
    _t(
        "gold",
        "scores",
        "Resultado da análise por cliente: valor, risco, prioridade e persona.",
        "cli sync-scores",
        [
            Col("customer_id", "string", "Cliente (chave estrangeira de customers)."),
            Col("value_score", "float64", "Score de valor de 0 a 100."),
            Col(
                "churn_risk", "float64", "Risco de evasão de 0 a 1; o método está em model_version."
            ),
            Col("priority_score", "float64", "Valor x risco; ordena a fila de retenção."),
            Col("estimated_value_at_risk", "float64", "Gasto observado x risco; proxy, não CLV."),
            Col("segment", "string", "Persona do cliente (ou segmento por regras)."),
            Col("drivers", "list_string", "Fatores que explicam o resultado, em texto."),
            Col("model_version", "string", "Versões do valor, do risco e do segmentador."),
            Col("evaluated_at", "date", "Data de corte da avaliação."),
        ],
        primary_key=("customer_id",),
    ),
    _t(
        "gold",
        "personas",
        "Perfil médio de cada persona, formada por clustering sobre comportamento.",
        "artifacts/personas.json (azul-crm personas)",
        [
            Col("method", "string", "Método de segmentação."),
            Col("cluster", "int64", "Número do grupo no treino."),
            Col("name", "string", "Nome da persona."),
            Col("description", "string", "Descrição gerada a partir do comportamento do grupo."),
            Col("size", "int64", "Clientes no grupo."),
            Col("share", "float64", "Fração da base."),
            Col("spend", "float64", "Gasto médio (BRL)."),
            Col("frequency", "float64", "Viagens médias."),
            Col("recency_days", "float64", "Dias médios sem voar."),
            Col(
                "incident_rate", "float64", "Fração média de viagens com atraso de 60 min ou mais."
            ),
            Col("high_value", "bool", "Grupo acima da média em valor.", nullable=True),
            Col("cooling", "bool", "Grupo há bastante tempo sem voar.", nullable=True),
            Col("delays", "bool", "Grupo com atrasos frequentes.", nullable=True),
        ],
        primary_key=("name",),
    ),
    _t(
        "gold",
        "bias_audit_groups",
        "Resultado da auditoria de viés por atributo e grupo.",
        "artifacts/bias_report.json (azul-crm bias-audit)",
        [
            Col("attribute", "string", "Atributo auditado."),
            Col("verdict", "string", "ok, atencao, alerta, confundido ou amostra_insuficiente."),
            Col("group", "string", "Grupo dentro do atributo."),
            Col("customers", "int64", "Clientes no grupo."),
            Col("selection_rate", "float64", "Fração do grupo entre os mais prioritários."),
            Col("recall_among_churners", "float64", "Entre quem saiu, fração selecionada.", True),
            Col("mean_predicted_risk", "float64", "Risco previsto médio."),
            Col("observed_churn", "float64", "Churn observado (simulado)."),
            Col("calibration_gap", "float64", "Risco previsto menos churn observado."),
        ],
        primary_key=("attribute", "group"),
    ),
    _t(
        "gold",
        "manifest",
        "Linhagem da execução: de onde vieram os dados, com que janela e semente.",
        "pipeline.extended.generate",
        [
            Col("schema_version", "string", "Versão do contrato da Gold."),
            Col("mode", "string", "demo_fixture ou synthetic_public_fares."),
            Col("seed", "int64", "Semente que reproduz a geração."),
            Col("observation_start", "date", "Início da janela de observação."),
            Col("observation_end", "date", "Fim da janela de observação."),
            Col("customer_count", "int64", "Clientes na carteira."),
            Col("trip_count", "int64", "Viagens na carteira."),
            Col(
                "calibrated_with_public_data", "bool", "Verdadeiro se tarifas públicas calibraram."
            ),
            Col(
                "calibration_scope",
                "string",
                "O que foi calibrado (none ou route_mean_fares_and_route_demand).",
            ),
            Col("churn_label_status", "string", "Origem do rótulo de churn."),
            Col("notes", "string", "Observações e limitações da geração."),
            Col("storage", "string", "Persistência usada: sqlite ou snowflake."),
        ],
    ),
    _t(
        "gold",
        "decisions",
        "Decisões humanas sobre recomendações (aprovar ou rejeitar). Nada é enviado.",
        "api /decisions",
        [
            Col("id", "string", "Identificador da decisão."),
            Col("customer_id", "string", "Cliente da recomendação."),
            Col("status", "string", "APPROVED ou REJECTED."),
            Col("note", "string", "Observação do revisor."),
            Col("recommendation", "json", "Recomendação revisada, como JSON."),
            Col("created_at", "timestamp", "Momento da decisão (UTC)."),
            Col("sent", "bool", "Sempre falso: o MVP não envia mensagens."),
        ],
        primary_key=("id",),
    ),
)
BY_NAME = {t.qualified: t for t in TABLES}
STORE_TABLES = {
    t.qualified: t.name for t in TABLES if not t.origin.startswith(("artifacts", "derivada"))
}


# ----------------------------------------------------------------------------- conversão


def _convert(dtype, value):
    if dtype == "string":
        return str(value)
    if dtype == "int64":
        if isinstance(value, bool):
            raise ValueError("booleano não é inteiro")
        return int(value)
    if dtype == "float64":
        return float(value)
    if dtype == "bool":
        if isinstance(value, bool):
            return value
        if str(value).lower() in {"true", "false"}:
            return str(value).lower() == "true"
        raise ValueError("não é booleano")
    if dtype == "date":
        return value if isinstance(value, date) else date.fromisoformat(str(value))
    if dtype == "timestamp":
        stamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        if stamp.tzinfo is None:
            raise ValueError("data e hora sem fuso")
        return stamp.astimezone(timezone.utc)
    if dtype == "list_string":
        return [str(v) for v in value]
    if dtype == "list_date":
        return [v if isinstance(v, date) else date.fromisoformat(str(v)) for v in value]
    if dtype == "json":
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    raise ValueError(f"tipo desconhecido: {dtype}")


def convert_rows(table: Table, records: list[dict], start: int = 1) -> list[list]:
    """Valida os registros contra o esquema e devolve linhas na ordem das colunas."""
    expected = {c.key for c in table.columns} | set(table.ignore_keys)
    rows = []
    for number, record in enumerate(records, start=start):
        extra = set(record) - expected
        if extra and table.strict:
            raise ValueError(
                f"{table.qualified}: colunas fora do esquema {sorted(extra)} (registro {number})"
            )
        row = []
        for col in table.columns:
            value = record.get(col.key)
            if value is None or (value == "" and col.dtype != "string"):
                if not col.nullable:
                    raise ValueError(f"{table.qualified}.{col.name}: valor obrigatório ausente")
                row.append(None)
                continue
            try:
                row.append(_convert(col.dtype, value))
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"{table.qualified}.{col.name}: valor inválido {value!r} ({exc})"
                ) from exc
        rows.append(row)
    return rows


def arrow_schema(table: Table) -> pa.Schema:
    return pa.schema(
        [
            pa.field(
                c.name,
                ARROW_TYPES[c.dtype],
                nullable=c.nullable,
                metadata={"description": c.description},
            )
            for c in table.columns
        ],
        metadata={"description": table.description},
    )


# ----------------------------------------------------------------------------- origens


def _derived_transactions(loyalty_records):
    return [t for record in loyalty_records for t in record.get("transactions", [])]


def _personas_records(root: Path):
    path = root / "artifacts" / "personas.json"
    if not path.exists():
        return []
    artifact = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for p in artifact["personas"]:
        traits = p.get("traits") or {}
        records.append(
            {
                "method": artifact["method"],
                "cluster": p["cluster"],
                "name": p["name"],
                "description": p["description"],
                "size": p["size"],
                "share": p["share"],
                **p["profile"],
                **traits,
            }
        )
    return records


def _bias_records(root: Path):
    path = root / "artifacts" / "bias_report.json"
    if not path.exists():
        return []
    report = json.loads(path.read_text(encoding="utf-8"))
    return [
        {
            "attribute": key,
            "verdict": attribute["verdict"],
            **{
                k: g[k]
                for k in (
                    "group",
                    "customers",
                    "selection_rate",
                    "recall_among_churners",
                    "mean_predicted_risk",
                    "observed_churn",
                    "calibration_gap",
                )
            },
        }
        for key, attribute in report["attributes"].items()
        for g in attribute["groups"]
    ]


def _batches(qualified: str, root: Path, store, size: int):
    """Lotes de registros de uma tabela do lake, do store ou dos artefatos."""
    if qualified == "gold.loyalty_transactions":
        for batch in store.iter_batches("loyalty", size):
            rows = _derived_transactions(batch)
            if rows:
                yield rows
    elif qualified == "gold.personas":
        rows = _personas_records(root)
        if rows:
            yield rows
    elif qualified == "gold.bias_audit_groups":
        rows = _bias_records(root)
        if rows:
            yield rows
    else:
        yield from store.iter_batches(STORE_TABLES[qualified], size)


# ----------------------------------------------------------------------------- saídas


def snowflake_ddl() -> str:
    lines = [
        "-- Gerado por `azul-crm export-lake`. NÃO TESTADO em conta Snowflake: revisar antes de rodar.",
        "-- Tabelas tipadas da camada analítica, em schemas LAKE_* para não colidir com as tabelas",
        "-- JSON (id, payload VARIANT) que o adaptador atual do app usa em BRONZE/SILVER/GOLD.",
        "USE ROLE SYSADMIN;",
        "CREATE DATABASE IF NOT EXISTS AZUL_CRM;",
    ]
    for layer in LAYERS:
        lines.append(f"CREATE SCHEMA IF NOT EXISTS AZUL_CRM.LAKE_{layer.upper()};")
    lines.append("")
    for t in TABLES:
        target = f"AZUL_CRM.LAKE_{t.layer.upper()}.{t.name.upper()}"
        columns = [
            f"  {c.name.upper()} {SNOWFLAKE_TYPES[c.dtype]}{'' if c.nullable else ' NOT NULL'}"
            f" COMMENT '{c.description.replace(chr(39), chr(39) * 2)}'"
            for c in t.columns
        ]
        if t.primary_key:
            keys = ", ".join(k.upper() for k in t.primary_key)
            columns.append(f"  PRIMARY KEY ({keys})  -- informativa: tabelas padrão não impõem")
        lines.append(f"-- {t.description}")
        lines.append(f"CREATE TABLE IF NOT EXISTS {target} (")
        lines.append(",\n".join(columns))
        lines.append(");")
        lines.append("")
    lines += [
        "-- Carga a partir dos Parquet (exemplo; ajuste stage e caminho):",
        "-- CREATE STAGE IF NOT EXISTS AZUL_CRM.LAKE_GOLD.CRM_STAGE;",
        "-- PUT file://data/lake/gold/customers.parquet @AZUL_CRM.LAKE_GOLD.CRM_STAGE/gold/;",
        "-- COPY INTO AZUL_CRM.LAKE_GOLD.CUSTOMERS FROM @AZUL_CRM.LAKE_GOLD.CRM_STAGE/gold/customers.parquet",
        "--   FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;",
    ]
    return "\n".join(lines) + "\n"


def dictionary_markdown(dictionary: dict) -> str:
    snapshot = dictionary["snapshot"]
    out = [
        "# Dicionário de dados do lake",
        "",
        "Gerado por `python -m azul_crm.cli export-lake`. "
        + (
            "**Clientes sintéticos**, sem informação real de clientes; as tabelas silver podem "
            "conter dados públicos reais (ANAC)."
            if dictionary["customers_are_synthetic"]
            else "**Atenção: há clientes não sintéticos.** Aplicar LGPD antes de compartilhar."
        ),
        "",
        f"Janela de observação: {snapshot.get('observation_start')} a "
        f"{snapshot.get('observation_end')} · clientes: {snapshot.get('customer_count')} · "
        f"seed: {snapshot.get('seed')} · calibrado com dados públicos: "
        f"{snapshot.get('calibrated_with_public_data')}.",
        "",
        "Para usar dados reais, alimente as mesmas tabelas com as mesmas colunas e tipos. "
        "O exportador recusa coluna extra, coluna ausente e valor inválido.",
        "",
    ]
    for layer in LAYERS:
        out += [f"## Camada {layer}", ""]
        for key, table in dictionary["tables"].items():
            if table["layer"] != layer:
                continue
            state = f"{table['rows']} linhas" if table["exported"] else "sem dados nesta execução"
            keys = ", ".join(table["primary_key"]) or "sem chave natural"
            out += [
                f"### {key}",
                "",
                f"{table['description']}",
                "",
                f"Origem: {table['origin']} · chave: {keys} · {state}",
                "",
                "| Coluna | Tipo | Nulo | Descrição |",
                "|---|---|---|---|",
            ]
            out += [
                f"| {c['name']} | {c['type']} | {'sim' if c['nullable'] else 'não'} | "
                f"{c['description']} |"
                for c in table["columns"]
            ]
            out.append("")
    return "\n".join(out)


def export_lake(root: Path, store, out: Path | None = None, batch_size: int | None = None) -> dict:
    """Exporta o lake em lotes. Grava numa pasta temporária e só troca os arquivos no fim:
    se qualquer tabela falhar, a saída anterior fica intacta e nada novo é criado."""
    size = batch_size or BATCH_SIZE
    out = Path(out) if out else root / "data" / "lake"
    out.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".lake-", dir=out.parent))
    manifest = (store.read("manifest") or [{}])[0]
    entries, customers_synthetic = {}, True
    try:
        for table in TABLES:
            path = work / table.layer / f"{table.name}.parquet"
            schema, writer = arrow_schema(table), None
            digest, total, number = hashlib.sha256(), 0, 1
            flag = (
                [c.name for c in table.columns].index("is_synthetic")
                if (table.qualified == "gold.customers")
                else None
            )
            try:
                for records in _batches(table.qualified, root, store, size):
                    rows = convert_rows(table, records, start=number)
                    number += len(records)
                    if not rows:
                        continue
                    if writer is None:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        writer = pq.ParquetWriter(path, schema, compression="snappy")
                    arrays = [
                        pa.array(list(values), type=ARROW_TYPES[c.dtype])
                        for c, values in zip(table.columns, zip(*rows))
                    ]
                    writer.write_table(pa.Table.from_arrays(arrays, schema=schema))
                    for row in rows:  # hash por linha: não depende do tamanho do lote
                        digest.update(json.dumps(row, default=str, ensure_ascii=False).encode())
                        digest.update(b"\n")
                    total += len(rows)
                    if flag is not None:
                        customers_synthetic &= all(row[flag] for row in rows)
            finally:
                if writer is not None:
                    writer.close()
            entries[table.qualified] = {
                "layer": table.layer,
                "name": table.name,
                "description": table.description,
                "origin": table.origin,
                "primary_key": list(table.primary_key),
                "path": f"{table.layer}/{table.name}.parquet",
                "exported": total > 0,
                "rows": total,
                "content_sha256": digest.hexdigest() if total else None,
                "columns": [
                    {
                        "name": c.name,
                        "type": c.dtype,
                        "nullable": c.nullable,
                        "description": c.description,
                        "snowflake_type": SNOWFLAKE_TYPES[c.dtype],
                    }
                    for c in table.columns
                ],
            }
        # Tudo validado e gravado: agora sim troca os arquivos de uma vez.
        out.mkdir(parents=True, exist_ok=True)
        for table in TABLES:
            source = work / table.layer / f"{table.name}.parquet"
            target = out / table.layer / f"{table.name}.parquet"
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(source, target)
            elif target.exists():
                target.unlink()  # sobra de uma execução anterior com dados
        dictionary = {
            "generated_by": "azul-crm export-lake",
            "customers_are_synthetic": customers_synthetic,
            "snapshot": {
                k: manifest.get(k)
                for k in (
                    "seed",
                    "observation_start",
                    "observation_end",
                    "customer_count",
                    "trip_count",
                    "mode",
                    "calibrated_with_public_data",
                )
            },
            "layers": {
                layer: [e["name"] for e in entries.values() if e["layer"] == layer]
                for layer in LAYERS
            },
            "tables": entries,
        }
        (out / "data_dictionary.json").write_text(
            json.dumps(dictionary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (out / "DATA_DICTIONARY.md").write_text(dictionary_markdown(dictionary), encoding="utf-8")
        (out / "snowflake_typed.sql").write_text(snowflake_ddl(), encoding="utf-8")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    exported = {k: v["rows"] for k, v in entries.items() if v["exported"]}
    return {
        "out": str(out),
        "tables_exported": len(exported),
        "tables_without_data": sorted(k for k, v in entries.items() if not v["exported"]),
        "rows": exported,
    }


def load_dictionary(root: Path) -> dict:
    path = root / "data" / "lake" / "data_dictionary.json"
    if not path.exists():
        return {"available": False}
    return {"available": True, **json.loads(path.read_text(encoding="utf-8"))}
