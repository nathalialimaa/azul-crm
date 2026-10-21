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
        from dotenv import load_dotenv

        root = Path(os.environ.get("CRM_PROJECT_ROOT", default_root)).resolve()
        load_dotenv(root / ".env", override=False)
        return cls(root)

    @property
    def gold_directory(self) -> Path:
        return self.root / "data" / "gold"

    def scoring_policy(self) -> ScoringPolicy:
        with (self.root / "config" / "settings.toml").open("rb") as file:
            return ScoringPolicy(**tomllib.load(file)["scoring"])

    def windows(self) -> dict:
        from datetime import date, timedelta

        with (self.root / "config" / "settings.toml").open("rb") as file:
            windows = tomllib.load(file)["windows"]
        if set(windows) != {"observation_start", "observation_end", "outcome_start", "outcome_end"}:
            raise ValueError("Configuração de janelas incompleta")
        if not all(type(value) is date for value in windows.values()):
            raise ValueError("Janelas devem usar datas TOML sem aspas")
        if not (
            windows["observation_start"]
            <= windows["observation_end"]
            < windows["outcome_start"]
            <= windows["outcome_end"]
        ):
            raise ValueError("Janelas invertidas ou sobrepostas")
        if windows["outcome_start"] != windows["observation_end"] + timedelta(days=1):
            raise ValueError("Desfecho deve começar no dia seguinte ao corte")
        return windows
