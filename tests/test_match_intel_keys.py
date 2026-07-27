"""Match key stability for MIC filesystem paths."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.match_intel.schema import mic_match_key


def test_key_stability_examples():
    assert mic_match_key("Barcelona SC vs LDU Quito") == "barcelona_sc_vs_ldu_quito"
    assert mic_match_key("Team A vs Team B") == "team_a_vs_team_b"
    # normalize hyphen/dash to vs via odds_common first
    k1 = mic_match_key("Home - Away")
    k2 = mic_match_key("Home vs Away")
    assert k1 == k2 == "home_vs_away"


def test_key_truncation():
    long = "A" * 200 + " vs " + "B" * 200
    key = mic_match_key(long)
    assert len(key) <= 120
    assert key  # non-empty
