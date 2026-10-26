"""Executa o pipeline existente com os arquivos empacotados, sem acessar a rede.

Uso: python scripts/preparar_anac.py
ATENÇÃO: gera novamente a Gold sintética e limpa decisões anteriores, como demo --public.
Feche a aplicação antes de executar. Use uma cópia separada para preservar outra demonstração.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from azul_crm.infrastructure.settings import Settings
from azul_crm.infrastructure.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--customers", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    root = Settings.load().root
    directory = args.data_dir or root / "data/inputs/ANAC"
    if not 100 <= args.customers <= 10000:
        parser.error("--customers deve estar entre 100 e 10000 (treino exige pelo menos 100)")
    if Store(root).backend != "sqlite":
        parser.error("Este preparo de demonstração exige CRM_STORAGE=sqlite")
    expected = {
        "anac_tarifa_setembro2026.zip": "458f3b2e3d330c10517b69edc237b2a0351e0d879c01e006f6414cf361b1a1e4",
        "VRA-agosto_2026.csv": "2414e55a3baf16600462119192af3dcdc2775420942f997bc1b897d75a78392b",
        "airports.csv": "fe7f0d9dc2646e41b0cc520f1733d99b9c76a6b26a3e6a55f66fa89e62083ad5",
    }
    # Verifica TODAS as entradas antes de alterar a base.
    for name, digest in expected.items():
        path = directory / name
        if not path.is_file():
            parser.error(f"Arquivo ausente: {path}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            parser.error(f"Checksum divergente: {name}; use o snapshot fornecido no ZIP")
    commands = [
        ["airports", "--file", str(directory / "airports.csv")],
        ["fares", "--file", str(directory / "anac_tarifa_setembro2026.zip"), "--period", "2026-09"],
        ["vra", "--file", str(directory / "VRA-agosto_2026.csv"), "--period", "2026-08"],
        ["demo", "--public", "--customers", str(args.customers), "--seed", str(args.seed)],
        ["train", "--seed", str(args.seed)],
        ["personas", "--seed", str(args.seed)],
        ["sync-scores"], ["bias-audit"], ["clv-report"], ["validate"], ["index"], ["export-lake"],
    ]
    for command in commands:
        print("ETAPA: " + " ".join(command), flush=True)
        subprocess.run([sys.executable, "-m", "azul_crm.cli", *command], cwd=root, check=True)
    print(json.dumps({"status": "ok", "next": "python -m streamlit run streamlit_app.py"}))


if __name__ == "__main__":
    main()
