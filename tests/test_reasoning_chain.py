"""Minimal reasoning-chain build + dump (recommend audit path)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.portfolio import Recommendation
from nt.reasoning_chain import (
    append_reasoning_chains,
    build_chain_from_near_miss,
    build_chain_from_pick,
    build_recommend_chains,
    dump_reasoning_for_recommend,
    format_reasoning_md,
    is_near_miss_reject,
    reasoning_cfg,
    select_near_misses,
)


def _cfg(tmp: Path) -> dict:
    state = tmp / "state"
    state.mkdir(parents=True, exist_ok=True)
    return {
        "paths": {
            "state_dir": str(state),
            "reasoning_chains_jsonl": str(state / "reasoning_chains.jsonl"),
        },
        "selection": {"probability_haircut": 0.03},
        "reasoning": {
            "enabled": True,
            "jsonl": str(state / "reasoning_chains.jsonl"),
            "max_near_miss": 5,
            "near_miss_ev_slack": 0.04,
            "place_md_section": True,
        },
    }


def test_build_chain_from_pick_minimal():
    rec = Recommendation(
        match="Alpha vs Beta",
        selection="Over 2.5",
        decimal_odds=2.05,
        stake_nok=12.0,
        ev=0.062,
        grade="B",
        odds_band="1.85-2.20",
        sport="football",
        market_type="total",
        p_model=0.55,
        notes="p_model=0.5500; EV=0.062; promo_score=72.5",
        explore=False,
        learning_stake_mult=1.0,
        learning_ev_boost=0.0,
        reasons=["mid band"],
        evidence_path="evidence/alpha_over25.json",
    )
    chain = build_chain_from_pick(rec, haircut=0.03, phase_id="1A", bet_id="bid1")
    assert chain["kind"] == "pick"
    assert chain["match"] == "Alpha vs Beta"
    assert chain["selection"] == "Over 2.5"
    assert abs(float(chain["p_model"]) - 0.55) < 1e-9
    assert chain["stake_nok"] == 12.0
    assert chain["phase"] == "1A"
    assert chain["bet_id"] == "bid1"
    assert chain["haircut"] == 0.03
    # haircut EV: (0.55-0.03)*2.05 - 1 = 0.066
    assert chain["ev_after_haircut"] is not None
    assert abs(float(chain["ev_after_haircut"]) - 0.066) < 1e-6
    assert chain["light"].get("promotion_score") == 72.5
    assert chain["evidence_path"].endswith("alpha_over25.json")


def test_build_chain_from_pick_dict_and_controls():
    pick = {
        "match": "X vs Y",
        "selection": "X ML",
        "decimal_odds": 1.95,
        "stake_nok": 15,
        "ev": 0.04,
        "grade": "A",
        "sport": "tennis",
        "p_model": 0.58,
        "notes": "temp_ev_relax:delta=0.015;stake×0.80; EXPLORE",
        "explore": True,
        "learning_stake_mult": 0.9,
        "learning_ev_boost": 0.01,
        "stake_decision": {
            "size_mode": "NORMAL",
            "active_unit_nok": 12,
            "temp_ev_relax": {"delta_ev": 0.015, "stake_mult": 0.80},
        },
    }
    chain = build_chain_from_pick(pick, haircut=0.03, phase_id="1A+")
    assert chain["kind"] == "pick"
    ctrl = chain["controls"]
    assert ctrl.get("temp_ev_relax") is True
    assert abs(float(ctrl.get("temp_ev_relax_delta")) - 0.015) < 1e-9
    assert ctrl.get("explore") is True
    assert ctrl.get("size_mode") == "NORMAL"
    assert abs(float(ctrl.get("learning_stake_mult")) - 0.9) < 1e-9


def test_near_miss_select_and_build():
    rejects = [
        {"match": "A", "selection": "ML", "reason": "no p_model", "odds": 1.9},
        {
            "match": "B",
            "selection": "Over 3.5",
            "reason": "EV 0.018 < min_ev 0.03",
            "ev": 0.018,
            "odds": 2.10,
            "p_model": 0.52,
            "grade": "B",
            "sport": "football",
        },
        {
            "match": "C",
            "selection": "HC -1.5",
            "reason": "process_gate:+0.02",
            "ev": 0.035,
            "odds": 2.40,
        },
    ]
    assert not is_near_miss_reject(rejects[0])
    assert is_near_miss_reject(rejects[1])
    assert is_near_miss_reject(rejects[2])
    selected = select_near_misses(rejects, max_n=2)
    assert len(selected) == 2
    # Higher EV first
    assert selected[0]["match"] == "C"
    chain = build_chain_from_near_miss(selected[1], haircut=0.03, phase_id="1A")
    assert chain["kind"] == "near_miss"
    assert chain["match"] == "B"
    assert "min_ev" in chain["reject_reason"]


def test_format_reasoning_md_and_dump(tmp_path: Path):
    cfg = _cfg(tmp_path)
    picks = [
        Recommendation(
            match="Home vs Away",
            selection="BTTS Yes",
            decimal_odds=1.90,
            stake_nok=12.0,
            ev=0.05,
            grade="B",
            odds_band="1.85-2.20",
            sport="football",
            market_type="btts",
            p_model=0.58,
            notes="p_model=0.5800; EV=0.050",
        )
    ]
    rejects = [
        {
            "match": "Home vs Away",
            "selection": "Over 2.5",
            "reason": "EV 0.01 < min_ev 0.03",
            "ev": 0.01,
            "odds": 2.00,
            "p_model": 0.52,
        }
    ]
    chains = build_recommend_chains(cfg, picks, rejects, phase_id="1A")
    assert len(chains) >= 2
    md = format_reasoning_md(chains)
    assert "## Reasoning" in md
    assert "Home vs Away" in md
    assert "p_model=" in md

    place = "# Bets to place\n\n| 1 | Home vs Away | BTTS Yes |\n\n## Notes\n\n- ok\n"
    updated, written, path = dump_reasoning_for_recommend(
        cfg, picks, rejects, place_md=place, phase_id="1A"
    )
    assert "## Reasoning" in updated
    assert path is not None and path.exists()
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == len(written)
    row = json.loads(lines[0])
    assert row["kind"] in ("pick", "near_miss")
    assert row.get("schema_version") == 1


def test_reasoning_disabled_skips(tmp_path: Path):
    cfg = _cfg(tmp_path)
    cfg["reasoning"]["enabled"] = False
    chains = build_recommend_chains(
        cfg,
        [
            {
                "match": "M",
                "selection": "S",
                "decimal_odds": 2.0,
                "stake_nok": 10,
                "ev": 0.05,
                "grade": "B",
                "p_model": 0.55,
            }
        ],
        [],
    )
    assert chains == []
    md, written, path = dump_reasoning_for_recommend(
        cfg, [], [], place_md="# empty\n"
    )
    assert written == []
    assert path is None
    assert md == "# empty\n"


def test_append_and_cfg_defaults():
    cfg = {"reasoning": {}, "selection": {}}
    rc = reasoning_cfg(cfg)
    assert rc["enabled"] is True
    assert rc["max_near_miss"] == 8
