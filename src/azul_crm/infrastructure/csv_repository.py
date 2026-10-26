import csv
from datetime import date
from pathlib import Path

from azul_crm.domain.models import Customer, Trip


class CsvCustomerRepository:
    """Carrega um snapshot Gold no startup. Um reinício lê nova publicação."""

    def __init__(self, directory: Path):
        with (directory / "customers.csv").open(encoding="utf-8", newline="") as file:
            customers = [
                Customer(
                    row["customer_id"],
                    row["home_airport"],
                    row["preferred_channel"],
                    row["loyalty_tier"],
                    row["is_synthetic"].lower() == "true",
                )
                for row in csv.DictReader(file)
            ]
        self._customers = {c.customer_id: c for c in customers}
        if len(customers) != len(self._customers):
            raise ValueError("IDs de clientes duplicados")
        with (directory / "trips.csv").open(encoding="utf-8", newline="") as file:
            self._trips = [
                Trip(
                    row["trip_id"],
                    row["customer_id"],
                    row["origin"],
                    row["destination"],
                    date.fromisoformat(row["flight_date"]),
                    float(row["fare_amount"]),
                    int(row["delay_minutes"]),
                )
                for row in csv.DictReader(file)
            ]
        if len({t.trip_id for t in self._trips}) != len(self._trips):
            raise ValueError("IDs de viagens duplicados")
        if any(t.customer_id not in self._customers for t in self._trips):
            raise ValueError("Viagem sem cliente correspondente")

    def list_customers(self) -> list[Customer]:
        return list(self._customers.values())

    def get_customer(self, customer_id: str) -> Customer | None:
        return self._customers.get(customer_id)

    def trips_for(self, customer_id: str) -> list[Trip]:
        return [trip for trip in self._trips if trip.customer_id == customer_id]
