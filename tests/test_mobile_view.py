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
    # place_these.rows_preview is always a list (object rows or empty)
    assert isinstance(snap["place_these"]["rows_preview"], list)


def test_rows_preview_object_shape_from_fixture(readers_mod, tmp_path):
    """Object-shaped rows_preview when PLACE_THESE has placeable table rows."""
    md = """# Bets to place — 2026-07-12

Phase **1B** | Equity **547.57** | Remaining risk **65.71** / cap **65.71**

| # | Match | Selection | Odds | Stake NOK | EV | Grade | Band |
|---|-------|-----------|------|-----------|----|-------|------|
| 1 | Racing Club Montevideo vs CA Penarol Montevideo | CA Penarol Montevideo | 2.30 | 18 | 0.117 | A | 2.2-2.5 |
| 2 | Washington Mystics vs Seattle Storm | Washington Mystics (incl. OT) | 1.37 | 14 | 0.061 | A | <1.5 |
| 3 | FH Hafnarfjordur vs Valur Reykjavik | Over 2.5 goals | 1.37 | 13 | 0.048 | A | <1.5 |

## Notes
- note one
"""
    root = tmp_path
    (root / "outbox").mkdir()
    (root / "data" / "state").mkdir(parents=True)
    (root / "outbox" / "PLACE_THESE.md").write_text(md, encoding="utf-8")
    (root / "data" / "bets.csv").write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,sport,updated_at,p_l_nok,created_at\n",
        encoding="utf-8",
    )

    place = readers_mod._place_these(root / "outbox" / "PLACE_THESE.md")
    rows = place["rows_preview"]
    assert len(rows) == 3
    assert all(isinstance(r, dict) for r in rows)
    r0 = rows[0]
    for key in (
        "index",
        "match",
        "selection",
        "decimal_odds",
        "stake_nok",
        "ev",
        "grade",
        "band",
    ):
        assert key in r0
    assert r0["index"] == 1
    assert r0["match"] == "Racing Club Montevideo vs CA Penarol Montevideo"
    assert r0["selection"] == "CA Penarol Montevideo"
    assert abs(r0["decimal_odds"] - 2.30) < 0.001
    assert abs(r0["stake_nok"] - 18) < 0.001
    assert abs(r0["ev"] - 0.117) < 0.0001
    assert r0["grade"] == "A"
    assert r0["band"] == "2.2-2.5"
    assert rows[2]["selection"] == "Over 2.5 goals"

    snap = readers_mod.build_desk_snapshot(root)
    assert snap["schema_version"] == 1
    assert len(snap["place_these"]["rows_preview"]) == 3


def test_rows_preview_empty_for_no_bets_slip(readers_mod, tmp_path):
    """NO BETS marker → rows_preview stays [] (not a placeable row)."""
    md = """# Bets to place — empty

Phase **1A** | Equity **550.99** | Remaining risk **8.00** / cap **42.00**

| # | Match | Selection | Odds | Stake NOK | EV | Grade | Band |
|---|-------|-----------|------|-----------|----|-------|------|
| — | **NO BETS** | empty slip is success (after research) | — | — | — | — | — |
"""
    (tmp_path / "outbox").mkdir()
    (tmp_path / "outbox" / "PLACE_THESE.md").write_text(md, encoding="utf-8")
    place = readers_mod._place_these(tmp_path / "outbox" / "PLACE_THESE.md")
    assert place["exists"] is True
    assert place["rows_preview"] == []


def test_rows_preview_empty_when_missing_or_unparseable(readers_mod, tmp_path):
    missing = readers_mod._place_these(tmp_path / "nope.md")
    assert missing["exists"] is False
    assert missing["rows_preview"] == []

    (tmp_path / "outbox").mkdir()
    (tmp_path / "outbox" / "PLACE_THESE.md").write_text("hello\nno table\n", encoding="utf-8")
    place = readers_mod._place_these(tmp_path / "outbox" / "PLACE_THESE.md")
    assert place["rows_preview"] == []


def test_rows_preview_optional_columns(readers_mod):
    md = """# Bets to place — test
Phase **2** | Equity **100.00** | Remaining risk **10.00** / cap **20.00**
| # | Match | Selection | Odds | Stake NOK |
|---|-------|-----------|------|-----------|
| 1 | Team A vs Team B | Team A | 1.90 | 12 |
"""
    rows = readers_mod._parse_rows_preview(md)
    assert len(rows) == 1
    assert rows[0]["match"] == "Team A vs Team B"
    assert rows[0]["grade"] is None
    assert rows[0]["band"] is None
    assert abs(rows[0]["decimal_odds"] - 1.90) < 0.001


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
    body_h = h.json()
    assert body_h["ok"] is True
    assert body_h.get("service") == "nt-mobile-view"
    d = client.get("/api/desk")
    assert d.status_code == 200
    body = d.json()
    assert body["schema_version"] == 1
    assert body["view_only"] is True
    # Raw JSON object (not re-encoded strip) — future keys would survive round-trip at cache layer
    assert "charts" in body
    assert isinstance(body["place_these"]["rows_preview"], list)
    # Additive contract: element is dict when present
    for row in body["place_these"]["rows_preview"]:
        assert isinstance(row, dict)
        assert "match" in row and "selection" in row
    raw = json.dumps(body)
    assert "schema_version" in raw
