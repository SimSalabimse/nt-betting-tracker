"""Thin optional adapter to the sibling ``nt_data`` package (nt-data-platform).

Never raises on a missing ``nt_data`` install. Callers must treat ``None``
from ``get_client`` as "lake unavailable" and continue without lake features.
"""

from __future__ import annotations

from typing import Any


def is_available() -> bool:
    """True only when the ``nt_data`` package is importable."""
    try:
        import nt_data  # noqa: F401
    except ImportError:
        return False
    return True


def get_client(cfg: dict[str, Any] | None = None) -> Any | None:
    """
    Return a read-only ``DataClient`` or ``None``.

    Returns ``None`` when:
      - ``data_platform.enabled`` is false (even if ``nt_data`` is installed)
      - ``nt_data`` is not importable
    """
    from nt.defaults import data_platform_cfg

    if cfg is None:
        from nt.config import load_config

        cfg = load_config()

    dp = data_platform_cfg(cfg)
    if not dp.get("enabled"):
        return None
    if not is_available():
        return None

    try:
        from nt_data.paths import resolve_lake_root
        from nt_data.query.api import DataClient
    except ImportError:
        return None

    root = resolve_lake_root(
        lake_cfg_root=dp.get("lake_root"),
        environ=None,  # uses os.environ (NT_DATA_LAKE wins)
    )
    # Adapter default: read_only so sql() is gated. allow_raw_sql is a
    # config flag for future operator wrappers — never auto-open SQL here.
    return DataClient(lake_root=root, read_only=True)
