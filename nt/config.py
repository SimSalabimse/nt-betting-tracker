from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nt.paths import ROOT, resolve


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or (ROOT / "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("config.yaml must be a mapping")
    return data


def path_from_config(cfg: dict[str, Any], key: str) -> Path:
    return resolve(cfg["paths"][key])
