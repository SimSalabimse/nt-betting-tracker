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
    build_light_by_key,
    build_recommend_chains,
    collect_near_miss_candidates,
    dump_reasoning_for_recommend,
    format_reasoning_md,
    is_near_miss_reject,
    reasoning_cfg,
    select_near_misses,
)


def _cfg(tmp: Path) -> dict:
    state = tmp / "state"
    outbox = tmp / "outbox"
    light = outbox / "light_research"
    state.mkdir(parents=True, exist_ok=True)
    light.mkdir(parents=True, exist_ok=True)
    return {
        "paths": {
            "state_dir": str(state),
            "outbox": str(outbox),
            "reasoning_chains_jsonl": str(state / "reasoning_chains.jsonl"),
        },
        "selection": {"probability_haircut": 0.03},
        "reasoning": {
            "enabled": True,
            "jsonl": str(state / "reasoning_chains.jsonl"),
            "max_near_miss": 5,
            "near_miss_ev_slack": 0.04,
            "place_md_section": True,
            "join_light": True,
        },
        "research": {
            "tiers": {
                "short_chalk_odds": 1.70,
                "preferred_odds_lo": 1.85,
                "preferred_odds_hi": 2.60,
                "alt_preferred_odds_lo": 1.80,
                "soft_value_min_rel": 0.03,
                "promo_mid_band_boost": 60,
                "promo_alt_boost": 14,
                "promo_short_chalk_penalty": -55,
            }
        },
    }


def _write_light_latest(cfg: dict, records: list[dict], deep_queue: list[dict] | None = None) -> Path:
    outbox = Path(cfg["paths"]["outbox"])
    light_dir = outbox / "light_research"
    light_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "records": records,
        "deep_queue": deep_queue or [],
        "shortlist_n": len(records),
    }
    path = light_dir / "LATEST.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


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
        {"match": "A", "selection": "ML", "reason": "no p_model", "odds": 1.5},
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
    # short chalk no p_model alone is not a near-miss under mid-band prefer
    assert not is_near_miss_reject(rejects[0])
    assert is_near_miss_reject(rejects[1])
    assert is_near_miss_reject(rejects[2])
    selected = select_near_misses(rejects, max_n=2)
    assert len(selected) == 2
    # Mid-band + EV prefer — B is mid-band 2.10
    assert any(s["match"] == "B" for s in selected)
    chain = build_chain_from_near_miss(
        next(s for s in selected if s["match"] == "B"),
        haircut=0.03,
        phase_id="1A",
    )
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
    assert "## Near-miss / Rejected" in md
    assert "Home vs Away" in md
    assert "p_model=" in md

    place = "# Bets to place\n\n| 1 | Home vs Away | BTTS Yes |\n\n## Notes\n\n- ok\n"
    updated, written, path = dump_reasoning_for_recommend(
        cfg, picks, rejects, place_md=place, phase_id="1A"
    )
    assert "## Reasoning" in updated
    assert "## Near-miss / Rejected" in updated
    assert path is not None and path.exists()
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == len(written)
    row = json.loads(lines[0])
    assert row["kind"] in ("pick", "near_miss", "rejected_prefilter")
    assert row.get("schema_version") == 1


def test_empty_picks_still_has_near_miss_section(tmp_path: Path):
    """Empty slip still emits ## Near-miss / Rejected (even if set is empty)."""
    cfg = _cfg(tmp_path)
    rejects = [
        {
            "match": "Mid vs Band",
            "selection": "Over 2.5",
            "reason": "EV 0.02 < min_ev 0.04",
            "ev": 0.02,
            "odds": 2.05,
            "p_model": 0.51,
            "grade": "B",
        }
    ]
    chains = build_recommend_chains(cfg, [], rejects, phase_id="1A")
    assert any(c.get("kind") != "pick" for c in chains)
    md = format_reasoning_md(chains)
    assert "## Reasoning" in md
    assert "## Near-miss / Rejected" in md
    assert "Mid vs Band" in md
    assert "stage:" in md
    assert "promo=" in md

    place = "# Bets to place\n\n| — | **NO BETS** |\n"
    updated, written, path = dump_reasoning_for_recommend(
        cfg, [], rejects, place_md=place, phase_id="1A"
    )
    assert "## Near-miss / Rejected" in updated
    assert any(c.get("kind") != "pick" for c in written)
    assert path is not None


def test_blocked_recommend_still_emits_near_miss_chains(tmp_path: Path):
    """Blocked recommend path still dumps near-miss chains from light + rejects."""
    cfg = _cfg(tmp_path)
    _write_light_latest(
        cfg,
        records=[
            {
                "match": "Bodø/Glimt vs Guest",
                "selection": "Bodø/Glimt -1.5",
                "sport": "football",
                "decimal_odds": 2.05,
                "odds_band": "1.85-2.20",
                "market_family": "handicap",
                "verdict": "pass",
                "promote_to_deep": True,
                "has_p_model": False,
                "has_deep_pack": False,
                "reason": "engine deep queue",
                "rough_ev_note": "promo_score=95.0",
            },
            {
                "match": "Short vs Fav",
                "selection": "Short ML",
                "sport": "football",
                "decimal_odds": 1.45,
                "market_family": "ml",
                "verdict": "pass",
                "has_p_model": False,
                "reason": "light-pass chalk",
            },
        ],
        deep_queue=[
            {
                "match": "Bodø/Glimt vs Guest",
                "selection": "Bodø/Glimt -1.5",
                "decimal_odds": 2.05,
                "reason": "deep queue",
            }
        ],
    )
    place = "# Bets to place\n\n## BLOCKED — research required first\n"
    updated, chains, path = dump_reasoning_for_recommend(
        cfg,
        [],
        [
            {
                "match": "Bodø/Glimt vs Guest",
                "selection": "Bodø/Glimt -1.5",
                "odds": 2.05,
                "reason": "no p_model / blocked recommend",
                "near_miss": True,
                "rejected_at_stage": "blocked_no_research",
                "source": "blocked",
            }
        ],
        place_md=place,
        phase_id="1A",
        blocked=True,
        block_reason="no_research",
    )
    assert chains, "blocked recommend must still emit near-miss chains"
    assert all(c.get("kind") != "pick" for c in chains)
    assert "## Near-miss / Rejected" in updated
    assert "Bodø" in updated or "Bodø/Glimt" in updated
    assert path is not None and path.exists()
    # light join should attach promo components / score
    bodo = next(
        (c for c in chains if "Glimt" in str(c.get("match") or "") or "Bodø" in str(c.get("match") or "")),
        chains[0],
    )
    light = bodo.get("light") or {}
    assert light.get("promotion_score") is not None or bodo.get("promotion_score") is not None


def test_light_join_puts_promotion_components_on_chain(tmp_path: Path):
    """Light LATEST join must put promotion_score + components on chain (not notes-only)."""
    cfg = _cfg(tmp_path)
    _write_light_latest(
        cfg,
        records=[
            {
                "match": "Alpha vs Beta",
                "selection": "Over 3.5",
                "sport": "football",
                "decimal_odds": 2.10,
                "odds_band": "1.85-2.20",
                "market_family": "totals_over",
                "verdict": "pass",
                "promote_to_deep": True,
                "has_p_model": False,
                "has_deep_pack": False,
                "reason": "mid alt total",
                "rough_ev_note": "need p",
                "prior_available": False,
            }
        ],
        deep_queue=[
            {
                "match": "Alpha vs Beta",
                "selection": "Over 3.5",
                "decimal_odds": 2.10,
            }
        ],
    )
    light_map = build_light_by_key(cfg)
    key = "alpha vs beta||over 3.5"
    assert key in light_map
    assert light_map[key].get("promotion_score") is not None
    assert light_map[key].get("promotion_score_components") or light_map[key].get(
        "promotion_score_breakdown"
    )

    picks = [
        Recommendation(
            match="Alpha vs Beta",
            selection="Over 3.5",
            decimal_odds=2.10,
            stake_nok=12.0,
            ev=0.05,
            grade="B",
            odds_band="1.85-2.20",
            sport="football",
            market_type="total",
            p_model=0.52,
            notes="p_model=0.5200",  # notes-only would lack promo components
        )
    ]
    chains = build_recommend_chains(cfg, picks, [], phase_id="1A", light_by_key=light_map)
    assert len(chains) >= 1
    pick_chain = chains[0]
    assert pick_chain["kind"] == "pick"
    light = pick_chain["light"]
    assert light.get("promotion_score") is not None
    comps = light.get("promotion_score_components") or (
        (light.get("promotion_score_breakdown") or {}).get("components")
    )
    assert comps, "light join must attach promotion components, not notes-only"
    assert "base" in comps or "mid_band" in comps or len(comps) >= 1


def test_collect_prefers_mid_band_and_light_pass(tmp_path: Path):
    cfg = _cfg(tmp_path)
    _write_light_latest(
        cfg,
        records=[
            {
                "match": "Mid vs Line",
                "selection": "HC -1.5",
                "sport": "football",
                "decimal_odds": 2.00,
                "market_family": "handicap",
                "verdict": "pass",
                "has_p_model": False,
                "promote_to_deep": True,
                "reason": "deep queue",
            },
            {
                "match": "Long vs Shot",
                "selection": "ML",
                "sport": "football",
                "decimal_odds": 4.50,
                "market_family": "ml",
                "verdict": "pass",
                "has_p_model": False,
                "reason": "long dog",
            },
            {
                "match": "Fail vs Pre",
                "selection": "Over 2.5",
                "sport": "football",
                "decimal_odds": 1.95,
                "market_family": "totals_over",
                "verdict": "fail",
                "has_p_model": False,
                "prefilter_stage1": "fail: chalk noise",
                "discarded": True,
                "reason": "prefilter discard",
            },
        ],
        deep_queue=[
            {"match": "Mid vs Line", "selection": "HC -1.5", "decimal_odds": 2.00}
        ],
    )
    rows = collect_near_miss_candidates(cfg, [], max_n=3)
    assert rows
    # Mid-band light-pass should rank first
    assert rows[0]["match"] == "Mid vs Line"
    kinds = {r.get("kind") for r in rows}
    assert "near_miss" in kinds or "rejected_prefilter" in kinds
    # Prefilter mid-band present if cap allows
    assert any(
        r.get("kind") == "rejected_prefilter" or "prefilter" in str(r.get("rejected_at_stage") or "")
        for r in collect_near_miss_candidates(cfg, [], max_n=8)
    )


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


def test_build_chain_form_continuity_and_ev_split_fields():
    """PR3: additive chain keys from Recommendation (base_ev, pens, opposite side)."""
    rec = Recommendation(
        match="Milwaukee Brewers vs Colorado Rockies",
        selection="Handikap 2-veis -2.5: Colorado Rockies +2.5",
        decimal_odds=1.75,
        stake_nok=10.0,
        ev=0.032,
        grade="B",
        odds_band="1.70-1.85",
        sport="baseball",
        market_type="handicap",
        p_model=0.60,
        notes="thin public lean",
        form_continuity_reason=(
            "form_continuity: Opposite side of recent successful Milwaukee Brewers -1.5 "
            "— strong continuity penalty applied; weak flip justification — rejected"
        ),
        base_ev=0.014,
        explore_boost_applied=0.018,
        ranking_gap_hc=True,
        sort_ev=-0.021,
        market_key="baseball_handicap",
        evidence_path="evidence/milwaukee_brewers_vs_colorado_rockies_handikap.json",
        evidence_snapshot={
            "summary": "flip attempt",
            "opposite_side_check": {
                "one_liner": "Brewers -1.5 already hit; Rockies +2.5 is opposite side",
            },
            "grade": "B",
        },
        opposite_side_check_status="evaluated",
        soft_demotion_reason=(
            "similar to recent baseball_handicap – demoted (1 in last 12); "
            "lessons_soft: baseball_handicap (research_process_miss); "
            "form_continuity: Opposite side of recent successful Milwaukee Brewers -1.5 "
            "— strong continuity penalty applied; weak flip justification — rejected"
        ),
    )
    # Optional fields when present on dataclass (other ESR branches)
    try:
        rec.similar_recent_reason = (  # type: ignore[attr-defined]
            "similar to recent baseball_handicap – demoted (1 in last 12)"
        )
    except Exception:
        pass
    try:
        rec.lessons_soft_reason = (  # type: ignore[attr-defined]
            "lessons_soft: baseball_handicap (research_process_miss)"
        )
    except Exception:
        pass

    chain = build_chain_from_pick(rec, haircut=0.03, phase_id="1A")
    assert chain["kind"] == "pick"
    assert chain["form_continuity_reason"].startswith("form_continuity:")
    assert "lessons_soft" in chain["lessons_soft_reason"]
    assert "similar" in chain["similar_recent_reason"].lower()
    assert chain["base_ev"] is not None
    assert abs(float(chain["base_ev"]) - 0.014) < 1e-9
    assert abs(float(chain["explore_boost_applied"]) - 0.018) < 1e-9
    assert chain["ranking_gap_hc"] is True
    assert chain["sort_ev"] is not None
    assert abs(float(chain["sort_ev"]) + 0.021) < 1e-6
    opp = chain["opposite_side_check"]
    assert isinstance(opp, dict)
    assert "opposite" in str(opp.get("one_liner") or "").lower() or "Rockies" in str(
        opp.get("one_liner") or ""
    )
    # Deep pack present AND opposite_side_check present → no process flag
    assert chain.get("process") != "missing_opposite_side_check"


def test_missing_opposite_side_check_process_flag():
    """Deep pack path without opposite_side_check → process audit flag (not reject)."""
    rec = Recommendation(
        match="Alpha vs Beta",
        selection="Over 2.5",
        decimal_odds=2.05,
        stake_nok=12.0,
        ev=0.05,
        grade="B",
        odds_band="1.85-2.20",
        sport="football",
        market_type="total",
        p_model=0.55,
        notes="ok pack",
        evidence_path="evidence/alpha_over25.json",
        evidence_snapshot={"summary": "some edge", "grade": "B"},
        opposite_side_check_status="missing",
        base_ev=0.05,
        explore_boost_applied=0.0,
    )
    chain = build_chain_from_pick(rec, haircut=0.03)
    assert chain.get("process") == "missing_opposite_side_check"
    assert chain.get("opposite_side_check") is None
    # Not a reject — kind stays pick
    assert chain["kind"] == "pick"
    assert not chain.get("reject_reason")


def test_format_reasoning_md_always_emits_opposite_form_ev_diversity():
    """PLACE_THESE Reasoning always shows Opposite side / Form / EV split / Diversity."""
    rec = Recommendation(
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
        base_ev=0.032,
        explore_boost_applied=0.018,
        form_continuity_reason="",
        sort_ev=0.040,
        market_key="football_btts",
        soft_demotion_reason=(
            "similar to recent football_btts – demoted (1 in last 10); "
            "lessons_soft: football_btts (caution)"
        ),
    )
    chain = build_chain_from_pick(rec, haircut=0.03, phase_id="1A")
    md = format_reasoning_md([chain])
    assert "## Reasoning" in md
    assert "**Opposite side:**" in md
    assert "not evaluated" in md  # default when missing
    assert "**Form continuity:**" in md
    assert "**EV split:**" in md
    assert "base_ev=" in md
    assert "explore_boost=" in md
    assert "placed_ev=" in md
    assert "+0.018" in md or "explore_boost=+0.018" in md
    assert "**Diversity:**" in md
    assert "sort_ev=" in md
    assert "penalties:" in md
    # All three soft pen slots present
    assert "similar" in md.lower()
    assert "lessons" in md.lower()
    assert "form_continuity" in md.lower()


def test_format_md_explore_withheld_and_form_continuity_text():
    rec = Recommendation(
        match="A vs B",
        selection="A -1.5",
        decimal_odds=1.85,
        stake_nok=10.0,
        ev=0.01,
        grade="B",
        odds_band="1.70-1.85",
        sport="baseball",
        market_type="handicap",
        p_model=0.55,
        notes="thin",
        base_ev=0.004,
        explore_boost_applied=0.0,
        form_continuity_reason="form_continuity: Opposite side of recent successful A -1.5 — demoted",
        sort_ev=-0.02,
    )
    chain = build_chain_from_pick(rec, haircut=0.03)
    md = format_reasoning_md([chain])
    assert "explore_boost=withheld" in md
    assert "base_ev=+0.004" in md
    assert "form_continuity: Opposite side" in md
    assert "not evaluated" in md


def test_near_miss_form_continuity_fields_and_process():
    """form_continuity rejects and missing opposite-side process flag on near-miss."""
    row = {
        "match": "Milwaukee Brewers vs Colorado Rockies",
        "selection": "Handikap 2-veis -2.5: Colorado Rockies +2.5",
        "reason": (
            "form_continuity: Opposite side of recent successful Milwaukee Brewers -1.5 "
            "— strong continuity penalty applied; weak flip justification — rejected"
        ),
        "ev": 0.02,
        "base_ev": 0.02,
        "sort_ev": -0.04,
        "odds": 1.75,
        "p_model": 0.58,
        "grade": "B",
        "sport": "baseball",
        "near_miss": True,
        "form_continuity": True,
        "evidence_path": "evidence/rockies_plus25.json",
    }
    chain = build_chain_from_near_miss(row, haircut=0.03, phase_id="1A")
    assert chain["kind"] == "near_miss"
    assert chain["form_continuity_reason"].startswith("form_continuity:")
    assert chain.get("form_continuity") is True
    assert chain["base_ev"] is not None
    assert abs(float(chain["base_ev"]) - 0.02) < 1e-9
    assert chain.get("process") == "missing_opposite_side_check"

    md = format_reasoning_md([chain])
    assert "## Near-miss / Rejected" in md
    assert "form_continuity" in md
    assert "process: missing_opposite_side_check" in md or "Rockies" in md


def test_soft_demotion_reason_split_into_pen_slots():
    """When only soft_demotion_reason is set, Diversity slots still classify pens."""
    pick = {
        "match": "X vs Y",
        "selection": "Over 3.5",
        "decimal_odds": 2.10,
        "stake_nok": 12,
        "ev": 0.04,
        "grade": "B",
        "sport": "football",
        "market_type": "total",
        "market_key": "football_totals_over",
        "p_model": 0.52,
        "notes": "edge",
        "base_ev": 0.04,
        "explore_boost_applied": 0.0,
        "sort_ev": 0.02,
        "soft_demotion_reason": (
            "similar to recent football_totals_over – demoted (2 in last 12); "
            "lessons_soft: football_totals_over (caution); "
            "form_continuity: Opposite side of recent successful X -1.5 — caution"
        ),
    }
    chain = build_chain_from_pick(pick, haircut=0.03)
    assert "similar" in chain["similar_recent_reason"].lower()
    assert "lessons_soft" in chain["lessons_soft_reason"]
    assert chain["form_continuity_reason"].startswith("form_continuity:")
    md = format_reasoning_md([chain])
    assert "penalties:" in md
    # All three named in Diversity line
    assert "similar to recent" in md
    assert "lessons_soft" in md
    assert "form_continuity:" in md
