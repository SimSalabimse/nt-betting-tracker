"""Optional nt/data_platform adapter — works without nt_data installed."""

from __future__ import annotations

import builtins
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.data_platform import data_platform_cfg, get_client, is_available
from nt.data_platform.client import is_available as is_available_client
from nt.defaults import data_platform_cfg as defaults_data_platform_cfg


def test_data_platform_cfg_defaults_when_missing():
    cfg = data_platform_cfg({})
    assert cfg["enabled"] is False
    assert cfg["sim_features"] is False
    assert cfg["allow_raw_sql"] is False
    assert cfg["lake_root"] is None


def test_data_platform_cfg_merges_and_coerces():
    cfg = data_platform_cfg(
        {
            "data_platform": {
                "enabled": True,
                "sim_features": 1,
                "allow_raw_sql": "yes",
                "lake_root": r"C:\data\nt-lake",
            }
        }
    )
    assert cfg["enabled"] is True
    assert cfg["sim_features"] is True
    assert cfg["allow_raw_sql"] is True
    assert cfg["lake_root"] == r"C:\data\nt-lake"


def test_data_platform_cfg_empty_lake_root_becomes_none():
    cfg = data_platform_cfg({"data_platform": {"lake_root": "  "}})
    assert cfg["lake_root"] is None


def test_data_platform_cfg_reexported_from_package():
    assert data_platform_cfg is defaults_data_platform_cfg


def test_is_available_false_when_nt_data_missing(monkeypatch):
    """Simulate missing package: is_available must be False and must not raise."""
    removed: dict = {}
    for key in list(sys.modules):
        if key == "nt_data" or key.startswith("nt_data."):
            removed[key] = sys.modules.pop(key)

    real_import = builtins.__import__

    def _block_nt_data(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "nt_data" or (isinstance(name, str) and name.startswith("nt_data.")):
            raise ImportError("simulated missing nt_data")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _block_nt_data)
    try:
        assert is_available() is False
        assert is_available_client() is False
        # get_client must not raise even when enabled would want a client
        client = get_client({"data_platform": {"enabled": True}})
        assert client is None
    finally:
        sys.modules.update(removed)


def test_get_client_none_when_disabled():
    """enabled false → None even if nt_data happens to be installed."""
    client = get_client({"data_platform": {"enabled": False}})
    assert client is None


def test_get_client_none_when_section_absent():
    client = get_client({})
    assert client is None


def test_get_client_none_when_enabled_but_package_missing(monkeypatch):
    removed: dict = {}
    for key in list(sys.modules):
        if key == "nt_data" or key.startswith("nt_data."):
            removed[key] = sys.modules.pop(key)

    real_import = builtins.__import__

    def _block_nt_data(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "nt_data" or (isinstance(name, str) and name.startswith("nt_data.")):
            raise ImportError("simulated missing nt_data")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _block_nt_data)
    try:
        assert get_client({"data_platform": {"enabled": True, "lake_root": r"C:\data\nt-lake"}}) is None
    finally:
        sys.modules.update(removed)


def test_live_config_defaults_off():
    """config.yaml ships with data_platform disabled (desk without lake)."""
    from nt.config import load_config

    cfg = load_config()
    dp = data_platform_cfg(cfg)
    assert dp["enabled"] is False
    assert get_client(cfg) is None


def test_requirements_txt_has_no_lake_deps():
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for banned in ("pyarrow", "pandas", "duckdb"):
        assert banned not in req, f"{banned} must not enter base requirements.txt"
