"""Atomic MIC JSON write helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nt.match_intel.schema import mic_match_key


def mic_path(out_dir: Path | str, match: str, *, match_key: str | None = None) -> Path:
    """outbox/match_intel/{match_key}.json"""
    key = match_key or mic_match_key(match)
    return Path(out_dir) / f"{key}.json"


def atomic_write_json(path: Path | str, obj: dict[str, Any] | list[Any]) -> Path:
    """
    Write JSON atomically: temp → rename.

    Creates parent dirs. Always UTF-8 with trailing newline.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path


def write_mic(
    card: dict[str, Any],
    out_dir: Path | str,
    *,
    match_key: str | None = None,
) -> Path:
    """Atomic write of a MIC card to out_dir/{match_key}.json."""
    key = match_key or str(card.get("match_key") or mic_match_key(str(card.get("match") or "")))
    path = Path(out_dir) / f"{key}.json"
    return atomic_write_json(path, card)


def read_mic(path: Path | str) -> dict[str, Any] | None:
    """Load MIC JSON or None if missing/invalid."""
    p = Path(path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None
