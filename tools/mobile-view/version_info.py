"""Package version for mobile-view (distinct from desk schema_version)."""

from __future__ import annotations

from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parent / "VERSION"


def read_api_version() -> str:
    """Return api_version from VERSION file (fallback if missing)."""
    try:
        text = _VERSION_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text.splitlines()[0].strip()
    except OSError:
        pass
    return "0.0.0"


API_VERSION = read_api_version()
SCHEMA_VERSION = 1  # wire contract; see docs/api/DESK_SCHEMA_V1.md
SERVICE_NAME = "nt-mobile-view"
