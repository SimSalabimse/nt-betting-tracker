from __future__ import annotations

"""
Multi-leg / combo policy helpers.

Singles remain default. Combos are gated by phase max_doubles, config combos.*,
per-leg quality, and correlation scoring. Never bypasses portfolio EV/grade rules.
"""

from dataclasses import dataclass, field
from typing import Any

from nt.defaults import combos_cfg
from nt.evidence import ev_after_haircut


@dataclass
class ComboLeg:
    match: str
    selection: str
    decimal_odds: float
    p_model: float
    grade: str
    sport: str = ""
    market_type: str = ""
    league: str = ""
    team_tags: list[str] = field(default_factory=list)
    high_odds: bool = False
    ev: float = 0.0


@dataclass
class ComboAssessment:
    ok: bool
    reasons: list[str]
    n_legs: int
    combined_odds: float
    p_joint: float
    ev: float
    correlation_score: float
    recommended_stake_mult: float
    stake_nok: float = 0.0


def _grade_rank(g: str) -> int:
    return {"A": 4, "B": 3, "C": 2, "F": 1}.get((g or "").upper(), 0)


def _teams_from_match(match: str) -> list[str]:
    m = (match or "").lower()
    for sep in (" vs ", " v ", " - "):
        if sep in m:
            return [t.strip() for t in m.split(sep, 1) if t.strip()]
    return [m.strip()] if m.strip() else []


def correlation_score(legs: list[ComboLeg]) -> tuple[float, list[str]]:
    """
    Higher = more independent (better). Returns (score 0..1, notes).
    """
    notes: list[str] = []
    if len(legs) < 2:
        return 1.0, ["single leg"]

    score = 1.0
    matches = [(l.match or "").strip().lower() for l in legs]
    if len(set(matches)) < len(matches):
        return 0.0, ["hard reject: same match in multiple legs"]

    # shared team across different matches
    teams: list[str] = []
    for leg in legs:
        tags = leg.team_tags or _teams_from_match(leg.match)
        for t in tags:
            t = t.strip().lower()
            if t and t in teams:
                return 0.0, [f"hard reject: shared team '{t}'"]
            if t:
                teams.append(t)

    leagues = [(l.league or "").strip().lower() for l in legs if (l.league or "").strip()]
    if leagues and len(set(leagues)) == 1 and len(leagues) == len(legs):
        score -= 0.20
        notes.append("same league all legs (-0.20)")

    markets = [(l.market_type or "").strip().lower() for l in legs]
    if markets and len(set(markets)) == 1:
        score -= 0.10
        notes.append("same market family (-0.10)")

    sports = [(l.sport or "").strip().lower() for l in legs]
    if sports and len(set(sports)) == 1:
        score -= 0.05
        notes.append("same sport (-0.05)")
    else:
        score += 0.05
        notes.append("cross-sport diversification (+0.05)")

    score = max(0.0, min(1.0, score))
    notes.append(f"correlation_score={score:.2f}")
    return score, notes


def assess_combo(
    cfg: dict[str, Any],
    legs: list[ComboLeg],
    phase: dict[str, Any],
    *,
    haircut: float | None = None,
    remaining_risk: float | None = None,
    base_stake: float | None = None,
) -> ComboAssessment:
    """Validate multi-leg ticket against phase + combos policy."""
    cc = combos_cfg(cfg)
    reasons: list[str] = []
    n = len(legs)
    max_legs = int(cc.get("max_legs") or 3)
    thr = float((cfg.get("selection") or {}).get("high_odds_threshold", 2.5))
    haircut = float(
        haircut if haircut is not None else (cfg.get("selection") or {}).get("probability_haircut", 0.05)
    )
    min_grade = str(cc.get("min_leg_grade") or "B").upper()
    min_leg_ev = float(cc.get("min_leg_ev") or (cfg.get("selection") or {}).get("standard_min_ev", 0.03))

    if not cc.get("enabled"):
        return ComboAssessment(False, ["combos disabled in config"], n, 0.0, 0.0, 0.0, 0.0, 0.0)

    if n < 2:
        return ComboAssessment(False, ["need at least 2 legs"], n, 0.0, 0.0, 0.0, 0.0, 0.0)

    if n > max_legs:
        return ComboAssessment(False, [f"legs {n} > max_legs {max_legs}"], n, 0.0, 0.0, 0.0, 0.0, 0.0)

    max_doubles = int(phase.get("max_doubles_per_round") or 0)
    if max_doubles <= 0:
        return ComboAssessment(
            False, [f"phase {phase.get('phase_id')} max_doubles_per_round=0 (singles only)"], n, 0.0, 0.0, 0.0, 0.0, 0.0
        )

    if n >= 3:
        treble_min = str(cc.get("trebles_min_phase") or "4")
        order = list((cfg.get("phases") or {}).keys())
        pid = str(phase.get("phase_id") or "")
        if pid in order and treble_min in order:
            if order.index(pid) < order.index(treble_min):
                reasons.append(f"trebles require phase ≥ {treble_min} (at {pid})")
        aggr = str(cc.get("aggressiveness") or "conservative").lower()
        if aggr in ("off", "conservative"):
            reasons.append("trebles blocked under conservative/off aggressiveness")

    combined_odds = 1.0
    p_joint = 1.0
    for leg in legs:
        if leg.decimal_odds < 1.01:
            reasons.append(f"bad odds on {leg.match}")
            continue
        combined_odds *= float(leg.decimal_odds)
        p_adj = max(0.01, min(0.99, float(leg.p_model) - haircut))
        p_joint *= p_adj
        if _grade_rank(leg.grade) < _grade_rank(min_grade):
            reasons.append(f"leg grade {leg.grade} < min {min_grade}: {leg.selection}")
        high = leg.high_odds or (leg.decimal_odds >= thr)
        if high and not cc.get("allow_high_odds_legs"):
            reasons.append(f"high-odds leg not allowed in combos: {leg.selection}")
        ev_leg = leg.ev if leg.ev else ev_after_haircut(float(leg.p_model), float(leg.decimal_odds), haircut)
        if ev_leg < min_leg_ev:
            reasons.append(f"leg EV {ev_leg:.3f} < min {min_leg_ev:.3f}: {leg.selection}")

    corr, corr_notes = correlation_score(legs)
    min_corr = float(cc.get("min_correlation_score") or 0.55)
    if corr < min_corr:
        reasons.append(f"correlation_score {corr:.2f} < min {min_corr:.2f}")
    reasons.extend(corr_notes)

    ev = p_joint * combined_odds - 1.0
    stake_mult = float(cc.get("stake_multiplier") or 0.55)
    stake = 0.0
    if base_stake is not None:
        stake = float(int(round(base_stake * stake_mult)))
        lo = float(phase.get("stake_min") or 10)
        hi = float(phase.get("stake_max") or 12)
        stake = max(lo, min(hi, stake))
        if remaining_risk is not None:
            stake = min(stake, float(remaining_risk))
            stake = float(int(stake))

    ok = not any(
        r.startswith("hard reject")
        or r.startswith("combos disabled")
        or r.startswith("phase ")
        or r.startswith("need ")
        or r.startswith("legs ")
        or r.startswith("trebles")
        or r.startswith("leg grade")
        or r.startswith("high-odds")
        or r.startswith("leg EV")
        or r.startswith("correlation_score")
        or r.startswith("bad odds")
        for r in reasons
    )
    # tighten: if any reject-class reason above
    reject_prefixes = (
        "hard reject",
        "combos disabled",
        "phase ",
        "need ",
        "legs ",
        "trebles",
        "leg grade",
        "high-odds",
        "leg EV",
        "correlation_score",
        "bad odds",
    )
    ok = not any(any(r.startswith(p) for p in reject_prefixes) for r in reasons) and n >= 2 and corr >= min_corr

    if ok:
        reasons.insert(0, f"OK combo n={n} odds={combined_odds:.2f} EV={ev:.3f}")

    return ComboAssessment(
        ok=ok,
        reasons=reasons,
        n_legs=n,
        combined_odds=round(combined_odds, 4),
        p_joint=round(p_joint, 6),
        ev=round(ev, 4),
        correlation_score=round(corr, 4),
        recommended_stake_mult=stake_mult,
        stake_nok=stake,
    )


def format_combo_selection(legs: list[ComboLeg]) -> str:
    return " + ".join(f"{l.selection}" for l in legs)


def format_combo_match(legs: list[ComboLeg]) -> str:
    return " | ".join(l.match for l in legs)


def combo_policy_summary(cfg: dict[str, Any], phase: dict[str, Any] | None = None) -> dict[str, Any]:
    cc = combos_cfg(cfg)
    return {
        "enabled": bool(cc.get("enabled")),
        "aggressiveness": cc.get("aggressiveness"),
        "stake_multiplier": cc.get("stake_multiplier"),
        "min_correlation_score": cc.get("min_correlation_score"),
        "allow_high_odds_legs": cc.get("allow_high_odds_legs"),
        "max_legs": cc.get("max_legs"),
        "phase_max_doubles": (phase or {}).get("max_doubles_per_round"),
        "phase_id": (phase or {}).get("phase_id"),
        "default_recommendation": "singles",
    }
