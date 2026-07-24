"""Resolve project root without importing nt engines."""

from __future__ import annotations

import os
from pathlib import Path


def is_valid_project_root(path: Path) -> bool:
    return (path / "config.yaml").is_file() and (path / "data").is_dir()


def resolve_project_root(explicit: str | Path | None = None) -> Path:
    """
    Order: explicit arg → NT_PROJECT_ROOT → walk up from this file → cwd.
    """
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if is_valid_project_root(p):
            return p
        raise FileNotFoundError(f"Not a valid NT project root: {p}")

    env = os.environ.get("NT_PROJECT_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if is_valid_project_root(p):
            return p

    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if is_valid_project_root(parent):
            return parent

    cwd = Path.cwd().resolve()
    if is_valid_project_root(cwd):
        return cwd

    # Fallback: tools/mobile-view → repo root two levels up
    candidate = here.parents[1]
    return candidate
