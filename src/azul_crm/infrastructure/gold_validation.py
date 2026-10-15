"""Validação do contrato Gold v1; não substitui calibração contra dados públicos."""

import csv
import json
from dataclasses import asdict, fields
from datetime import date
from pathlib import Path

from azul_crm.application.features import FeatureBuilder
from azul_crm.domain.models import Customer, Features, Trip
from azul_crm.infrastructure.csv_repository import CsvCustomerRepository


def validate_gold(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["schema_version"] != "1.0" or manifest["mode"] != "demo_fixture":
        raise ValueError("Contrato aceita apenas Gold 1.0 demo_fixture")
    if manifest["calibrated_with_public_data"] is not False:
        raise ValueError("Fixture não pode declarar calibração pública")
    start = date.fromisoformat(manifest["observation_start"])
    end = date.fromisoformat(manifest["observation_end"])
    if start > end:
        raise ValueError("Janela inválida")
    tables = {}
    for name, model in (("customers", Customer), ("trips", Trip), ("features", Features)):
        with (directory / f"{name}.csv").open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames != [field.name for field in fields(model)]:
                raise ValueError(f"Colunas divergentes em {name}")
            tables[name] = list(reader)
        if not tables[name] or any(
            None in row or any(v in (None, "") for v in row.values()) for row in tables[name]
        ):
            raise ValueError(f"Tabela vazia ou campos ausentes em {name}")
    if any(row["is_synthetic"].lower() != "true" for row in tables["customers"]):
        raise ValueError("Demo exige clientes sintéticos")
    repo = CsvCustomerRepository(directory)
    customers = repo.list_customers()
    feature_rows = {row["customer_id"]: row for row in tables["features"]}
    if len(feature_rows) != len(tables["features"]) or set(feature_rows) != {
        c.customer_id for c in customers
    }:
        raise ValueError("Features devem cobrir cada cliente exatamente uma vez")
    if manifest["customer_count"] != len(customers) or manifest["trip_count"] != len(
        tables["trips"]
    ):
        raise ValueError("Contagens divergentes do manifesto")
    for customer in customers:
        trips = repo.trips_for(customer.customer_id)
        if any(not start <= t.flight_date <= end for t in trips):
            raise ValueError("Viagem fora da observação; desfechos devem ficar separados")
        expected = asdict(FeatureBuilder().build(customer.customer_id, trips, start, end))
        row = feature_rows[customer.customer_id]
        for key, value in expected.items():
            if isinstance(value, (int, float)):
                actual = int(row[key]) if isinstance(value, int) else float(row[key])
                if actual != value:
                    raise ValueError(f"Feature inconsistente: {customer.customer_id}.{key}")
            elif str(value) != row[key]:
                raise ValueError(f"Feature inconsistente: {customer.customer_id}.{key}")
    return {
        "status": "valid",
        "schema_version": "1.0",
        "customers": len(customers),
        "trips": len(tables["trips"]),
        "features": len(feature_rows),
    }
