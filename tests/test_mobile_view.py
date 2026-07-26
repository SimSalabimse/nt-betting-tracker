"""Mobile-view: bind resolver, desk snapshot, write-guard 405, no nt import in readers."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import time
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


def _write_minimal_desk_fixture(root: Path, *, stake: str = "18") -> None:
    """Minimal on-disk tree for content-identity tests."""
    (root / "data" / "state").mkdir(parents=True, exist_ok=True)
    (root / "outbox").mkdir(parents=True, exist_ok=True)
    (root / "inbox").mkdir(parents=True, exist_ok=True)
    (root / "data" / "state" / "bankroll.json").write_text(
        json.dumps(
            {
                "equity_nok": 500.0,
                "liquid_nok": 500.0,
                "baseline_nok": 500.0,
                "realized_pl_nok": 0.0,
                "pending_at_risk_nok": float(stake),
                "settled_count": 0,
                "pending_count": 1,
                "updated_at": "2026-07-26T12:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (root / "data" / "state" / "risk.json").write_text(
        json.dumps(
            {
                "can_bet": True,
                "size_mode": "normal",
                "stopped": False,
                "remaining_risk_nok": 50.0,
                "open_pending_risk_nok": float(stake),
                "reasons": [],
            }
        ),
        encoding="utf-8",
    )
    (root / "data" / "state" / "phase.json").write_text(
        json.dumps({"phase_id": "1B", "label": "Phase 1B"}),
        encoding="utf-8",
    )
    (root / "data" / "state" / "capital_segments.json").write_text(
        json.dumps({"ref_hwm_nok": 500.0}),
        encoding="utf-8",
    )
    (root / "data" / "state" / "status.md").write_text("# status\nok\n", encoding="utf-8")
    (root / "data" / "bets.csv").write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,sport,updated_at,p_l_nok,created_at,notes\n"
        f"b1,2026-07-26,Team A vs Team B,Team A,2.10,{stake},Pending,football,"
        "2026-07-26T10:00:00Z,,2026-07-26T09:00:00Z,kickoff=2026-07-26 18:00\n",
        encoding="utf-8",
    )
    (root / "outbox" / "PLACE_THESE.md").write_text(
        "# Bets to place — test\n\nPhase **1B** | Equity **500.00**\n",
        encoding="utf-8",
    )


@pytest.fixture
def isolated_identity(readers_mod, tmp_path, monkeypatch):
    """Point durable identity + clear memory cache so tests do not touch package .cache."""
    identity = tmp_path / "pkg_cache" / "desk_identity.json"
    monkeypatch.setattr(readers_mod, "_IDENTITY_PATH", identity)
    readers_mod.clear_desk_cache()
    yield identity
    readers_mod.clear_desk_cache()


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
    assert body_h.get("schema_version") == 1
    assert isinstance(body_h.get("api_version"), str) and body_h["api_version"]
    d = client.get("/api/desk")
    assert d.status_code == 200
    body = d.json()
    assert body["schema_version"] == 1
    assert body.get("api_version") == body_h["api_version"]
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


# --- content identity (api_version 1.2.0 / D1) ---------------------------------


def test_canonical_json_bytes_golden(readers_mod):
    """Golden: sorted keys, compact separators, UTF-8, no NaN."""
    obj = {"b": 2, "a": 1, "nested": {"z": True, "y": "æ"}, "n": None}
    raw = readers_mod._canonical_json_bytes(obj)
    assert raw == '{"a":1,"b":2,"n":null,"nested":{"y":"æ","z":true}}'.encode("utf-8")


def test_fingerprint_excludes_generated_at_and_content_hash(readers_mod):
    body = {
        "schema_version": 1,
        "api_version": "1.2.0",
        "equity_nok": 500.0,
        "project_root": "/tmp/x",
        "view_only": True,
        "generated_at": "2026-07-26T12:00:00Z",
        "content_hash": "deadbeefdeadbeef",
    }
    h1 = readers_mod.fingerprint_desk(body)
    stripped = {k: v for k, v in body.items() if k not in ("generated_at", "content_hash")}
    h2 = readers_mod.fingerprint_desk(stripped)
    assert h1 == h2
    assert len(h1) == 16
    assert all(c in "0123456789abcdef" for c in h1)
    # Changing content changes hash
    stripped["equity_nok"] = 501.0
    assert readers_mod.fingerprint_desk(stripped) != h1


def test_identity_path_is_package_local(readers_mod, monkeypatch):
    monkeypatch.setattr(readers_mod, "_IDENTITY_PATH", None)
    p = readers_mod._identity_file_path()
    assert p.name == "desk_identity.json"
    assert p.parent.name == ".cache"
    assert p.parent.parent.resolve() == MV.resolve()
    assert "data/state" not in p.as_posix()
    assert "data\\state" not in str(p)


def test_content_identity_stable_and_durable(readers_mod, tmp_path, isolated_identity):
    """Identical fixtures → same hash/generated_at; restart memory → same generated_at."""
    root = tmp_path / "desk_root"
    _write_minimal_desk_fixture(root)

    s1 = readers_mod.build_desk_snapshot(root)
    s2 = readers_mod.build_desk_snapshot(root)
    assert s1["content_hash"] == s2["content_hash"]
    assert s1["generated_at"] == s2["generated_at"]
    assert isinstance(s1["content_hash"], str) and len(s1["content_hash"]) == 16
    assert s1["schema_version"] == 1
    assert s1.get("api_version")  # package version present

    # Simulate process restart: drop memory cache; durable identity file remains.
    readers_mod.clear_desk_cache()
    s3 = readers_mod.build_desk_snapshot(root)
    assert s3["content_hash"] == s1["content_hash"]
    assert s3["generated_at"] == s1["generated_at"]
    assert isolated_identity.is_file()
    stored = json.loads(isolated_identity.read_text(encoding="utf-8"))
    assert stored["content_hash"] == s1["content_hash"]
    assert stored["generated_at"] == s1["generated_at"]


def test_content_identity_changes_when_stake_mutates(readers_mod, tmp_path, isolated_identity, monkeypatch):
    root = tmp_path / "desk_root"
    _write_minimal_desk_fixture(root, stake="18")
    times = iter(["2026-07-26T12:00:00Z", "2026-07-26T12:00:05Z"])
    monkeypatch.setattr(readers_mod, "_now_iso", lambda: next(times))
    s1 = readers_mod.build_desk_snapshot(root)

    # Mutate stake in bets.csv (and bankroll pending to keep consistent enough)
    _write_minimal_desk_fixture(root, stake="25")
    # Ensure mtime advances on filesystems with coarse resolution
    time.sleep(0.02)
    readers_mod.clear_desk_cache()
    s2 = readers_mod.build_desk_snapshot(root)
    assert s2["content_hash"] != s1["content_hash"]
    assert s2["generated_at"] != s1["generated_at"]
    assert s1["generated_at"] == "2026-07-26T12:00:00Z"
    assert s2["generated_at"] == "2026-07-26T12:00:05Z"


def test_content_identity_stable_across_wall_clock(readers_mod, tmp_path, isolated_identity, monkeypatch):
    """Idle wall-clock only → hash and generated_at stable (not response-time stamps)."""
    root = tmp_path / "desk_root"
    _write_minimal_desk_fixture(root)

    times = iter(
        [
            "2026-07-26T10:00:00Z",
            "2026-07-26T10:05:00Z",
            "2026-07-26T11:00:00Z",
        ]
    )

    def fake_now() -> str:
        return next(times)

    monkeypatch.setattr(readers_mod, "_now_iso", fake_now)
    s1 = readers_mod.build_desk_snapshot(root)
    # Memory hit should not call _now_iso again
    s2 = readers_mod.build_desk_snapshot(root)
    assert s1["generated_at"] == "2026-07-26T10:00:00Z"
    assert s2["generated_at"] == s1["generated_at"]
    assert s2["content_hash"] == s1["content_hash"]

    # After memory clear, durable identity reuses first-seen time (not next wall clock).
    readers_mod.clear_desk_cache()
    s3 = readers_mod.build_desk_snapshot(root)
    assert s3["generated_at"] == "2026-07-26T10:00:00Z"
    assert s3["content_hash"] == s1["content_hash"]


def test_memory_cache_skips_rebuild(readers_mod, tmp_path, isolated_identity, monkeypatch):
    root = tmp_path / "desk_root"
    _write_minimal_desk_fixture(root)
    calls = {"n": 0}
    real_build = readers_mod._build_desk_body

    def counting_build(r):
        calls["n"] += 1
        return real_build(r)

    monkeypatch.setattr(readers_mod, "_build_desk_body", counting_build)
    readers_mod.build_desk_snapshot(root)
    readers_mod.build_desk_snapshot(root)
    assert calls["n"] == 1
    readers_mod.clear_desk_cache()
    readers_mod.build_desk_snapshot(root)
    assert calls["n"] == 2


def test_no_writes_under_data_state(readers_mod, tmp_path, isolated_identity):
    root = tmp_path / "desk_root"
    _write_minimal_desk_fixture(root)
    state_dir = root / "data" / "state"
    before = {p.name: p.stat().st_mtime_ns for p in state_dir.iterdir()}
    readers_mod.build_desk_snapshot(root)
    readers_mod.clear_desk_cache()
    readers_mod.build_desk_snapshot(root)
    after = {p.name: p.stat().st_mtime_ns for p in state_dir.iterdir()}
    assert before == after
    # Identity only under the monkeypatched package-local path
    assert isolated_identity.is_file()
    assert not (root / "data" / "state" / "desk_identity.json").exists()


def test_api_version_is_1_2_0():
    ver = (MV / "VERSION").read_text(encoding="utf-8").strip().splitlines()[0]
    assert ver == "1.2.0"
