from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nt.bets_io import band_roi_stats, odds_band
from nt.evidence import (
    ev_after_haircut,
    grade_evidence,
    has_core_reason,
    is_strong_confidence,
    normalize_sources,
)
from nt.sport_taxonomy import normalize_sport


@dataclass
class Candidate:
    date: str  # match calendar date (YYYY-MM-DD) from kickoff when known — not place date
    match: str
    selection: str
    decimal_odds: float
    sport: str = ""
    market_type: str = ""
    p_model: float | None = None
    evidence: dict[str, Any] | None = None
    evidence_key: str = ""
    evidence_path: str = ""  # relative/absolute path of attached pack (forensic hard-link)
    notes: str = ""
    kickoff: str = ""  # "YYYY-MM-DD HH:MM" CEST when parsed from odds dump


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
    explore: bool = False
    learning_stake_mult: float = 1.0
    learning_ev_boost: float = 0.0
    market_key: str = ""
    reasons: list = field(default_factory=list)
    evidence_path: str = ""
    match_date: str = ""  # kickoff calendar date YYYY-MM-DD (CEST); empty → place-day fallback
    kickoff: str = ""
    # Phase 2.3: structured capital_v2 stake decision (in-memory; not JSONL yet)
    stake_decision: dict[str, Any] | None = None
    # P1 soft correlation keys
    league_key: str = "unknown"
    script_family: str = "other"


def _stake_for(
    phase: dict[str, Any],
    remaining_risk: float,
    min_stake: float,
    high_odds: bool,
    high_odds_mult: float,
    learning_stake_mult: float,
    ev: float,
) -> float:
    """Legacy phase band EV-scale sizing (capital_v2.enabled=false only)."""
    lo = float(phase["stake_min"])
    hi = float(phase["stake_max"])
    # Scale within band by EV strength (simple, not full Kelly)
    frac = min(1.0, max(0.0, (ev - 0.03) / 0.12))
    stake = lo + frac * (hi - lo)
    if high_odds:
        stake *= high_odds_mult
    # Ledger learning: sport/market form scales stake (clamped upstream)
    stake *= max(0.5, float(learning_stake_mult or 1.0))
    stake = max(min_stake, min(hi, stake))
    stake = min(stake, remaining_risk)
    # NT: whole kroner preferred
    stake = max(min_stake, float(int(round(stake))))
    if stake > remaining_risk:
        stake = float(int(remaining_risk))
    if stake < min_stake:
        return 0.0
    return stake


def _capital_v2_enabled(cfg: dict[str, Any]) -> bool:
    from nt.capital_v2 import capital_v2_cfg

    return bool(capital_v2_cfg(cfg).get("enabled"))


def _stake_for_capital_v2(
    cfg: dict[str, Any],
    risk: dict[str, Any],
    *,
    remaining_risk: float,
    min_stake: float,
    high_odds: bool,
    high_odds_mult: float,
    learning_stake_mult: float,
    ev: float,
    p_model: float,
    odds: float,
    match: str,
    selection: str,
    grade: str = "B",
    high_confidence: bool = False,
) -> tuple[float, dict[str, Any]]:
    """
    Unit-ladder sizing when capital_v2.enabled.
    Returns (final_stake, stake_decision_dict).
    High-Volume v2: grade_mult scales unit (C 1.0 · B 1.4 · A 2.0/2.2).
    """
    from nt.capital_v2 import (
        RULE_BUNDLE_VERSION,
        active_unit_for_mode,
        capital_v2_cfg,
        compute_unit_stake,
        grade_stake_multiplier,
        unit_size,
    )

    v2 = capital_v2_cfg(cfg)
    floor = float(v2.get("min_stake_nok") or min_stake)
    size_mode = str(risk.get("size_mode") or "NORMAL")
    if risk.get("stopped") or not risk.get("can_bet", True):
        size_mode = "FROZEN"

    unit = risk.get("unit_size_nok")
    if unit is None:
        liq = risk.get("riskable_liquid_nok")
        if liq is None:
            liq = risk.get("working_equity_nok") or remaining_risk
        unit = unit_size(float(liq), v2)
    unit = float(unit)
    g_mult = grade_stake_multiplier(
        grade, high_confidence=high_confidence, v2=v2
    )

    decision = compute_unit_stake(
        size_mode=size_mode,
        unit_size_nok=unit,
        remaining_room_nok=float(remaining_risk),
        min_stake=floor,
        stopped=bool(risk.get("stopped")),
        can_bet=bool(risk.get("can_bet", True)),
        high_odds=high_odds,
        high_odds_mult=float(high_odds_mult),
        learning_stake_mult=float(learning_stake_mult or 1.0),
        grade_mult=float(g_mult),
        match=match,
        selection=selection,
        rule_bundle_version=str(v2.get("rule_bundle_version") or RULE_BUNDLE_VERSION),
        inputs={
            "equity": risk.get("equity_nok"),
            "secure": risk.get("secure_nok"),
            "working_liquid": risk.get("riskable_liquid_nok"),
            "open_risk": risk.get("open_pending_risk_nok"),
            "dd_from_peak": risk.get("drawdown_from_peak"),
            "unit_size": unit,
            "size_mode": size_mode,
            "phase_id": risk.get("phase_id"),
            "p_model": p_model,
            "odds": odds,
            "ev": ev,
            "grade": grade,
            "grade_mult": g_mult,
            "learning_stake_mult": learning_stake_mult,
            "active_unit": active_unit_for_mode(unit, size_mode, floor),
            "remaining_room": remaining_risk,
        },
    )
    audit = decision.to_audit_dict()
    final = float(decision.final_stake_nok)

    # P2: optional fractional Kelly lift above unit (gated on liquid + Brier)
    try:
        from nt.kelly import fractional_kelly_stake

        kcfg = dict(v2.get("kelly") or {})
        if kcfg.get("enabled", True) and final >= floor:
            liq = float(
                risk.get("riskable_liquid_nok")
                or risk.get("working_equity_nok")
                or 0.0
            )
            active = float(decision.active_unit_nok or unit)
            cal_n, brier = 0, None
            try:
                from nt.calibrate import load_calibration_quality

                cq = load_calibration_quality(cfg)
                cal_n = int(cq.get("n") or 0)
                brier = cq.get("brier")
            except Exception:
                pass
            k_stake, k_notes = fractional_kelly_stake(
                p_model=float(p_model),
                odds=float(odds),
                liquid=liq,
                active_unit=active,
                min_stake=floor,
                remaining_room=float(remaining_risk),
                kelly_cfg=kcfg,
                brier=float(brier) if brier is not None else None,
                cal_n=cal_n,
            )
            cons = list(audit.get("constraints_applied") or [])
            cons.extend(k_notes)
            if k_stake is not None and k_stake > final + 1e-9:
                final = float(int(k_stake))
                audit["final_stake_nok"] = final
                audit["recommended_stake_nok"] = max(
                    float(audit.get("recommended_stake_nok") or 0), final
                )
                cons.append(f"kelly_applied:{final}")
            audit["constraints_applied"] = cons
            audit.setdefault("inputs", {})["kelly"] = {
                "stake": k_stake,
                "brier": brier,
                "cal_n": cal_n,
            }
    except Exception as ex:  # noqa: BLE001
        cons = list(audit.get("constraints_applied") or [])
        cons.append(f"kelly_error:{ex}")
        audit["constraints_applied"] = cons

    return final, audit


def rebalance_stakes(
    picked: list[Recommendation],
    budget: float,
    min_stake: float,
    max_stake: float,
    *,
    reserve_extra_seats: int = 0,
    max_stakes: list[float] | None = None,
) -> float:
    """
    Pack daily risk across the slip so we don't strand leftover under min_stake
    when more seats could still be filled.

    1) Seat every pick at min_stake (NT floor)
    2) Reserve ``reserve_extra_seats * min_stake`` for unfilled seats still possible
    3) Top up whole kroner to highest-EV picks (capped at max_stake or per-seat
       max_stakes for High-Volume grade mults) from *usable* only
    4) Return leftover kroner after packing (for multi-pass fill)

    Returns leftover budget not assigned to stakes (may fund another min seat).
    """
    if not picked:
        return float(budget)
    n = len(picked)
    budget = float(budget)
    min_stake = float(min_stake)
    max_stake = float(max_stake)
    if budget < min_stake:
        return budget
    # How many seats can this budget actually fund?
    max_seats = int(budget // min_stake)
    if max_seats < n:
        order = sorted(range(n), key=lambda i: picked[i].ev, reverse=True)
        keep = set(order[:max_seats])
        kept = [picked[i] for i in range(n) if i in keep]
        picked.clear()
        picked.extend(kept)
        n = len(picked)
        if max_stakes is not None and len(max_stakes) != n:
            max_stakes = None  # indices shifted — fall back to global cap
    if n == 0:
        return budget

    reserve = max(0, int(reserve_extra_seats)) * min_stake
    # Never reserve so much that current picks cannot sit at min_stake
    need = n * min_stake
    if budget - reserve < need:
        reserve = max(0.0, budget - need)
    usable = budget - reserve

    stakes = [min_stake] * n
    used = min_stake * n
    leftover_usable = usable - used
    order = sorted(range(n), key=lambda i: picked[i].ev, reverse=True)
    for i in order:
        seat_cap = max_stake
        if max_stakes is not None and i < len(max_stakes):
            seat_cap = min(max_stake, float(max_stakes[i]))
        seat_cap = max(min_stake, seat_cap)
        while leftover_usable >= 1.0 - 1e-9 and stakes[i] < seat_cap - 1e-9:
            stakes[i] += 1.0
            leftover_usable -= 1.0
    for i, s in enumerate(stakes):
        picked[i].stake_nok = float(int(s))
    # Total leftover = unused usable + reserved
    return round(leftover_usable + reserve, 2)


def build_portfolio(
    cfg: dict[str, Any],
    candidates: list[Candidate],
    phase: dict[str, Any],
    risk: dict[str, Any],
    historical_rows: list[dict[str, str]],
    learning: dict[str, Any] | None = None,
) -> tuple[list[Recommendation], list[dict[str, Any]]]:
    """
    Score candidates, enforce risk/phase, ALLOW high odds when evidence supports.

    High odds (> high_odds_threshold) are NOT banned. They require:
    - grade A evidence
    - higher min EV
    - reduced stake multiplier
    - optional extra EV if historical band ROI is bad

    Learning (optional): sport/market/band EV boosts + stake mults from ledger.
    """
    from nt.analytics import infer_market
    from nt.learning import diversification_limits, learning_adjustments, load_learning

    sel = cfg["selection"]
    min_stake = float(cfg["norsk_tipping"]["min_stake_nok"])
    thr = float(sel["high_odds_threshold"])
    haircut = float(sel["probability_haircut"])
    band_stats = band_roi_stats(historical_rows)
    band_cfg = sel.get("band_penalty", {})
    priors = sel.get("band_prior_boost", {})
    learn_cfg = cfg.get("learning") or {}
    learn_on = bool(learn_cfg.get("enabled", True))
    learn = learning if learning is not None else (load_learning(cfg) if learn_on else {})
    div_lim = diversification_limits(cfg)

    rejects: list[dict[str, Any]] = []
    scored: list[Recommendation] = []
    # per-call provisional Exploration weekly explore quota consumption while scoring
    build_portfolio._regime_explore_scored = 0  # type: ignore[attr-defined]

    if not risk.get("can_bet"):
        return [], [{"reason": "risk block", "detail": risk.get("reasons")}]
    if risk.get("research_only") or phase.get("research_only"):
        return [], [
            {
                "reason": "phase RESEARCH_ONLY",
                "detail": phase.get("process_health_reason")
                or risk.get("phase_health")
                or "process health blocks new risk",
            }
        ]

    remaining = float(risk["remaining_risk_nok"])
    max_bets = int(phase["max_bets_per_round"])
    high_odds_count = 0
    max_high = int(sel.get("high_odds_max_per_round", 2))
    high_odds_stress = bool(
        risk.get("high_odds_stress_block") or phase.get("high_odds_stress_block")
    )

    # Loss-streak discipline: after N consecutive losses, only grade A may be placed
    grade_a_only = False
    streak_lim = int((cfg.get("risk") or {}).get("loss_streak_grade_a_only", 3))
    if streak_lim > 0 and historical_rows:
        from nt.analytics import current_streak

        cur = current_streak(historical_rows)
        if cur.get("type") == "Loss" and int(cur.get("length") or 0) >= streak_lim:
            grade_a_only = True

    for c in candidates:
        odds = float(c.decimal_odds)
        band = odds_band(odds)
        high = odds >= thr
        grade, issues = grade_evidence(
            c.evidence,
            cfg,
            odds,
            selection=c.selection or "",
            sport=c.sport or "",
        )

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

        adj = learning_adjustments(
            learn,
            sport=c.sport or "",
            market=c.market_type or "",
            selection=c.selection or "",
            band=band,
            enabled=learn_on,
            learn_cfg=learn_cfg,
        )
        if adj.get("blocked"):
            rejects.append(
                {
                    "match": c.match,
                    "selection": c.selection,
                    "sport": c.sport,
                    "reason": adj.get("block_reason") or "learning soft-block",
                    "ev_boost": adj.get("ev_boost"),
                }
            )
            continue

        ev = ev_after_haircut(p_model, odds, haircut)
        # soft prior from config band table + live learning
        ev += float(priors.get(band, 0.0))
        ev += float(adj.get("ev_boost") or 0.0)

        # High-Volume v2 EV floors after haircut (+ soft boosts already applied)
        standard_floor = float(sel.get("standard_min_ev", 0.02))
        strong_floor = float(sel.get("strong_min_ev", 0.015))
        absolute_floor = float(sel.get("absolute_min_ev", 0.01))
        strong_n = int(sel.get("strong_min_sources", 8))
        strong = is_strong_confidence(c.evidence, grade, min_sources=strong_n)
        min_ev = strong_floor if strong else standard_floor
        # Thin sport/market explore path: lower EV bar so non-football can build sample
        if adj.get("explored"):
            min_ev = min(min_ev, float(div_lim.get("explore_min_ev", 0.012)))
        # Early-bankroll regime floor (Exploration 2% / Survival 3% under High-Volume v2)
        regime_floor = risk.get("regime_min_ev")
        if regime_floor is not None:
            try:
                min_ev = max(min_ev, float(regime_floor))
            except (TypeError, ValueError):
                pass
        # Exploration weekly quota: mid/alt unit bets may use thin EV band
        regime_explore = False
        if high:
            # Phase v5: concentration / poor calibration blocks high-odds entirely
            if high_odds_stress:
                rejects.append(
                    {
                        "match": c.match,
                        "selection": c.selection,
                        "odds": odds,
                        "reason": (
                            "phase_health: high_odds blocked "
                            "(concentration/calibration stress)"
                        ),
                        "grade": grade,
                        "ev": round(ev, 4),
                    }
                )
                continue
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

        # P1: process_error closed-loop temporary min_ev raise
        pg_raise = 0.0
        try:
            from nt.process_gates import process_gate_raise

            pg_raise = process_gate_raise(
                cfg,
                sport=c.sport or "",
                market_key=str(adj.get("market_key") or ""),
            )
            if pg_raise > 0:
                min_ev += pg_raise
        except Exception:
            pg_raise = 0.0

        # Before EV reject: try Exploration regime-explore quota (after process_gate raise)
        if (
            not high
            and regime_floor is not None
            and float(ev) + 1e-12 < float(min_ev)
            and str(risk.get("bankroll_regime") or "") == "exploration"
        ):
            try:
                from nt.bankroll_regime import (
                    EXPLORE_REGIME_TAG,
                    can_use_regime_explore_quota,
                )

                weekly_used = int(risk.get("regime_weekly_explore_used") or 0)
                # provisional slots already scored this round
                weekly_used += int(getattr(build_portfolio, "_regime_explore_scored", 0) or 0)
                regime_blob = dict(risk.get("regime") or {})
                has_pack = bool(c.evidence and c.evidence.get("p_model") is not None)
                if can_use_regime_explore_quota(
                    regime=regime_blob,
                    ev=float(ev),
                    odds=odds,
                    selection=c.selection or "",
                    sport=c.sport or "",
                    family=c.market_type or "",
                    weekly_used=weekly_used,
                    has_deep_pack=has_pack,
                ):
                    # pass at explore_min_ev only (process_gate still blocks if ev < raised min
                    # unless still within explore band — apply process_gate on top of explore floor)
                    explore_floor = float(
                        regime_blob.get("explore_min_ev")
                        or risk.get("regime_explore_min_ev")
                        or 0.02
                    )
                    eff = explore_floor + float(pg_raise or 0.0)
                    if float(ev) + 1e-12 >= eff:
                        regime_explore = True
                        min_ev = eff
                        build_portfolio._regime_explore_scored = (  # type: ignore[attr-defined]
                            int(getattr(build_portfolio, "_regime_explore_scored", 0) or 0)
                            + 1
                        )
            except Exception:
                regime_explore = False

        # Absolute floor after all boosts/raises (High-Volume v2: never below 1%)
        min_ev = max(float(min_ev), absolute_floor)

        if ev < min_ev:
            reason = f"EV {ev:.3f} < min {min_ev:.3f}"
            if pg_raise > 0:
                reason += f" (process_gate:+{pg_raise:.3f})"
            if strong:
                reason += " (strong_floor)"
            rejects.append(
                {
                    "match": c.match,
                    "selection": c.selection,
                    "odds": odds,
                    "reason": reason,
                    "grade": grade,
                    "high_odds": high,
                    "learning_ev_boost": adj.get("ev_boost"),
                    "process_gate_raise": pg_raise or None,
                }
            )
            continue

        # Grade F always rejected. Grade C: High-Volume v2 allows when core reason clear.
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
        if grade == "C" and not high:
            allow_c = bool(sel.get("grade_c_placeable", True))
            need_reason = bool(sel.get("grade_c_require_core_reason", True))
            min_c_src = int(sel.get("grade_c_min_sources", 4))
            n_src = len(normalize_sources((c.evidence or {}).get("sources")))
            if not allow_c:
                rejects.append(
                    {
                        "match": c.match,
                        "selection": c.selection,
                        "reason": "evidence grade C insufficient (need B+)",
                        "issues": issues,
                    }
                )
                continue
            if need_reason and not has_core_reason(c.evidence):
                rejects.append(
                    {
                        "match": c.match,
                        "selection": c.selection,
                        "reason": "grade C requires clear core reason (summary/takeaway ≥20 chars)",
                        "issues": issues,
                    }
                )
                continue
            if n_src < min_c_src:
                rejects.append(
                    {
                        "match": c.match,
                        "selection": c.selection,
                        "reason": f"grade C needs ≥{min_c_src} sources (got {n_src})",
                        "issues": issues,
                    }
                )
                continue
        if grade_a_only and grade != "A":
            rejects.append(
                {
                    "match": c.match,
                    "selection": c.selection,
                    "reason": f"loss streak ≥{streak_lim}: grade A only (got {grade})",
                    "issues": issues,
                }
            )
            continue

        learn_mult = float(adj.get("stake_mult") or 1.0)
        high_mult = float(sel["high_odds_stake_multiplier"])
        stake_decision: dict[str, Any] | None = None
        if _capital_v2_enabled(cfg):
            stake, stake_decision = _stake_for_capital_v2(
                cfg,
                risk,
                remaining_risk=remaining,
                min_stake=min_stake,
                high_odds=high,
                high_odds_mult=high_mult,
                learning_stake_mult=learn_mult,
                ev=ev,
                p_model=float(p_model),
                odds=odds,
                match=c.match,
                selection=c.selection,
                grade=grade,
                high_confidence=strong,
            )
        else:
            stake = _stake_for(
                phase,
                remaining,
                min_stake,
                high,
                high_mult,
                learn_mult,
                ev,
            )
        if stake < min_stake:
            rejects.append(
                {
                    "match": c.match,
                    "selection": c.selection,
                    "reason": "insufficient remaining risk for min stake",
                    "stake_decision": stake_decision,
                }
            )
            continue

        # Regime-explore: force 1 unit stake (spec: unit bets only for quota)
        if regime_explore:
            unit = float(risk.get("unit_size_nok") or min_stake)
            unit = max(float(min_stake), float(int(round(unit))))
            stake = min(unit, float(remaining))
            if stake + 1e-9 < min_stake:
                rejects.append(
                    {
                        "match": c.match,
                        "selection": c.selection,
                        "reason": "EXPLORE_REGIME: insufficient room for unit stake",
                    }
                )
                continue
            stake = float(int(round(stake)))
            if stake_decision is not None:
                stake_decision = dict(stake_decision)
                stake_decision["final_stake_nok"] = stake
                stake_decision["regime_explore"] = True

        note_bits = []
        if high:
            note_bits.append(f"HIGH_ODDS grade={grade}")
        if grade_a_only:
            note_bits.append("LOSS_STREAK_A_ONLY")
        # Dual-write p_model into notes for forensic recovery if side-car is missing
        note_bits.append(f"p_model={float(p_model):.4f}")
        note_bits.append(f"EV={ev:.3f}")
        if regime_explore:
            from nt.bankroll_regime import EXPLORE_REGIME_TAG

            note_bits.append(EXPLORE_REGIME_TAG)
            note_bits.append("explore")
        elif adj.get("explored"):
            note_bits.append("EXPLORE")
        if adj.get("stake_mult") and abs(float(adj["stake_mult"]) - 1.0) > 0.01:
            note_bits.append(f"learn_stake×{adj['stake_mult']}")
        if adj.get("ev_boost"):
            note_bits.append(f"learn_EV{float(adj['ev_boost']):+.3f}")
        if stake_decision:
            note_bits.append(
                f"stake_rec={stake_decision.get('final_stake_nok')};"
                f"rules={stake_decision.get('rule_bundle_version')};"
                f"size_mode={stake_decision.get('size_mode')};"
                f"unit={stake_decision.get('active_unit_nok')}"
            )
        for n in (adj.get("notes") or [])[:2]:
            note_bits.append(n)
        if c.notes:
            note_bits.append(c.notes[:120])

        mk = adj.get("market_key") or infer_market(c.selection or "", c.market_type or "")
        from nt.portfolio_correlation import league_key as _league_key
        from nt.portfolio_correlation import script_family as _script_family

        lg = _league_key(
            evidence=c.evidence if isinstance(c.evidence, dict) else None,
            match=c.match or "",
            sport=c.sport or "",
            notes=c.notes or "",
        )
        sf = _script_family(
            selection=c.selection or "",
            market_type=c.market_type or "",
            market_key=str(mk or ""),
            evidence=c.evidence if isinstance(c.evidence, dict) else None,
        )
        rec = Recommendation(
            match=c.match,
            selection=c.selection,
            decimal_odds=odds,
            stake_nok=stake,
            ev=round(ev, 4),
            grade=grade,
            odds_band=band,
            sport=normalize_sport(c.sport or "", default="unknown")
            if (c.sport or "").strip()
            else "",
            market_type=c.market_type or "",
            p_model=p_model,
            notes="; ".join(note_bits)[:400],
            high_odds=high,
            explore=bool(adj.get("explored") or regime_explore),
            learning_stake_mult=learn_mult,
            learning_ev_boost=float(adj.get("ev_boost") or 0.0),
            market_key=mk,
            reasons=list(adj.get("notes") or [])[:6],
            evidence_path=(c.evidence_path or "").strip(),
            match_date=(c.date or "").strip()[:10],
            kickoff=(c.kickoff or "").strip(),
            stake_decision=stake_decision,
            league_key=lg,
            script_family=sf,
        )
        scored.append(rec)

    # Sort by EV desc; optional explore-first reorder so thin sports get airtime
    scored.sort(key=lambda r: (r.ev, 1 if r.explore else 0), reverse=True)
    # Early regime: soft-prefer mid-odds lower-variance lines (sort only, not hard ban)
    if risk.get("regime_prefer_mid_odds") and risk.get("bankroll_regime") in (
        "exploration",
        "survival",
        "calibration",  # legacy id if any state still holds it
    ):
        from nt.bankroll_regime import is_mid_odds_preferred

        regime_blob = risk.get("regime") or {
            "prefer_mid_odds": True,
            "mid_odds_lo": 1.85,
            "mid_odds_hi": 2.50,
        }

        def _mid_key(r: Recommendation) -> tuple:
            mid = 1 if is_mid_odds_preferred(float(r.decimal_odds), regime_blob) else 0
            return (mid, r.ev, 1 if r.explore else 0)

        scored.sort(key=_mid_key, reverse=True)
    if div_lim.get("prefer_explore_first"):
        # Stable: explored non-football first among positive-EV, then pure EV
        scored.sort(
            key=lambda r: (
                0 if (r.explore and normalize_sport(r.sport) != "football") else 1,
                0 if r.explore else 1,
                -r.ev,
            )
        )

    picked: list[Recommendation] = []
    remaining = float(risk["remaining_risk_nok"])
    high_odds_count = 0
    match_counts: dict[str, int] = {}
    sport_counts: dict[str, int] = {}
    market_counts: dict[str, int] = {}
    band_counts: dict[str, int] = {}
    max_sport = int(div_lim["max_per_sport"])
    max_market = int(div_lim["max_per_market"])
    max_band = int(div_lim["max_per_band"])
    max_match = int(div_lim.get("max_per_match", 1))
    max_football = int(div_lim.get("max_football_per_round", 1))
    min_non_football = int(div_lim.get("min_non_football_per_round", 1))
    max_league = int(div_lim.get("max_per_league", 2))
    max_script = int(div_lim.get("max_per_script_family", 2))
    ko_window_h = float(div_lim.get("ko_window_hours", 3))
    max_ko_window = int(div_lim.get("max_per_ko_window", 2))

    from nt.portfolio_correlation import (
        count_ko_window,
        league_key as corr_league_key,
        parse_kickoff_hour,
        script_family as corr_script_family,
    )

    league_counts: dict[str, int] = {}
    script_counts: dict[str, int] = {}
    open_ko_hours: list[float | None] = []

    def _pending_sport(r: dict[str, str]) -> str:
        """Canonical sport key for open-risk diversify seed."""
        sp = (r.get("sport") or "").strip()
        if sp:
            return normalize_sport(sp, default="unknown")
        blob = f"{r.get('selection') or ''} {r.get('market_type') or ''} {r.get('match') or ''}".lower()
        if any(x in blob for x in ("kart", "maps", "cs2", "gaming", "esports")):
            return "esports"
        if any(x in blob for x in ("set handikap", "vinner:", "wimbledon", "atp", "wta")):
            return "tennis"
        if any(x in blob for x in ("inkludert overtid", "nba", "wnba", "lakers", "nets")):
            return "basketball"
        if any(
            x in blob
            for x in (
                "btts",
                "to win",
                "over ",
                "under ",
                "hub",
                "uavgjort",
                "tilbakebetales",
                "handikap",
                "mål",
            )
        ):
            return "football"
        return "unknown"

    # Seed caps from OPEN RISK (Pending + ConfirmedPlaced) — book-wide
    from nt.bets_io import is_open_risk

    for r in historical_rows or []:
        if not is_open_risk(r.get("result")):
            continue
        sp = _pending_sport(r)
        mk = infer_market(r.get("selection") or "", r.get("market_type") or "")
        bd = (r.get("odds_band") or "").strip()
        if not bd and r.get("decimal_odds") not in (None, ""):
            try:
                bd = odds_band(float(str(r.get("decimal_odds")).replace(",", ".")))
            except (TypeError, ValueError):
                bd = ""
        sport_counts[sp] = sport_counts.get(sp, 0) + 1
        if mk:
            market_counts[mk] = market_counts.get(mk, 0) + 1
        if bd:
            band_counts[bd] = band_counts.get(bd, 0) + 1
        m = (r.get("match") or "").strip()
        if m:
            match_counts[m] = match_counts.get(m, 0) + 1
        # P1 soft correlation seeds from open book
        notes = r.get("notes") or ""
        lg = corr_league_key(match=m, sport=sp, notes=notes)
        if lg != "unknown":
            league_counts[lg] = league_counts.get(lg, 0) + 1
        sf = corr_script_family(
            selection=r.get("selection") or "",
            market_type=r.get("market_type") or "",
        )
        script_counts[sf] = script_counts.get(sf, 0) + 1
        # kickoff from notes if present
        ko = ""
        if "kickoff=" in notes:
            try:
                ko = notes.split("kickoff=", 1)[1].split(";")[0].strip()
            except Exception:
                ko = ""
        open_ko_hours.append(parse_kickoff_hour(ko))

    def _is_football(sp: str) -> bool:
        return normalize_sport(sp, default="unknown") == "football"

    def _try_accept(rec: Recommendation, *, soft_football_cap: bool = False) -> str:
        """
        Try to add rec. Returns 'ok' | 'skip' | 'reject'.

        soft_football_cap:
            Prefer at most max_football while diversifying. Returns 'skip'
            (not reject) so the fill-up pass can still take good football
            (e.g. Racing BTTS Nei) when non-football cannot fill remaining seats.
            Hard ceiling remains max_per_sport (pending + this slip).
        """
        nonlocal remaining, high_odds_count
        if len(picked) >= max_bets or remaining < min_stake:
            return "skip"
        m = (rec.match or "").strip()
        if match_counts.get(m, 0) >= max_match:
            rejects.append(
                {
                    "match": rec.match,
                    "selection": rec.selection,
                    "reason": f"max {max_match} per match (including open pending)",
                }
            )
            return "reject"
        if any(
            is_open_risk(r.get("result"))
            and (r.get("match") or "").strip() == rec.match
            and (r.get("selection") or "").strip() == rec.selection
            for r in (historical_rows or [])
        ):
            rejects.append(
                {
                    "match": rec.match,
                    "selection": rec.selection,
                    "reason": "already open pending/confirmed on same selection",
                }
            )
            return "reject"
        if rec.high_odds and high_odds_count >= max_high:
            return "skip"

        sp_key = normalize_sport(rec.sport, default="unknown")
        mk_key = rec.market_key or infer_market(rec.selection, rec.market_type)
        bd_key = rec.odds_band or ""

        # Soft football preference only — never hard-kill remaining EV football
        if soft_football_cap and _is_football(sp_key):
            fb_open = sport_counts.get("football", 0)
            if fb_open >= max_football:
                return "skip"  # defer; pass 3 fill-up may still take it

        if sport_counts.get(sp_key, 0) >= max_sport:
            rejects.append(
                {
                    "match": rec.match,
                    "selection": rec.selection,
                    "reason": (
                        f"diversify: max {max_sport} open for sport '{sp_key}' "
                        f"(already {sport_counts.get(sp_key, 0)} pending/picked)"
                    ),
                }
            )
            return "reject"
        if market_counts.get(mk_key, 0) >= max_market:
            rejects.append(
                {
                    "match": rec.match,
                    "selection": rec.selection,
                    "reason": (
                        f"diversify: max {max_market} open for market '{mk_key}' "
                        f"(already {market_counts.get(mk_key, 0)} pending/picked)"
                    ),
                }
            )
            return "reject"
        if bd_key and band_counts.get(bd_key, 0) >= max_band:
            rejects.append(
                {
                    "match": rec.match,
                    "selection": rec.selection,
                    "reason": (
                        f"diversify: max {max_band} open for band '{bd_key}' "
                        f"(already {band_counts.get(bd_key, 0)} pending/picked)"
                    ),
                }
            )
            return "reject"

        # P1 soft correlation: league / script / KO window
        lg = (rec.league_key or "unknown").strip() or "unknown"
        if lg != "unknown" and league_counts.get(lg, 0) >= max_league:
            rejects.append(
                {
                    "match": rec.match,
                    "selection": rec.selection,
                    "reason": (
                        f"soft correlation: max {max_league} open for league '{lg}' "
                        f"(already {league_counts.get(lg, 0)})"
                    ),
                }
            )
            return "reject"
        sf = (rec.script_family or "other").strip() or "other"
        # Soft script caps only for high-correlation families (not bare ML fill)
        _SCRIPT_SOFT = {
            "totals_under",
            "totals_over",
            "btts_no",
            "btts_yes",
            "clean_sheet",
            "handicap",
        }
        if sf in _SCRIPT_SOFT and script_counts.get(sf, 0) >= max_script:
            rejects.append(
                {
                    "match": rec.match,
                    "selection": rec.selection,
                    "reason": (
                        f"soft correlation: max {max_script} open for script '{sf}' "
                        f"(already {script_counts.get(sf, 0)})"
                    ),
                }
            )
            return "reject"
        cand_h = parse_kickoff_hour(rec.kickoff or "")
        if cand_h is not None:
            n_ko = count_ko_window(cand_h, open_ko_hours, window_hours=ko_window_h)
            if n_ko >= max_ko_window:
                rejects.append(
                    {
                        "match": rec.match,
                        "selection": rec.selection,
                        "reason": (
                            f"soft correlation: max {max_ko_window} open in "
                            f"±{ko_window_h:.0f}h kickoff window (already {n_ko})"
                        ),
                    }
                )
                return "reject"

        stake = min(rec.stake_nok, remaining)
        stake = float(int(stake))
        if stake < min_stake:
            return "skip"
        rec.stake_nok = stake
        picked.append(rec)
        remaining = round(remaining - stake, 2)
        if rec.high_odds:
            high_odds_count += 1
        match_counts[m] = match_counts.get(m, 0) + 1
        sport_counts[sp_key] = sport_counts.get(sp_key, 0) + 1
        market_counts[mk_key] = market_counts.get(mk_key, 0) + 1
        if bd_key:
            band_counts[bd_key] = band_counts.get(bd_key, 0) + 1
        if lg != "unknown":
            league_counts[lg] = league_counts.get(lg, 0) + 1
        script_counts[sf] = script_counts.get(sf, 0) + 1
        open_ko_hours.append(cand_h)
        return "ok"

    picked_keys: set[tuple[str, str]] = set()
    combo_leg_keys: set[tuple[str, str]] = set()

    def _take(rec: Recommendation, *, soft_football_cap: bool = False) -> bool:
        if (rec.match, rec.selection) in picked_keys:
            return False
        # Don't re-place legs already used in a combo this round
        if (rec.match, rec.selection) in combo_leg_keys:
            return False
        # Combo tickets skip diversify sport counts as multi
        status = _try_accept(rec, soft_football_cap=soft_football_cap)
        if status == "ok":
            picked_keys.add((rec.match, rec.selection))
            return True
        return False

    # Pass 0: doubles FIRST (while remaining risk is still large)
    try:
        from nt.combos import (
            ComboLeg,
            assess_combo,
            format_combo_match,
            format_combo_selection,
        )
        from nt.defaults import combos_cfg

        cc = combos_cfg(cfg)
        max_doubles = int(phase.get("max_doubles_per_round") or 0)
        open_doubles = sum(
            1
            for r in (historical_rows or [])
            if is_open_risk(r.get("result"))
            and " + " in (r.get("selection") or "")
        )
        doubles_room = max(0, max_doubles - open_doubles)

        if cc.get("enabled") and doubles_room > 0 and len(scored) >= 2:
            legs_pool = [r for r in scored if r.ev >= float(cc.get("min_leg_ev") or 0.025)]
            legs_pool = legs_pool[:14]
            best_combo: Recommendation | None = None
            best_pair: tuple[Recommendation, Recommendation] | None = None
            best_ev = -1.0
            for i in range(len(legs_pool)):
                for j in range(i + 1, len(legs_pool)):
                    a, b = legs_pool[i], legs_pool[j]
                    if (a.match or "").strip().lower() == (b.match or "").strip().lower():
                        continue
                    combo_legs = [
                        ComboLeg(
                            match=a.match,
                            selection=a.selection,
                            decimal_odds=a.decimal_odds,
                            p_model=a.p_model,
                            grade=a.grade,
                            sport=a.sport,
                            market_type=a.market_type or a.market_key,
                            league="",
                            high_odds=a.high_odds,
                            ev=a.ev,
                        ),
                        ComboLeg(
                            match=b.match,
                            selection=b.selection,
                            decimal_odds=b.decimal_odds,
                            p_model=b.p_model,
                            grade=b.grade,
                            sport=b.sport,
                            market_type=b.market_type or b.market_key,
                            league="",
                            high_odds=b.high_odds,
                            ev=b.ev,
                        ),
                    ]
                    base = min(a.stake_nok, b.stake_nok, float(phase.get("stake_max") or 18))
                    assess = assess_combo(
                        cfg,
                        combo_legs,
                        phase,
                        haircut=haircut,
                        remaining_risk=remaining,
                        base_stake=base,
                    )
                    if not assess.ok:
                        continue
                    if assess.ev > best_ev and assess.stake_nok >= min_stake:
                        best_ev = assess.ev
                        stake = min(float(assess.stake_nok), remaining)
                        stake = float(int(stake))
                        if stake < min_stake:
                            continue
                        gr = (
                            a.grade
                            if {"A": 0, "B": 1, "C": 2, "F": 3}.get(a.grade, 9)
                            >= {"A": 0, "B": 1, "C": 2, "F": 3}.get(b.grade, 9)
                            else b.grade
                        )
                        best_pair = (a, b)
                        best_combo = Recommendation(
                            match=format_combo_match(combo_legs),
                            selection=format_combo_selection(combo_legs),
                            decimal_odds=float(assess.combined_odds),
                            stake_nok=stake,
                            ev=float(assess.ev),
                            grade=gr,
                            odds_band=odds_band(float(assess.combined_odds)),
                            sport=(
                                f"{a.sport}+{b.sport}"
                                if (a.sport or "") != (b.sport or "")
                                else (a.sport or "multi")
                            ),
                            market_type="combo_double",
                            p_model=float(assess.p_joint),
                            notes=(
                                f"COMBO_DOUBLE; p_joint={assess.p_joint:.4f}; EV={assess.ev:.3f}; "
                                f"corr={assess.correlation_score:.2f}; "
                                f"legs: {a.match} / {a.selection} @ {a.decimal_odds} + "
                                f"{b.match} / {b.selection} @ {b.decimal_odds}"
                            )[:400],
                            high_odds=float(assess.combined_odds) >= thr,
                            explore=False,
                            learning_stake_mult=1.0,
                            learning_ev_boost=0.0,
                            market_key="combo_double",
                            reasons=list(assess.reasons)[:6],
                            evidence_path="",
                        )
            if best_combo is not None and best_pair is not None:
                stake = min(best_combo.stake_nok, remaining)
                stake = float(int(stake))
                if stake >= min_stake and len(picked) < max_bets:
                    best_combo.stake_nok = stake
                    picked.append(best_combo)
                    remaining = round(remaining - stake, 2)
                    for leg in best_pair:
                        combo_leg_keys.add((leg.match, leg.selection))
                        picked_keys.add((leg.match, leg.selection))
    except Exception as exc:
        rejects.append({"reason": f"combo pass skipped: {exc}"})

    # Pack at min_stake first so sequential EV-sized stakes don't burn seats
    # (e.g. 12+10+11=33 leave 8.51 stranded under NT min 10).
    for rec in scored:
        rec.stake_nok = float(min_stake)

    def _fill_passes() -> None:
        # Pass 1: non-football first (build sample for thin sports)
        for rec in scored:
            if len(picked) >= max_bets or remaining < min_stake:
                break
            if _is_football(rec.sport or ""):
                continue
            _take(rec, soft_football_cap=False)

        # Pass 2: limited football first (max_football is a soft preference only)
        for rec in scored:
            if len(picked) >= max_bets or remaining < min_stake:
                break
            if not _is_football(rec.sport or ""):
                continue
            _take(rec, soft_football_cap=True)

        # Pass 3: fill remaining seats
        for rec in scored:
            if len(picked) >= max_bets or remaining < min_stake:
                break
            _take(rec, soft_football_cap=False)

    def _count_extra_eligible() -> int:
        """How many more scored candidates could still clear diversify at min_stake."""
        if len(picked) >= max_bets or remaining < min_stake:
            return 0
        n_extra = 0
        # Snapshot counts — trial without mutating
        for rec in scored:
            if (rec.match, rec.selection) in picked_keys:
                continue
            if (rec.match, rec.selection) in combo_leg_keys:
                continue
            m = (rec.match or "").strip()
            if match_counts.get(m, 0) >= max_match:
                continue
            sp_key = normalize_sport(rec.sport, default="unknown")
            mk_key = rec.market_key or infer_market(rec.selection, rec.market_type)
            bd_key = rec.odds_band or ""
            if sport_counts.get(sp_key, 0) >= max_sport:
                continue
            if market_counts.get(mk_key, 0) >= max_market:
                continue
            if bd_key and band_counts.get(bd_key, 0) >= max_band:
                continue
            if rec.high_odds and high_odds_count >= max_high:
                continue
            n_extra += 1
            if n_extra + len(picked) >= max_bets:
                break
        return n_extra

    _fill_passes()

    # Multi-pass pack: reserve min seats for still-eligible candidates, then refill
    # High-Volume v2: per-run stake sum ≤ max_run_stake_pct_of_equity × equity
    # (also min'd with remaining_risk — fail-closed).
    remaining_risk_budget = float(risk["remaining_risk_nok"])
    equity_now = float(risk.get("equity_nok") or 0.0)
    run_pct = float((cfg.get("recommend") or {}).get("max_run_stake_pct_of_equity") or 0.20)
    if equity_now > 0 and run_pct > 0:
        run_equity_cap = equity_now * run_pct
    else:
        run_equity_cap = remaining_risk_budget
    budget = min(remaining_risk_budget, run_equity_cap)
    build_portfolio._run_stake_cap_nok = budget  # type: ignore[attr-defined]
    build_portfolio._run_stake_equity_cap_nok = run_equity_cap  # type: ignore[attr-defined]
    max_stake = float(phase.get("stake_max") or min_stake)
    if _capital_v2_enabled(cfg):
        # Unit ladder is the hard per-bet ceiling (active unit after size_mode).
        # Grade mult can lift recommended above unit — rebalance may top toward
        # max of unit and each seat's recommended final from scoring.
        from nt.capital_v2 import active_unit_for_mode, capital_v2_cfg, unit_size

        v2 = capital_v2_cfg(cfg)
        floor = float(v2.get("min_stake_nok") or min_stake)
        mode = str(risk.get("size_mode") or "NORMAL")
        if risk.get("stopped") or not risk.get("can_bet", True):
            mode = "FROZEN"
        u = risk.get("unit_size_nok")
        if u is None:
            liq = risk.get("riskable_liquid_nok")
            if liq is None:
                liq = risk.get("working_equity_nok") or budget
            u = unit_size(float(liq), v2)
        active_u = active_unit_for_mode(float(u), mode, floor)
        # Cap rebalance top-up at active unit × max grade mult (High-Volume v2)
        max_stake = max(floor, active_u * 2.2) if active_u > 0 else floor
        for rec in picked:
            if rec.stake_decision is not None:
                rec.stake_decision = dict(rec.stake_decision)
                rec.stake_decision["active_unit_nok"] = active_u
                caps = list(rec.stake_decision.get("constraints_applied") or [])
                tag = f"rebalance_cap_unit:{max_stake}"
                if tag not in caps:
                    caps.append(tag)
                rec.stake_decision["constraints_applied"] = caps
                rec.stake_decision["run_stake_cap_nok"] = budget

    def _seat_maxes() -> list[float]:
        caps: list[float] = []
        for rec in picked:
            rec_cap = float(
                (rec.stake_decision or {}).get("recommended_stake_nok")
                or (rec.stake_decision or {}).get("final_stake_nok")
                or max_stake
            )
            caps.append(max(min_stake, min(max_stake, rec_cap)))
        return caps

    for _ in range(3):  # bounded retries
        extra = _count_extra_eligible()
        fundable_extra = max(
            0,
            int(budget // min_stake) - len(picked),
        )
        reserve = min(extra, fundable_extra, max_bets - len(picked))
        leftover = rebalance_stakes(
            picked,
            budget,
            min_stake,
            max_stake,
            reserve_extra_seats=reserve,
            max_stakes=_seat_maxes(),
        )
        remaining = leftover
        if remaining < min_stake or len(picked) >= max_bets or reserve <= 0:
            rebalance_stakes(
                picked,
                budget,
                min_stake,
                max_stake,
                reserve_extra_seats=0,
                max_stakes=_seat_maxes(),
            )
            break
        n_before = len(picked)
        _fill_passes()
        if len(picked) == n_before:
            rebalance_stakes(
                picked,
                budget,
                min_stake,
                max_stake,
                reserve_extra_seats=0,
                max_stakes=_seat_maxes(),
            )
            break

    # P0: never leave a fundable min-seat idle when diversify still allows it
    rebalance_stakes(
        picked,
        budget,
        min_stake,
        max_stake,
        reserve_extra_seats=0,
        max_stakes=_seat_maxes(),
    )
    used = sum(float(p.stake_nok) for p in picked)
    leftover_final = round(budget - used, 2)
    if leftover_final + 1e-9 >= min_stake and len(picked) < max_bets:
        remaining = leftover_final
        n_before = len(picked)
        _fill_passes()
        if len(picked) > n_before:
            rebalance_stakes(
                picked,
                budget,
                min_stake,
                max_stake,
                reserve_extra_seats=0,
                max_stakes=_seat_maxes(),
            )

    # EXPLORE_REGIME unit bets must stay at 1 unit (rebalance must not top them up)
    try:
        from nt.bankroll_regime import EXPLORE_REGIME_TAG

        unit = max(float(min_stake), float(int(round(float(risk.get("unit_size_nok") or min_stake)))))
        for rec in picked:
            if EXPLORE_REGIME_TAG in (rec.notes or ""):
                rec.stake_nok = unit
    except Exception:
        pass

    # After final rebalance: fail-closed floor + refresh stake_decision finals (v2)
    if _capital_v2_enabled(cfg):
        for rec in picked:
            if rec.stake_nok + 1e-9 < min_stake:
                rec.stake_nok = 0.0
            else:
                rec.stake_nok = float(int(rec.stake_nok))
            if rec.stake_decision is not None:
                sd = dict(rec.stake_decision)
                sd["final_stake_nok"] = rec.stake_nok
                sd["recommended_stake_nok"] = max(
                    float(sd.get("recommended_stake_nok") or 0.0), rec.stake_nok
                )
                sd["run_stake_cap_nok"] = budget
                rec.stake_decision = sd
        # Drop any zeroed seats (should be rare; rebalance already drops by budget)
        picked[:] = [r for r in picked if r.stake_nok >= min_stake]

    # Strict per-run sum check (High-Volume v2): never exceed budget
    used_sum = sum(float(p.stake_nok) for p in picked)
    if used_sum > budget + 1e-6 and picked:
        # Scale down whole-krone greedily from lowest-EV first
        ordered = sorted(picked, key=lambda r: float(r.ev))
        over = used_sum - budget
        for rec in ordered:
            if over <= 1e-9:
                break
            cut = min(float(rec.stake_nok) - min_stake, over) if rec.stake_nok > min_stake else 0.0
            if cut >= 1.0:
                rec.stake_nok = float(int(rec.stake_nok - cut))
                over = sum(float(p.stake_nok) for p in picked) - budget
        # Drop seats that can no longer fund min stake under budget
        while sum(float(p.stake_nok) for p in picked) > budget + 1e-6 and picked:
            # drop lowest EV
            worst = min(picked, key=lambda r: float(r.ev))
            picked.remove(worst)
            rejects.append(
                {
                    "match": worst.match,
                    "selection": worst.selection,
                    "reason": f"run stake budget {budget:.0f} NOK (20% equity / remaining)",
                }
            )

    return picked, rejects
