"""
On Windows, the built-in module name ``nt`` shadows this project's ``nt/`` package.
Call ``ensure_local_nt()`` before any ``from nt...`` import so the local package wins.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PKG_DIR = ROOT / "nt"


def ensure_local_nt() -> None:
    existing = sys.modules.get("nt")
    if existing is not None and getattr(existing, "__path__", None):
        # Already a package (local)
        paths = list(existing.__path__)
        if str(PKG_DIR) in paths or any(Path(p).resolve() == PKG_DIR.resolve() for p in paths):
            return

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    # Replace built-in/non-package nt with our package shell
    init_py = PKG_DIR / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "nt",
        init_py,
        submodule_search_locations=[str(PKG_DIR)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load local nt package from {PKG_DIR}")

    module = importlib.util.module_from_spec(spec)
    # Ensure package attributes before exec (submodule imports need __path__)
    module.__path__ = [str(PKG_DIR)]  # type: ignore[attr-defined]
    module.__package__ = "nt"
    sys.modules["nt"] = module
    spec.loader.exec_module(module)


# Auto-run on import for convenience
ensure_local_nt()
