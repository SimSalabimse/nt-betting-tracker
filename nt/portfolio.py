from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nt.bets_io import band_roi_stats, odds_band
from nt.evidence import ev_after_haircut, grade_evidence


@dataclass
class Candidate:
    date: str
    match: str
    selection: str
    decimal_odds: float
    sport: str = ""
    market_type: str = ""
    p_model: float | None = None
    evidence: dict[str, Any] | None = None
    evidence_key: str = ""
    notes: str = ""


@dataclass
class Recommendation:
    match: str
    selection: str
    decimal_odds: float
    stake_nok: float
    ev: float
    grade: str
    odds_band: str
    sport: str
    market_type: str
    p_model: float
    notes: str
    high_odds: bool = False
    reject_reason: str = ""


def _stake_for(
    phase: dict[str, Any],
    remaining_risk: float,
    min_stake: float,
    high_odds: bool,
    stake_mult: float,
    ev: float,
) -> float:
    lo = float(phase["stake_min"])
    hi = float(phase["stake_max"])
    # Scale within band by EV strength (simple, not full Kelly)
    frac = min(1.0, max(0.0, (ev - 0.03) / 0.12))
    stake = lo + frac * (hi - lo)
    if high_odds:
        stake *= stake_mult
    stake = max(min_stake, min(hi, stake))
    stake = min(stake, remaining_risk)
    # NT: whole kroner preferred
    stake = max(min_stake, float(int(round(stake))))
    if stake > remaining_risk:
        stake = float(int(remaining_risk))
    if stake < min_stake:
        return 0.0
    return stake


def build_portfolio(
    cfg: dict[str, Any],
    candidates: list[Candidate],
    phase: dict[str, Any],
    risk: dict[str, Any],
    historical_rows: list[dict[str, str]],
) -> tuple[list[Recommendation], list[dict[str, Any]]]:
    """
    Score candidates, enforce risk/phase, ALLOW high odds when evidence supports.

    High odds (> high_odds_threshold) are NOT banned. They require:
    - grade A evidence
    - higher min EV
    - reduced stake multiplier
    - optional extra EV if historical band ROI is bad
    """
    sel = cfg["selection"]
    min_stake = float(cfg["norsk_tipping"]["min_stake_nok"])
    thr = float(sel["high_odds_threshold"])
    haircut = float(sel["probability_haircut"])
    band_stats = band_roi_stats(historical_rows)
    band_cfg = sel.get("band_penalty", {})
    priors = sel.get("band_prior_boost", {})

    rejects: list[dict[str, Any]] = []
    scored: list[Recommendation] = []

    if not risk.get("can_bet"):
        return [], [{"reason": "risk block", "detail": risk.get("reasons")}]

    remaining = float(risk["remaining_risk_nok"])
    max_bets = int(phase["max_bets_per_round"])
    high_odds_count = 0
    max_high = int(sel.get("high_odds_max_per_round", 2))

    for c in candidates:
        odds = float(c.decimal_odds)
        band = odds_band(odds)
        high = odds >= thr
        grade, issues = grade_evidence(c.evidence, cfg, odds)

        p_model = c.p_model
        if p_model is None and c.evidence and c.evidence.get("p_model") is not None:
            p_model = float(c.evidence["p_model"])
        if p_model is None:
            rejects.append(
                {
                    "match": c.match,
                    "selection": c.selection,
                    "reason": "no p_model",
                    "grade": grade,
                    "issues": issues,
                }
            )
            continue

        ev = ev_after_haircut(p_model, odds, haircut)
        # soft prior from this book's band ROI history
        ev += float(priors.get(band, 0.0))

        min_ev = float(sel["standard_min_ev"])
        if high:
            min_ev = float(sel["high_odds_min_ev"])
            need_grade = str(sel["high_odds_min_grade"]).upper()
            if grade > need_grade or grade == "F" or (need_grade == "A" and grade != "A"):
                # grades A < B < C < F lexicographically wrong — explicit check
                if grade != "A":
                    rejects.append(
                        {
                            "match": c.match,
                            "selection": c.selection,
                            "odds": odds,
                            "reason": f"high odds {odds} requires grade A (got {grade})",
                            "issues": issues,
                            "ev": round(ev, 4),
                        }
                    )
                    continue
            if high_odds_count >= max_high:
                rejects.append(
                    {
                        "match": c.match,
                        "selection": c.selection,
                        "reason": f"high-odds slot full ({max_high}/round)",
                    }
                )
                continue

        # Historical band penalty
        st = band_stats.get(band)
        if st and st["n"] >= float(band_cfg.get("min_sample", 15)):
            if st["roi"] < float(band_cfg.get("bad_roi_below", -0.10)):
                min_ev += float(band_cfg.get("extra_ev_required", 0.05))

        if ev < min_ev:
            rejects.append(
                {
                    "match": c.match,
                    "selection": c.selection,
                    "odds": odds,
                    "reason": f"EV {ev:.3f} < min {min_ev:.3f}",
                    "grade": grade,
                    "high_odds": high,
                }
            )
            continue

        # Standard bets need at least grade B (structured evidence). High odds already require A.
        if grade in ("F", "C") and not high:
            rejects.append(
                {
                    "match": c.match,
                    "selection": c.selection,
                    "reason": f"evidence grade {grade} insufficient (need B+)",
                    "issues": issues,
                }
            )
            continue
        if grade == "F":
            rejects.append(
                {
                    "match": c.match,
                    "selection": c.selection,
                    "reason": "evidence grade F",
                    "issues": issues,
                }
            )
            continue

        stake = _stake_for(
            phase,
            remaining,
            min_stake,
            high,
            float(sel["high_odds_stake_multiplier"]),
            ev,
        )
        if stake < min_stake:
            rejects.append(
                {
                    "match": c.match,
                    "selection": c.selection,
                    "reason": "insufficient remaining risk for min stake",
                }
            )
            continue

        note_bits = []
        if high:
            note_bits.append(f"HIGH_ODDS grade={grade}")
        note_bits.append(f"EV={ev:.3f}")
        if c.notes:
            note_bits.append(c.notes[:120])

        scored.append(
            Recommendation(
                match=c.match,
                selection=c.selection,
                decimal_odds=odds,
                stake_nok=stake,
                ev=round(ev, 4),
                grade=grade,
                odds_band=band,
                sport=c.sport or "",
                market_type=c.market_type or "",
                p_model=p_model,
                notes="; ".join(note_bits)[:400],
                high_odds=high,
            )
        )

    # Sort by EV desc and fill portfolio
    scored.sort(key=lambda r: r.ev, reverse=True)
    picked: list[Recommendation] = []
    remaining = float(risk["remaining_risk_nok"])
    high_odds_count = 0
    used_matches: set[str] = set()

    for rec in scored:
        if len(picked) >= max_bets:
            break
        if remaining < min_stake:
            break
        # soft diversification: max 2 per match
        mcount = sum(1 for p in picked if p.match == rec.match)
        if mcount >= 2:
            rejects.append(
                {"match": rec.match, "selection": rec.selection, "reason": "max 2 per match"}
            )
            continue
        if rec.high_odds and high_odds_count >= max_high:
            continue
        stake = min(rec.stake_nok, remaining)
        stake = float(int(stake))
        if stake < min_stake:
            continue
        rec.stake_nok = stake
        picked.append(rec)
        remaining = round(remaining - stake, 2)
        if rec.high_odds:
            high_odds_count += 1
        used_matches.add(rec.match)

    return picked, rejects
