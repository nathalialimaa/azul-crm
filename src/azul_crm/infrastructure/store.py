"""Persistência de snapshots canônicos. CSV é intercâmbio, nunca banco da UI v2."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date

from azul_crm.domain.models import Customer, Trip

TABLES = {
    "sources": "BRONZE.SOURCES",
    "raw_rows": "BRONZE.RAW_ROWS",
    "airports": "SILVER.AIRPORTS",
    "fares": "SILVER.FARES",
    "operations": "SILVER.OPERATIONS",
    "demand": "SILVER.DEMAND",
    "customers": "GOLD.CUSTOMERS",
    "trips": "GOLD.TRIPS",
    "features": "GOLD.FEATURES",
    "loyalty": "GOLD.LOYALTY",
    "outcomes": "GOLD.OUTCOMES",
    "scores": "GOLD.SCORES",
    "manifest": "GOLD.MANIFEST",
    "decisions": "GOLD.DECISIONS",
}


def dumps(value):
    return json.dumps(value, default=str, ensure_ascii=False, allow_nan=False)


class Store:
    def __init__(self, root, backend=None):
        self.root = root
        self.backend = backend or os.getenv("CRM_STORAGE", "sqlite")
        if self.backend not in {"sqlite", "snowflake"}:
            raise ValueError("CRM_STORAGE deve ser sqlite ou snowflake")
        self.path = root / "data" / "crm.sqlite3"
        if self.backend == "sqlite":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.connection() as con:
                for table in TABLES:
                    con.execute(
                        f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
                    )

    @contextmanager
    def connection(self):
        if self.backend == "sqlite":
            con = sqlite3.connect(self.path, timeout=30)
        else:
            import snowflake.connector

            required = ["ACCOUNT", "USER", "ROLE", "DATABASE", "WAREHOUSE"]
            missing = [k for k in required if not os.getenv("SNOWFLAKE_" + k)]
            if missing:
                raise ValueError("Configuração Snowflake ausente: " + ", ".join(missing))
            args = {k.lower(): os.environ["SNOWFLAKE_" + k] for k in required}
            args["authenticator"] = os.getenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser")
            if os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"):
                args["private_key_file"] = os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"]
                args["authenticator"] = "SNOWFLAKE_JWT"
                if os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"):
                    args["private_key_file_pwd"] = os.environ["SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"]
            args.update(
                login_timeout=30,
                network_timeout=60,
                session_parameters={
                    "QUERY_TAG": "azul_crm_mvp",
                    "STATEMENT_TIMEOUT_IN_SECONDS": 60,
                },
            )
            con = snowflake.connector.connect(**args)
        try:
            yield con
        finally:
            con.close()

    def table(self, name):
        if name not in TABLES:
            raise ValueError("Tabela não permitida")
        return name if self.backend == "sqlite" else TABLES[name]

    def read(self, name):
        with self.connection() as con:
            cur = con.cursor()
            try:
                cur.execute(f"SELECT payload FROM {self.table(name)} ORDER BY id")
                return [json.loads(r[0]) if isinstance(r[0], str) else r[0] for r in cur.fetchall()]
            finally:
                cur.close()

    def iter_batches(self, name, batch_size=20000):
        """Lê a tabela em lotes, na mesma ordem de ``read``, sem carregar tudo na memória."""
        with self.connection() as con:
            cur = con.cursor()
            try:
                cur.execute(f"SELECT payload FROM {self.table(name)} ORDER BY id")
                while True:
                    chunk = cur.fetchmany(batch_size)
                    if not chunk:
                        break
                    yield [json.loads(r[0]) if isinstance(r[0], str) else r[0] for r in chunk]
            finally:
                cur.close()

    def publish(self, tables, replace=True):
        """Uma transação para o snapshot inteiro; use apenas um escritor por vez."""
        for name, rows in tables.items():
            self.table(name)
            ids = [str(r[0]) for r in rows]
            if len(ids) != len(set(ids)):
                raise ValueError("IDs duplicados em " + name)
            for _, payload in rows:
                dumps(payload)
        with self.connection() as con:
            cur = con.cursor()
            try:
                cur.execute("BEGIN")
                for name, rows in tables.items():
                    table = self.table(name)
                    if replace is True or (isinstance(replace, set) and name in replace):
                        cur.execute(f"DELETE FROM {table}")
                    if self.backend == "sqlite":
                        cur.executemany(
                            f"INSERT OR REPLACE INTO {table} (id,payload) VALUES (?,?)",
                            [(str(key), dumps(payload)) for key, payload in rows],
                        )
                    else:
                        # Lotes pequenos reduzem round trips e consumo do warehouse.
                        for offset in range(0, len(rows), 500):
                            batch = rows[offset : offset + 500]
                            placeholders = ",".join(["(%s,%s)"] * len(batch))
                            parameters = tuple(
                                value
                                for key, payload in batch
                                for value in (str(key), dumps(payload))
                            )
                            cur.execute(
                                f"""MERGE INTO {table} t USING
                                (SELECT column1 AS id, PARSE_JSON(column2) AS payload
                                 FROM VALUES {placeholders}) s ON t.id=s.id
                                WHEN MATCHED THEN UPDATE SET payload=s.payload
                                WHEN NOT MATCHED THEN INSERT (id,payload) VALUES (s.id,s.payload)""",
                                parameters,
                            )
                con.commit()
            except Exception:
                con.rollback()
                raise
            finally:
                cur.close()

    def ping(self):
        with self.connection() as con:
            cur = con.cursor()
            try:
                cur.execute("SELECT 1")
                return {"backend": self.backend, "connected": cur.fetchone()[0] == 1}
            finally:
                cur.close()


class StoredCustomerRepository:
    """Snapshot de leitura evita N+1 no warehouse. Reinicie após publicar nova Gold."""

    def __init__(self, store):
        self._customers = {r["customer_id"]: Customer(**r) for r in store.read("customers")}
        self._trips = {}
        for row in store.read("trips"):
            row["flight_date"] = date.fromisoformat(row["flight_date"])
            trip = Trip(**row)
            if trip.customer_id not in self._customers:
                raise ValueError("Viagem órfã")
            self._trips.setdefault(trip.customer_id, []).append(trip)

    def list_customers(self):
        return list(self._customers.values())

    def get_customer(self, customer_id):
        return self._customers.get(customer_id)

    def trips_for(self, customer_id):
        return self._trips.get(customer_id, [])
