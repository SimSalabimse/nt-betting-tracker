from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def resolve(rel: str | Path) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p
