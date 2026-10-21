from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = ROOT / "figures"


@dataclass(frozen=True)
class StudyConfig:
    raw: dict[str, Any]
    root: Path = ROOT

    @property
    def seed(self) -> int:
        env = os.environ.get("TFV_SEED")
        return int(env) if env else int(self.raw["project"]["seed"])

    @property
    def timeframes(self) -> list[str]:
        return list(self.raw["timeframes"])

    @property
    def timeframe_minutes(self) -> dict[str, int]:
        return {k: int(v) for k, v in self.raw["timeframe_minutes"].items()}

    @property
    def crypto_symbols(self) -> list[str]:
        return list(self.raw["data"]["binance"]["symbols"])

    @property
    def equity_symbols(self) -> list[str]:
        return list(self.raw["data"]["equities"]["symbols"])

    @property
    def cache_dir(self) -> Path:
        p = self.root / self.raw["data"]["cache_dir"]
        p.mkdir(parents=True, exist_ok=True)
        return p


def load_config(path: str | Path | None = None) -> StudyConfig:
    path = Path(path) if path else CONFIG_DIR / "study.yaml"
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    return StudyConfig(raw=raw)
