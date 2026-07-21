"""P2 multi-sport suggestion sims."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.sim_basketball import BasketballSimInputs, simulate_basketball
from nt.sim_tennis import TennisSimInputs, simulate_tennis


def test_tennis_p_in_unit_interval():
    r = simulate_tennis(
        TennisSimInputs(
            player_a="A",
            player_b="B",
            hold_a=0.82,
            hold_b=0.74,
            selection="Vinner: A",
        )
    )
    assert 0.01 < r["p_model"] < 0.99
    assert "SUGGESTION ONLY" in " ".join(r["warnings"])
    assert r["sport"] == "tennis"


def test_basketball_over_under():
    r = simulate_basketball(
        BasketballSimInputs(
            home="H",
            away="A",
            mean_margin=3.0,
            mean_total=220.0,
            total_line=218.5,
            selection="Over 218.5",
        )
    )
    assert 0.01 < r["p_model"] < 0.99
    assert "over" in r["markets"]
    assert r["sport"] == "basketball"
