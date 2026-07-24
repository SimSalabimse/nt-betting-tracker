"""Mobile-view: bind resolver, desk snapshot, write-guard 405, no nt import in readers."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MV = REPO / "tools" / "mobile-view"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def server_mod():
    return _load("mv_server", MV / "server.py")


@pytest.fixture(scope="module")
def readers_mod():
    return _load("mv_readers", MV / "readers.py")


def test_readers_has_no_nt_import():
    tree = ast.parse((MV / "readers.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("nt"), alias.name
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("nt"), node.module


def test_resolve_bind_host_fail_closed(server_mod, monkeypatch):
    resolve = server_mod.resolve_bind_host
    monkeypatch.delenv("MOBILE_VIEW_LAN", raising=False)
    monkeypatch.delenv("MOBILE_VIEW_HOST", raising=False)
    assert resolve(None, lan=False) == "127.0.0.1"
    assert resolve("0.0.0.0", lan=False) == "127.0.0.1"
    assert resolve("192.168.1.5", lan=False) == "127.0.0.1"
    assert resolve("localhost", lan=False) == "127.0.0.1"
    assert resolve("::1", lan=False) == "::1"
    assert resolve("0.0.0.0", lan=True) == "0.0.0.0"
    assert resolve("192.168.1.5", lan=True) == "192.168.1.5"
    assert resolve("100.64.1.2", lan=True) == "100.64.1.2"
    monkeypatch.setenv("MOBILE_VIEW_HOST", "0.0.0.0")
    monkeypatch.delenv("MOBILE_VIEW_LAN", raising=False)
    assert resolve(None, lan=None) == "127.0.0.1"
    monkeypatch.setenv("MOBILE_VIEW_LAN", "1")
    assert resolve(None, lan=None) == "0.0.0.0"


def test_build_desk_snapshot_shape(readers_mod):
    snap = readers_mod.build_desk_snapshot(REPO)
    assert snap["schema_version"] == 1
    assert snap["view_only"] is True
    assert "equity_nok" in snap
    assert "pending_bets" in snap
    assert "place_these" in snap
    assert "charts" in snap
    ch = snap["charts"]
    assert "equity_curve" in ch
    assert "daily" in ch
    assert "by_sport" in ch
    assert "overall" in ch
    assert "max_drawdown" in ch
    # Equity curve last point should track bankroll when data present
    if ch["equity_curve"] and snap.get("equity_nok") is not None:
        assert abs(ch["equity_curve"][-1]["equity"] - float(snap["equity_nok"])) < 0.05


def test_post_returns_405(server_mod):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app = server_mod.create_app(REPO)
    client = TestClient(app)
    for path in ("/api/desk", "/api/health", "/"):
        r = client.post(path, json={})
        assert r.status_code == 405, path


def test_get_desk_and_health(server_mod):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app = server_mod.create_app(REPO)
    client = TestClient(app)
    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["ok"] is True
    d = client.get("/api/desk")
    assert d.status_code == 200
    body = d.json()
    assert body["schema_version"] == 1
    assert body["view_only"] is True
    # Raw JSON object (not re-encoded strip) — future keys would survive round-trip at cache layer
    assert "charts" in body
    raw = json.dumps(body)
    assert "schema_version" in raw
