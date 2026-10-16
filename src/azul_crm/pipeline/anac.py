"""Ingestão Bronze dos microdados de tarifas domésticas da ANAC.

Copia o CSV bruto para a camada Bronze e registra a procedência.
Não altera o conteúdo do arquivo.
"""

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from azul_crm.infrastructure.settings import Settings

# Colunas esperadas no CSV da ANAC, na ordem original.
EXPECTED_COLUMNS = [
    "nr_ano_referencia",
    "nr_mes_referencia",
    "sg_empresa_icao",
    "sg_icao_origem",
    "sg_icao_destino",
    "nr_tarifa",
    "nr_assentos",
]

SOURCE_PAGE = (
    "https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas/"
    "microdados-de-tarifas-aereas-comercializadas"
)


class AnacIngestor:
    """Guarda o arquivo bruto na Bronze junto com um registro de procedência."""

    def ingest(self, source: Path, bronze: Path) -> Path:
        # 1. Confere o arquivo de entrada
        if not source.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {source}")

        header, first_row, row_count = self._read_summary(source)

        if header != EXPECTED_COLUMNS:
            raise ValueError(f"Colunas inesperadas em {source.name}: {header}")

        # 2. Copia o arquivo para a Bronze
        target_dir = bronze / "anac" / "tarifas_domesticas"
        target_dir.mkdir(parents=True, exist_ok=True)

        target = target_dir / source.name
        shutil.copyfile(source, target)

        # 3. Registra de onde o arquivo veio
        year, month = int(first_row[0]), int(first_row[1])
        metadata = {
            "dataset": "anac_tarifas_aereas_domesticas",
            "file_name": source.name,
            "source_page": SOURCE_PAGE,
            "reference_year": year,
            "reference_month": month,
            "rows": row_count,
            "columns": header,
            "size_bytes": source.stat().st_size,
            "sha256": self._sha256(source),
            "ingested_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "is_demo": False,
        }

        metadata_path = target_dir / f"{source.name}.source.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return target

    @staticmethod
    def _read_summary(path: Path) -> tuple[list[str], list[str], int]:
        """Lê o cabeçalho, a primeira linha de dados e conta as linhas."""
        with path.open(encoding="latin-1", newline="") as file:
            header = file.readline().strip().split(";")
            first_row = file.readline().strip().split(";")

            row_count = 1 if first_row != [""] else 0
            row_count += sum(1 for _ in file)

        if row_count == 0:
            raise ValueError("Arquivo sem linhas de dados")

        return header, first_row, row_count

    @staticmethod
    def _sha256(path: Path) -> str:
        """Calcula o hash do arquivo em blocos, sem carregar tudo na memória."""
        digest = hashlib.sha256()

        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="Ingere um CSV de tarifas da ANAC na Bronze",
    )
    parser.add_argument("csv", type=Path, help="Caminho do CSV já extraído do zip")
    args = parser.parse_args()

    root = Settings.load().root
    target = AnacIngestor().ingest(args.csv, root / "data/bronze")

    print(f"Bronze atualizada: {target}")


if __name__ == "__main__":
    main()