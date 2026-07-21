"""P2 historical replay of settled tickets under capital_v2 + Kelly rules."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.historical_replay import replay_last_settled, render_replay_markdown


def test_replay_last_settled_zero_violations():
    cfg = load_config()
    report = replay_last_settled(cfg, n=40)
    assert report["n_replayed"] >= 1
    assert report["n_replayed"] <= 40
    # May be fewer than 40 if live book is small
    assert report["n_available_settled"] >= report["n_replayed"]
    assert report["summary"]["n_violations"] == 0
    assert report["pass"] is True
    for row in report["rows"]:
        assert row["stake_replay"] >= 0
        # NT floor or zero (room/frozen)
        if row["stake_replay"] > 0:
            assert row["stake_replay"] >= 10 - 1e-9
            assert abs(row["stake_replay"] - int(row["stake_replay"])) < 1e-9
        assert not row["violations"]


def test_replay_markdown_renders():
    cfg = load_config()
    report = replay_last_settled(cfg, n=5)
    md = render_replay_markdown(report)
    assert "Historical replay" in md
    assert "PASS" in md
