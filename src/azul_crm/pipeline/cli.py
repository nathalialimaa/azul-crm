import argparse
from datetime import date

from azul_crm.infrastructure.settings import Settings
from azul_crm.pipeline.stages import (
    DemoSyntheticGenerator,
    FixtureIngestor,
    GoldPublisher,
    RouteCleaner,
)


def main():
    parser = argparse.ArgumentParser(description="Pipeline de integração com fixtures fictícias")
    parser.add_argument("command", choices=["demo"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--customers", type=int, default=40)
    args = parser.parse_args()
    if not 4 <= args.customers <= 10000:
        parser.error("--customers deve estar entre 4 e 10000")
    root = Settings.load().root
    bronze = FixtureIngestor().ingest(root / "data/fixtures/routes.csv", root / "data/bronze")
    routes = RouteCleaner().clean(bronze, root / "data/silver")
    start, end = date(2025, 10, 1), date(2026, 9, 30)
    customers, trips = DemoSyntheticGenerator().generate(
        routes, args.customers, args.seed, start, end
    )
    GoldPublisher().publish(root / "data/gold", customers, trips, args.seed, start, end)
    print(f"Gold de DEMONSTRAÇÃO gerada: {len(customers)} clientes, {len(trips)} viagens.")
    print("Não calibrada pela ANAC. Reinicie a API após regenerar os arquivos.")


if __name__ == "__main__":
    main()
