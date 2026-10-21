"""Comandos operacionais v2; v1 azul-pipeline continua disponível."""

import argparse
import json
import logging
from pathlib import Path

from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Azul CRM integrado")
    parser.add_argument(
        "command",
        choices=[
            "demo",
            "train",
            "index",
            "check",
            "validate",
            "airports",
            "fares",
            "sync-scores",
            "vra",
            "document",
        ],
    )
    parser.add_argument("--customers", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--public", action="store_true", help="Calibrar tarifas com Silver pública já importada"
    )
    parser.add_argument("--file", type=Path)
    parser.add_argument("--url", help="URL HTTPS oficial do CSV ou ZIP")
    parser.add_argument("--period", help="Mês de venda YYYY-MM")
    parser.add_argument("--max-mb", type=int, default=50)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--document-id")
    parser.add_argument("--title")
    parser.add_argument("--demo-doc", action="store_true")
    args = parser.parse_args()
    settings = Settings.load()
    store = Store(settings.root)
    if args.command == "document":
        from azul_crm.pipeline.documents import import_document

        if not args.file:
            parser.error("document exige --file")
        result = import_document(
            args.file, settings.root, args.document_id, args.title, args.url, args.demo_doc
        )
    elif args.command == "demo":
        from azul_crm.pipeline.extended import generate

        result = generate(settings, args.customers, args.seed, args.public)
    elif args.command == "train":
        from azul_crm.pipeline.modeling import train

        result = train(settings.root, store, args.seed)
    elif args.command == "index":
        from azul_crm.infrastructure.rag import DocumentIndex

        result = DocumentIndex(settings.root).build()
    elif args.command == "check":
        result = store.ping()
    elif args.command in {"airports", "fares", "vra"}:
        from azul_crm.pipeline.public_data import (
            AIRPORT_URL,
            download,
            import_airports,
            ingest_fares,
        )

        path = args.file
        url = args.url or (AIRPORT_URL if args.command == "airports" else None)
        if path is None and not url and args.command == "fares":
            from azul_crm.pipeline.public_data import discover_fares_url

            url = discover_fares_url(args.period)
        if path is None:
            if not url:
                parser.error(
                    "Informe --url do arquivo oficial ou --file; URL mensal não é inventada"
                )
            if args.command in {"fares", "vra"}:
                from urllib.parse import urlparse

                host = urlparse(url).hostname or ""
                if not (host == "anac.gov.br" or host.endswith(".anac.gov.br")):
                    parser.error("Download ANAC exige domínio oficial anac.gov.br")
            path, _ = download(url, settings.root / "data/downloads", args.max_mb, args.refresh)
        if args.command == "vra":
            from azul_crm.pipeline.public_data import ingest_vra

            result = ingest_vra(path, settings.root, args.period, url or "official_local_file")
            print(json.dumps(result, indent=2))
            return
        result = (
            import_airports(path, store)
            if args.command == "airports"
            else ingest_fares(path, settings.root, args.period, url or "official_local_file")
        )
    elif args.command == "validate":
        from azul_crm.infrastructure.validation import validate_store

        result = validate_store(store)
    else:
        from dataclasses import asdict

        from azul_crm.bootstrap import build_container

        c = build_container(settings)
        rows = c.crm.priorities()
        store.publish({"scores": [(r.customer_id, asdict(r)) for r in rows]})
        result = {"scores": len(rows)}
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
