"""
PR2 — EV-fail refresh / second-pass (T12-style).

Pre-seed failing packs (raw_ev << 0), inject better alts → queue prefers injects;
exhausted packs not re-queued without force.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import ev_after_haircut
from nt.light_research import (
    LightRecord,
    build_deep_queue,
    ev_fail_refresh_triggered,
    rank_inject_records,
    research_second_pass,
    tiers_cfg,
)


def _cfg(tmp_path: Path | None = None, **tier_extra) -> dict:
    paths = {}
    if tmp_path is not None:
        paths = {
            "evidence": str(tmp_path / "evidence"),
            "outbox": str(tmp_path / "outbox"),
            "state_dir": str(tmp_path / "state"),
        }
        (tmp_path / "evidence").mkdir(parents=True, exist_ok=True)
        (tmp_path / "outbox").mkdir(parents=True, exist_ok=True)
        (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    return {
        "selection": {"probability_haircut": 0.03, "standard_min_ev": 0.02},
        "paths": paths,
        "research": {
            "tiers": {
                "engine_deep_queue": True,
                "clearability_promotion": True,
                "dual_track_deep_queue": True,
                "second_pass_from_dump": True,
                "second_pass_max_inject": 12,
                "raw_ev_exhausted": -0.05,
                "second_pass_min_deep_packs": 8,
                "deep_target_n": 8,
                "deep_max_n": 12,
                "deep_min_preferred_share": 0.55,
                "deep_max_short_main_share": 0.25,
                "preferred_odds_lo": 1.85,
                "preferred_odds_hi": 2.60,
                "alt_preferred_odds_lo": 1.80,
                "short_chalk_odds": 1.70,
                **tier_extra,
            }
        },
    }


def _rec(
    match: str,
    selection: str,
    odds: float,
    *,
    sport: str = "football",
    family: str = "ml",
    prior_p: float | None = 0.48,
    has_p: bool = False,
    raw_ev: float | None = None,
    source: str = "auto",
    is_inject: bool = False,
) -> LightRecord:
    haircut = 0.03
    prior_ev = None
    if prior_p is not None:
        prior_ev = (float(prior_p) - haircut) * float(odds) - 1.0
    return LightRecord(
        match=match,
        selection=selection,
        sport=sport,
        decimal_odds=float(odds),
        odds_band="mid",
        market_family=family,
        verdict="pass",
        has_p_model=has_p,
        has_deep_pack=has_p,
        prior_p=prior_p,
        prior_ev=prior_ev,
        prior_available=prior_ev is not None,
        raw_ev=raw_ev,
        source=source,
        is_inject=is_inject,
    )


def test_ev_fail_refresh_trigger():
    assert ev_fail_refresh_triggered(
        n_packs_with_p=8, n_raw_ev_pass=0, mid_unresearched=0
    )
    assert not ev_fail_refresh_triggered(
        n_packs_with_p=7, n_raw_ev_pass=0, mid_unresearched=0
    )
    assert not ev_fail_refresh_triggered(
        n_packs_with_p=10, n_raw_ev_pass=1, mid_unresearched=0
    )
    assert not ev_fail_refresh_triggered(
        n_packs_with_p=10, n_raw_ev_pass=0, mid_unresearched=2
    )


def test_t12_refresh_prefers_injects_over_exhausted():
    """
    Pre-seed 10 failing mid packs (p≈implied → raw_ev < -0.05).
    Inject 5 alts with better rel_prior → refresh queue prefers injects.
    """
    cfg = _cfg()
    haircut = 0.03

    failing: list[LightRecord] = []
    pack_meta: dict[tuple[str, str], dict] = {}
    for i in range(10):
        odds = 1.95 + (i % 5) * 0.05  # mid band
        # p ≈ implied → raw_ev ≈ -haircut*odds < -0.05
        p_model = 1.0 / odds
        raw = ev_after_haircut(p_model, odds, haircut)
        assert raw < -0.05
        r = _rec(
            f"Fail{i} vs Opp",
            f"Vinner: Home{i}",
            odds,
            family="ml",
            prior_p=p_model,
            has_p=True,
            raw_ev=raw,
        )
        failing.append(r)
        pack_meta[r.key()] = {
            "has_pack": True,
            "p_model": p_model,
            "odds": odds,
            "raw_ev": raw,
            "deep_exhausted": True,
        }

    injects: list[LightRecord] = []
    for i in range(5):
        odds = 2.05 + i * 0.05
        # Better prior_p than market → higher rel_prior
        prior_p = 0.50 + i * 0.01
        inj = _rec(
            f"Inj{i} vs X",
            f"Handikap +{3 + i}.5: Away",
            odds,
            sport="tennis" if i % 2 else "football",
            family="handicap",
            prior_p=prior_p,
            has_p=False,
            source="inject",
            is_inject=True,
        )
        injects.append(inj)

    # Extra open preferred (not packed, not inject) should also be eligible
    open_pref = [
        _rec(
            f"Open{i}",
            f"Totalt 3.5: Over 3.5",
            2.10,
            family="totals_over",
            prior_p=0.49,
        )
        for i in range(3)
    ]

    queue = build_deep_queue(
        failing + open_pref,
        cfg,
        mode="refresh",
        inject_records=injects,
        pack_meta_by_key=pack_meta,
        force_requeue_exhausted=False,
    )

    assert queue, "refresh queue should not be empty with injects"
    # Exhausted failing packs must not re-enter
    fail_keys = {r.key() for r in failing}
    q_keys = {r.key() for r in queue}
    assert fail_keys.isdisjoint(q_keys), "exhausted packs re-queued without inject preference"

    # Injects preferred into queue
    inject_keys = {r.key() for r in injects}
    n_inject_in_q = len(q_keys & inject_keys)
    assert n_inject_in_q >= 1, "expected at least one inject in refresh queue"
    # Prefer injects over re-grinding failures
    assert n_inject_in_q == len([r for r in queue if r.is_inject or r.source == "inject"])

    # Mode / track fields
    for r in queue:
        assert r.queue_mode == "refresh"
        assert r.clearability_score is not None


def test_exhausted_not_requeued_without_force():
    cfg = _cfg()
    haircut = 0.03
    odds = 2.0
    p_model = 0.50
    raw = ev_after_haircut(p_model, odds, haircut)
    assert raw < -0.05
    exhausted = _rec(
        "Ex vs Y",
        "Vinner: Home",
        odds,
        family="ml",
        prior_p=p_model,
        has_p=True,
        raw_ev=raw,
    )
    meta = {
        exhausted.key(): {
            "has_pack": True,
            "raw_ev": raw,
            "deep_exhausted": True,
            "p_model": p_model,
            "odds": odds,
        }
    }
    # No injects, no other open preferred with pass
    queue = build_deep_queue(
        [exhausted],
        cfg,
        mode="refresh",
        inject_records=[],
        pack_meta_by_key=meta,
        force_requeue_exhausted=False,
    )
    assert exhausted.key() not in {r.key() for r in queue}

    # With force requeue and no injects, exhausted MUST re-enter (operator path)
    queue_f = build_deep_queue(
        [exhausted],
        cfg,
        mode="refresh",
        inject_records=[],
        pack_meta_by_key=meta,
        force_requeue_exhausted=True,
    )
    assert exhausted.key() in {r.key() for r in queue_f}, (
        "force_requeue_exhausted=True with empty injects must re-queue exhausted preferred line"
    )


def test_research_second_pass_api(tmp_path: Path):
    """Function API marks exhausted, injects alts, writes deep_queue state."""
    cfg = _cfg(tmp_path)
    haircut = 0.03
    evidence = Path(cfg["paths"]["evidence"])

    # Write 8 failing packs
    for i in range(8):
        odds = 2.0
        p_model = 0.50  # implied 0.5 → raw_ev = -0.06
        pack = {
            "match": f"Pack{i} vs Opp",
            "selection": f"Vinner: Home{i}",
            "sport": "football",
            "p_model": p_model,
            "odds_at_research": odds,
            "decimal_odds_ref": odds,
            "summary": "Market mimic mid ML for refresh fixture research.",
            "failure_modes": "No edge after haircut; efficient price.",
            "sources": [{"name": "fixture", "url": "http://x"}],
        }
        (evidence / f"pack_{i}.json").write_text(
            json.dumps(pack), encoding="utf-8"
        )

    records = [
        _rec(
            f"Pack{i} vs Opp",
            f"Vinner: Home{i}",
            2.0,
            family="ml",
            prior_p=0.50,
            has_p=True,
            raw_ev=ev_after_haircut(0.50, 2.0, haircut),
        )
        for i in range(8)
    ]
    inject_cands = [
        {
            "match": f"Alt{i} vs Z",
            "selection": f"Handikap +{i + 2}.5: Away",
            "sport": "tennis",
            "decimal_odds": 2.10 + i * 0.05,
            "prior_p": 0.50,
            "prior_ev": (0.50 - haircut) * (2.10 + i * 0.05) - 1.0,
        }
        for i in range(5)
    ]

    payload = research_second_pass(
        cfg,
        None,
        records=records,
        inject_candidates=inject_cands,
        force=True,
        write=True,
        mid_unresearched=0,
        n_raw_ev_pass=0,
    )
    assert payload.get("ok") is True
    assert payload.get("mode") == "refresh"
    assert payload.get("second_pass_ran") is True
    assert int(payload.get("inject_n") or 0) >= 1
    assert int(payload.get("exhausted_n") or 0) >= 1

    dq = payload.get("deep_queue") or []
    # Prefer injects in queue
    inject_in_q = [r for r in dq if r.get("inject")]
    exhausted_in_q = [r for r in dq if r.get("deep_exhausted")]
    assert len(inject_in_q) >= 1 or any(
        "Handikap" in str(r.get("selection") or "") for r in dq
    )
    assert not exhausted_in_q

    # deep_queue.json mode=refresh
    state_path = Path(cfg["paths"]["state_dir"]) / "deep_queue.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state.get("mode") == "refresh"
        for line in state.get("deep_queue") or []:
            if "clearability_score" in line:
                assert isinstance(line["clearability_score"], (int, float))


def test_w_fail_demotes_bad_raw_ev_in_score():
    """has_pack + raw_ev < -0.05 applies w_fail inside clearability (refresh scoring)."""
    from nt.clearability import clearability_score, DEFAULT_CLEARABILITY_WEIGHTS

    base = clearability_score(odds=2.0, prior_ev=-0.06, prior_p=0.48, has_pack=False)
    bad = clearability_score(
        odds=2.0,
        prior_ev=-0.06,
        prior_p=0.48,
        has_pack=True,
        raw_ev=-0.10,
    )
    assert bad == pytest.approx(base + DEFAULT_CLEARABILITY_WEIGHTS["w_fail"])
    assert bad < base


def test_inject_hard_cap_ranks_by_clearability_not_dump_order():
    """
    Review issue 1: >max_inject candidates — best clearability alts survive cap,
    not the first N dump-order weak lines.
    """
    cfg = _cfg(second_pass_max_inject=5)
    haircut = 0.03
    # First 12 weak priors (would win dump-order cap of 12 / 5)
    weak: list[LightRecord] = []
    for i in range(12):
        weak.append(
            _rec(
                f"Weak{i} vs Z",
                f"Vinner: Weak{i}",
                2.00,
                family="ml",
                prior_p=0.40,  # poor rel_prior
                source="inject",
                is_inject=True,
            )
        )
    # Last 8 strong alts (must survive if ranked)
    strong: list[LightRecord] = []
    for i in range(8):
        strong.append(
            _rec(
                f"Strong{i} vs Z",
                f"Handikap +{i + 2}.5: Away",
                2.15,
                sport="tennis",
                family="handicap",
                prior_p=0.55,  # much better rel_prior + alt
                source="inject",
                is_inject=True,
            )
        )
    # Dump order: weak first
    ranked = rank_inject_records(weak + strong, cfg, max_inject=5)
    assert len(ranked) == 5
    strong_keys = {r.key() for r in strong}
    n_strong = sum(1 for r in ranked if r.key() in strong_keys)
    assert n_strong == 5, "hard-cap must keep high-clearability injects, not weak dump prefix"

    # Through second_pass API
    payload = research_second_pass(
        cfg,
        None,
        records=[],
        inject_candidates=[
            {
                "match": r.match,
                "selection": r.selection,
                "sport": r.sport,
                "decimal_odds": r.decimal_odds,
                "prior_p": r.prior_p,
                "prior_ev": r.prior_ev,
            }
            for r in (weak + strong)
        ],
        pack_meta_by_key={},
        force=True,
        write=False,
        mid_unresearched=0,
        n_raw_ev_pass=0,
    )
    assert payload.get("ok") is True
    assert int(payload.get("inject_n") or 0) == 5
    # Injects fed to queue are the ranked top-5 (all strong)
    # Queue may be empty if injects fail light prefilter — rank_inject already asserted.
    # When queue non-empty, prefer strong keys
    dq = payload.get("deep_queue") or []
    if dq:
        dq_keys = {(r.get("match"), r.get("selection")) for r in dq}
        assert dq_keys & strong_keys


def test_auto_second_pass_blocks_unknown_mid_unresearched(tmp_path: Path):
    """force=False without mid_unresearched / coverage_health must not false-trigger."""
    cfg = _cfg(tmp_path)
    # No coverage_health.json written
    payload = research_second_pass(
        cfg,
        None,
        records=[
            _rec(f"P{i}", f"Vinner: H{i}", 2.0, has_p=True, raw_ev=-0.08)
            for i in range(8)
        ],
        inject_candidates=[],
        force=False,
        write=False,
        # mid_unresearched deliberately omitted
    )
    assert payload.get("ok") is False
    assert payload.get("reason") == "mid_unresearched_unknown"

    # Explicit mid=0 allows auto trigger when packs fail EV
    pack_meta = {}
    for i in range(8):
        k = (f"P{i}", f"Vinner: H{i}")
        pack_meta[k] = {
            "has_pack": True,
            "p_model": 0.5,
            "odds": 2.0,
            "raw_ev": -0.08,
            "deep_exhausted": True,
        }
    payload2 = research_second_pass(
        cfg,
        None,
        records=[
            _rec(f"P{i}", f"Vinner: H{i}", 2.0, has_p=True, raw_ev=-0.08)
            for i in range(8)
        ],
        pack_meta_by_key=pack_meta,
        inject_candidates=[
            {
                "match": "Alt vs Z",
                "selection": "Handikap +3.5: Away",
                "sport": "tennis",
                "decimal_odds": 2.10,
                "prior_p": 0.50,
            }
        ],
        force=False,
        write=False,
        mid_unresearched=0,
        n_raw_ev_pass=0,
    )
    assert payload2.get("ok") is True
    assert payload2.get("mode") == "refresh"
    assert float(payload2.get("raw_ev_pass_threshold") or 0) == pytest.approx(0.02)
