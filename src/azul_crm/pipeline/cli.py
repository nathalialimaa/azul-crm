import argparse
import json

from azul_crm.infrastructure.gold_validation import validate_gold
from azul_crm.infrastructure.settings import Settings
from azul_crm.pipeline.stages import (
    DemoSyntheticGenerator,
    FixtureIngestor,
    GoldPublisher,
    RouteCleaner,
)


def main():
    parser = argparse.ArgumentParser(description="Pipeline de integração com fixtures fictícias")
    parser.add_argument("command", choices=["demo", "validate"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--customers", type=int, default=40)
    args = parser.parse_args()
    if not 4 <= args.customers <= 10000:
        parser.error("--customers deve estar entre 4 e 10000")
    settings = Settings.load()
    root = settings.root
    if args.command == "validate":
        print(json.dumps(validate_gold(settings.gold_directory), indent=2))
        return
    bronze = FixtureIngestor().ingest(root / "data/fixtures/routes.csv", root / "data/bronze")
    routes = RouteCleaner().clean(bronze, root / "data/silver")
    windows = settings.windows()
    start, end = windows["observation_start"], windows["observation_end"]
    customers, trips = DemoSyntheticGenerator().generate(
        routes, args.customers, args.seed, start, end
    )
    GoldPublisher().publish(root / "data/gold", customers, trips, args.seed, start, end)
    validate_gold(settings.gold_directory)
    print(f"Gold de DEMONSTRAÇÃO gerada: {len(customers)} clientes, {len(trips)} viagens.")
    print("Não calibrada pela ANAC. Reinicie a API após regenerar os arquivos.")


if __name__ == "__main__":
    main()
