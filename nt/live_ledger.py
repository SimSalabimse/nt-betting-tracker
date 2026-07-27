"""
Live-ledger isolation helpers.

Diversify / similar-recent / Settlement Lessons must never consume
history/archives/* or history/rounds/* rows. Only live data/bets.csv
rows with source != era_archive count as live memory.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ARCHIVE_PATH_MARKERS: tuple[str, ...] = ("history/archives", "history/rounds")


def filter_live_rows(
    rows: Sequence[Mapping[str, Any]] | Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """
    Drop era_archive (and non-mapping) rows. Keep live ledger memory only.

    Rows without a ``source`` field are treated as live (legacy CSV).
    """
    if not rows:
        return []
    out: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        src = str(r.get("source") or "").strip().lower()
        if src == "era_archive":
            continue
        out.append(dict(r))
    return out


def assert_not_archive_path(path: str | Path) -> None:
    """
    Refuse archive / round history paths for live-ledger loaders.

    Raises RuntimeError if ``path`` contains any ARCHIVE_PATH_MARKERS
    (normalized with forward slashes, case-insensitive).
    """
    p = str(path or "").replace("\\", "/").lower()
    for marker in ARCHIVE_PATH_MARKERS:
        if marker.lower() in p:
            raise RuntimeError(
                f"live ledger refuses archive path containing '{marker}': {path}"
            )
