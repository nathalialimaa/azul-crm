import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from azul_crm.domain.scoring import ScoringPolicy


@dataclass(frozen=True)
class Settings:
    root: Path

    @classmethod
    def load(cls):
        default_root = Path(__file__).resolve().parents[3]
        return cls(Path(os.environ.get("CRM_PROJECT_ROOT", default_root)).resolve())

    @property
    def gold_directory(self) -> Path:
        return self.root / "data" / "gold"

    def scoring_policy(self) -> ScoringPolicy:
        with (self.root / "config" / "settings.toml").open("rb") as file:
            return ScoringPolicy(**tomllib.load(file)["scoring"])
