"""Deep queue SSOT export (data/state/deep_queue.json / D17)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.deep_queue_state import (
    build_deep_queue_state,
    build_deep_queue_state_from_payload,
    composition_from_queue,
    deep_queue_state_path,
    load_deep_queue_state,
    normalize_queue_line,
    write_deep_queue_from_light_payload,
    write_deep_queue_state,
)


def _cfg(tmp_path: Path) -> dict:
    return {"paths": {"state_dir": str(tmp_path)}}


def test_normalize_queue_line_flags_from_engine():
    line = {
        "match": "A vs B",
        "selection": "Handikap 3.5: A +3.5",
        "sport": "tennis",
        "decimal_odds": 1.95,
        "preferred": True,
        "short_main": False,
    }
    out = normalize_queue_line(line)
    assert out["match"] == "A vs B"
    assert out["selection"] == "Handikap 3.5: A +3.5"
    assert out["decimal_odds"] == 1.95
    assert out["preferred"] is True
    assert out["short_main"] is False
    assert out["sport"] == "tennis"


def test_composition_from_queue_shares():
    queue = [
        {"preferred": True, "short_main": False},
        {"preferred": True, "short_main": False},
        {"preferred": True, "short_main": False},
        {"preferred": False, "short_main": True},
    ]
    comp = composition_from_queue(queue)
    assert comp["n"] == 4
    assert comp["preferred_n"] == 3
    assert comp["short_main_n"] == 1
    assert comp["preferred_share"] == 0.75
    assert comp["short_main_share"] == 0.25
    assert comp["meets_preferred_floor"] is True
    assert comp["meets_short_main_cap"] is True


def test_build_uses_engine_composition_not_invented():
    """Engine deep_queue_composition is SSOT when n matches queue length."""
    queue = [
        {
            "match": "M1",
            "selection": "Vinner: A",
            "decimal_odds": 2.05,
            "preferred": True,
            "short_main": False,
        },
        {
            "match": "M2",
            "selection": "Vinner: B",
            "decimal_odds": 1.70,
            "preferred": False,
            "short_main": True,
        },
    ]
    # Engine reports shares (must be used as-is when n matches)
    engine_comp = {
        "n": 2,
        "preferred_n": 1,
        "short_main_n": 1,
        "preferred_share": 0.5,
        "short_main_share": 0.5,
        "meets_preferred_floor": False,
        "meets_short_main_cap": False,
    }
    state = build_deep_queue_state(
        queue=queue,
        composition=engine_comp,
        updated_at="2026-07-22T12:00:00+00:00",
        source="light_research",
        odds_path="inbox/fake.txt",
        day="2026-07-22",
    )
    assert state["schema_version"] == 1
    assert state["updated_at"] == "2026-07-22T12:00:00+00:00"
    assert state["source"] == "light_research"
    assert state["deep_queue_composition"]["preferred_share"] == 0.5
    assert state["deep_queue_composition"]["short_main_share"] == 0.5
    assert state["preferred_share"] == 0.5
    assert state["short_main_share"] == 0.5
    assert len(state["deep_queue"]) == 2
    assert state["deep_queue"][0]["preferred"] is True
    assert state["deep_queue"][1]["short_main"] is True


def test_build_from_light_payload_shape():
    payload = {
        "day": "2026-07-22",
        "odds_path": "inbox/x.txt",
        "generated_at": "2026-07-22T15:00:00+00:00",
        "tiers_config": {
            "preferred_odds_lo": 1.85,
            "deep_min_preferred_share": 0.55,
            "deep_max_short_main_share": 0.25,
        },
        "deep_queue": [
            {
                "match": "A vs B",
                "selection": "Totalt 3.5: Over 3.5",
                "sport": "football",
                "decimal_odds": 2.10,
                "preferred": True,
                "short_main": False,
            },
            {
                "match": "C vs D",
                "selection": "Game handikap: E +2.5",
                "sport": "tennis",
                "decimal_odds": 1.92,
                "preferred": True,
                "short_main": False,
            },
            {
                "match": "E vs F",
                "selection": "Vinner: Fav",
                "sport": "basketball",
                "decimal_odds": 1.60,
                "preferred": False,
                "short_main": True,
            },
        ],
        "deep_queue_composition": {
            "n": 3,
            "preferred_n": 2,
            "short_main_n": 1,
            "preferred_share": 0.667,
            "short_main_share": 0.333,
            "meets_preferred_floor": True,
            "meets_short_main_cap": False,
        },
    }
    state = build_deep_queue_state_from_payload(payload, source="board")
    assert state["source"] == "board"
    assert state["day"] == "2026-07-22"
    assert state["odds_path"] == "inbox/x.txt"
    assert state["updated_at"] == "2026-07-22T15:00:00+00:00"
    comp = state["deep_queue_composition"]
    assert comp["n"] == 3
    assert comp["preferred_n"] == 2
    assert comp["short_main_n"] == 1
    assert comp["preferred_share"] == 0.667
    assert comp["short_main_share"] == 0.333
    assert len(state["deep_queue"]) == 3
    assert {k for k in state["deep_queue"][0]} >= {
        "match",
        "selection",
        "decimal_odds",
        "preferred",
        "short_main",
    }


def test_write_and_load_roundtrip(tmp_path: Path):
    cfg = _cfg(tmp_path)
    payload = {
        "day": "2026-07-22",
        "odds_path": "inbox/y.txt",
        "generated_at": "2026-07-22T16:00:00+00:00",
        "deep_queue": [
            {
                "match": "X vs Y",
                "selection": "Under 2.5",
                "decimal_odds": 2.00,
                "preferred": True,
                "short_main": False,
            }
        ],
        "deep_queue_composition": {
            "n": 1,
            "preferred_n": 1,
            "short_main_n": 0,
            "preferred_share": 1.0,
            "short_main_share": 0.0,
            "meets_preferred_floor": True,
            "meets_short_main_cap": True,
        },
    }
    path = write_deep_queue_from_light_payload(cfg, payload, source="light_research")
    assert path == deep_queue_state_path(cfg)
    assert path.is_file()
    assert path.name == "deep_queue.json"

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["deep_queue_composition"]["preferred_share"] == 1.0
    assert raw["deep_queue"][0]["match"] == "X vs Y"

    loaded = load_deep_queue_state(cfg)
    assert loaded is not None
    assert loaded["preferred_share"] == 1.0
    assert loaded["short_main_share"] == 0.0


def test_empty_queue_write_shape(tmp_path: Path):
    cfg = _cfg(tmp_path)
    state = build_deep_queue_state(queue=[], composition=None, source="light_research")
    path = write_deep_queue_state(cfg, state)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["deep_queue"] == []
    assert loaded["deep_queue_composition"]["n"] == 0
    assert loaded["deep_queue_composition"]["preferred_share"] == 0.0
    assert loaded["deep_queue_composition"]["short_main_share"] == 0.0
    assert loaded["preferred_share"] == 0.0


def test_composition_recount_when_engine_n_mismatch():
    """If composition.n disagrees with queue length, recount from line flags."""
    queue = [
        {
            "match": "A",
            "selection": "s",
            "decimal_odds": 2.0,
            "preferred": True,
            "short_main": False,
        },
        {
            "match": "B",
            "selection": "s2",
            "decimal_odds": 2.1,
            "preferred": True,
            "short_main": False,
        },
    ]
    bad_comp = {
        "n": 99,
        "preferred_n": 99,
        "short_main_n": 0,
        "preferred_share": 0.99,
        "short_main_share": 0.0,
        "meets_preferred_floor": True,
        "meets_short_main_cap": True,
    }
    state = build_deep_queue_state(queue=queue, composition=bad_comp)
    assert state["deep_queue_composition"]["n"] == 2
    assert state["deep_queue_composition"]["preferred_n"] == 2
    assert state["deep_queue_composition"]["preferred_share"] == 1.0
