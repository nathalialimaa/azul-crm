"""Pipeline local de fixtures, sem download nem alegação de calibração pública."""

import csv
import hashlib
import json
import random
import shutil
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from azul_crm.application.features import FeatureBuilder
from azul_crm.domain.models import Customer, Trip


class FixtureIngestor:
    def ingest(self, source: Path, bronze: Path) -> Path:
        bronze.mkdir(parents=True, exist_ok=True)
        target = bronze / "demo_routes.csv"
        shutil.copyfile(source, target)
        metadata = {
            "source": str(source.name),
            "is_demo": True,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
        (bronze / "source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return target


class RouteCleaner:
    def clean(self, source: Path, silver: Path) -> list[dict]:
        with source.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        routes = []
        seen = set()
        for row in rows:
            origin, destination = row["origin"].strip().upper(), row["destination"].strip().upper()
            fare = float(row["mean_fare"])
            if not (
                len(origin) == len(destination) == 3
                and origin.isalpha()
                and destination.isalpha()
                and origin != destination
                and 0 < fare < float("inf")
            ):
                raise ValueError("Rota/tarifa inválida")
            if (origin, destination) in seen:
                continue
            seen.add((origin, destination))
            routes.append({"origin": origin, "destination": destination, "mean_fare": fare})
        if not routes:
            raise ValueError("Fixture de rotas vazia")
        silver.mkdir(parents=True, exist_ok=True)
        write_csv(silver / "routes.csv", routes)
        return routes


class DemoSyntheticGenerator:
    def generate(
        self, routes: list[dict], count: int, seed: int, start: date, end: date
    ) -> tuple[list[Customer], list[Trip]]:
        rng = random.Random(seed)
        customers, trips = [], []
        days = (end - start).days
        for index in range(count):
            customer_id = f"SYN-{index + 1:04d}"
            route = routes[index % len(routes)]
            customers.append(
                Customer(
                    customer_id, route["origin"], rng.choice(["email", "app"]), "DEMO_UNVERIFIED"
                )
            )
            # Perfis contrastantes ajudam a integrar a UI. Não representam personas treinadas.
            for number in range(rng.randint(18, 32) if index % 2 == 0 else rng.randint(2, 8)):
                maximum_day = max(1, days - 150) if index % 4 == 0 else days
                flight_date = start + timedelta(days=rng.randint(0, maximum_day))
                trips.append(
                    Trip(
                        f"T-{index + 1:04d}-{number + 1:03d}",
                        customer_id,
                        route["origin"],
                        route["destination"],
                        flight_date,
                        round(route["mean_fare"] * rng.uniform(0.7, 1.5), 2),
                        rng.choice([0, 0, 30, 90, 180]),
                    )
                )
        return customers, trips


class GoldPublisher:
    def publish(
        self,
        gold: Path,
        customers: list[Customer],
        trips: list[Trip],
        seed: int,
        start: date,
        end: date,
    ) -> None:
        gold.mkdir(parents=True, exist_ok=True)
        builder = FeatureBuilder()
        features = [builder.build(c.customer_id, trips, start, end) for c in customers]
        write_csv(gold / "customers.csv", [asdict(c) for c in customers])
        write_csv(gold / "trips.csv", [asdict(t) for t in trips])
        write_csv(gold / "features.csv", [asdict(f) for f in features])
        manifest = {
            "schema_version": "1.0",
            "mode": "demo_fixture",
            "seed": seed,
            "observation_start": start.isoformat(),
            "observation_end": end.isoformat(),
            "customer_count": len(customers),
            "trip_count": len(trips),
            "calibrated_with_public_data": False,
            "notes": "Sem treino de ML, rótulos de churn ou regras oficiais de fidelidade.",
        }
        (gold / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Publicação vazia não permitida")
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
