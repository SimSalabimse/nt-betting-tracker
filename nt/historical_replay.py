"""
Historical stake replay under current capital_v2 + Kelly rules.

Read-only vs ledger: never mutates bets.csv. Used for validation / counterfactual.
"""
from __future__ import annotations

import re
from typing import Any

from nt.bets_io import fnum, is_open_risk, is_performance_settled, load_bets
from nt.capital_v2 import (
    capital_v2_cfg,
    compute_unit_stake,
    drawdown_from_peak,
    peak_equity_settlement,
    portfolio_open_room,
    size_mode_from_dd,
    unit_size,
    whole_krone,
)
from nt.config import path_from_config
from nt.kelly import fractional_kelly_stake


def parse_p_model_from_notes(notes: str) -> float | None:
    m = re.search(r"\bp_model\s*=\s*([+-]?\d+(?:[.,]\d+)?)", notes or "", re.I)
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    if v > 1.0:
        v /= 100.0
    if 0.01 < v < 0.99:
        return v
    return None


def parse_ev_from_notes(notes: str) -> float | None:
    m = re.search(r"\bEV\s*=\s*([+-]?\d+(?:[.,]\d+)?)", notes or "", re.I)
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    if abs(v) > 1.0:
        v /= 100.0
    return v


def _sort_key(r: dict[str, Any]) -> tuple:
    return (
        str(r.get("created_at") or r.get("date") or ""),
        str(r.get("bet_id") or ""),
    )


def _equity_at(baseline: float, prior_settled: list[dict[str, Any]]) -> float:
    pl = sum(fnum(r.get("p_l_nok")) or 0.0 for r in prior_settled if is_performance_settled(r.get("result")))
    return round(float(baseline) + pl, 2)


def _open_at_place(
    all_rows: list[dict[str, Any]],
    place_ts: str,
    exclude_id: str,
) -> list[dict[str, Any]]:
    """
    Tickets that were open risk when this bet was placed:
    created_at <= place_ts and (still open today OR settled after place_ts).
    """
    open_rows: list[dict[str, Any]] = []
    for r in all_rows:
        if str(r.get("bet_id") or "") == exclude_id:
            continue
        created = str(r.get("created_at") or r.get("date") or "")
        if created > place_ts:
            continue
        result = str(r.get("result") or "")
        if is_open_risk(result):
            open_rows.append(r)
            continue
        updated = str(r.get("updated_at") or "")
        # Settled after place → was open at place time
        if updated and place_ts and updated > place_ts:
            open_rows.append(r)
    return open_rows


def replay_stake_for_row(
    cfg: dict[str, Any],
    row: dict[str, Any],
    *,
    prior_settled: list[dict[str, Any]],
    open_at_place: list[dict[str, Any]],
    baseline: float,
    cal_n: int = 0,
    brier: float | None = None,
) -> dict[str, Any]:
    """
    Recompute capital_v2 + Kelly stake as if placing this ticket under current rules.
    """
    v2 = capital_v2_cfg(cfg)
    floor = float(v2.get("min_stake_nok") or cfg.get("norsk_tipping", {}).get("min_stake_nok") or 10)
    stake_actual = fnum(row.get("stake_nok")) or 0.0
    odds = fnum(row.get("decimal_odds")) or 0.0
    p_model = parse_p_model_from_notes(str(row.get("notes") or ""))
    if p_model is None:
        # Implied + tiny edge fallback for audit only
        p_model = min(0.75, max(0.35, (1.0 / odds) + 0.03)) if odds > 1.01 else 0.5
        p_src = "implied_fallback"
    else:
        p_src = "notes"

    equity = _equity_at(baseline, prior_settled)
    # Peak from settlement curve of prior settled only
    peak = peak_equity_settlement(prior_settled, baseline) if prior_settled else baseline
    peak = max(peak, equity, baseline)
    dd = drawdown_from_peak(equity, peak)
    dd_cfg = v2.get("drawdown") or {}
    size_mode = size_mode_from_dd(
        dd,
        freeze_active=False,
        reduce_at=float(dd_cfg.get("reduce_at") or 0.15),
        freeze_at=float(dd_cfg.get("freeze_at") or 0.25),
    )

    open_stake = sum(fnum(r.get("stake_nok")) or 0.0 for r in open_at_place)
    # Riskable liquid ≈ equity - open (no secure bucket in historical rows)
    liquid = max(0.0, equity - open_stake)
    unit = unit_size(liquid, v2)
    por_cfg = v2.get("portfolio_open_risk") or {}
    max_open_pct = float(por_cfg.get("max_pct_of_riskable_liquid") or 0.18)
    # Match risk.py: open_room(open_pending, liquid_now, max_pct=...)
    room = portfolio_open_room(open_stake, liquid, max_pct=max_open_pct)
    # Phase-style open budget ≈ 8% equity floor/ceil soft approx for Phase 1A
    phase_cap = max(30.0, min(42.0, equity * 0.08))
    phase_remaining = max(0.0, phase_cap - open_stake)
    remaining = max(0.0, min(room, phase_remaining))

    decision = compute_unit_stake(
        size_mode=size_mode,
        unit_size_nok=unit,
        remaining_room_nok=remaining,
        min_stake=floor,
        stopped=False,
        can_bet=remaining + 1e-9 >= floor and size_mode != "FROZEN",
        high_odds=odds >= float((cfg.get("selection") or {}).get("high_odds_threshold") or 2.5),
        high_odds_mult=float((cfg.get("selection") or {}).get("high_odds_stake_multiplier") or 0.6),
        learning_stake_mult=1.0,
        match=str(row.get("match") or ""),
        selection=str(row.get("selection") or ""),
    )
    audit = decision.to_audit_dict()
    final = float(decision.final_stake_nok)
    k_notes: list[str] = []
    k_stake = None
    kcfg = dict(v2.get("kelly") or {})
    if kcfg.get("enabled", True) and final >= floor and p_model is not None and odds > 1.01:
        active = float(decision.active_unit_nok or unit)
        k_stake, k_notes = fractional_kelly_stake(
            p_model=float(p_model),
            odds=float(odds),
            liquid=liquid,
            active_unit=active,
            min_stake=floor,
            remaining_room=remaining,
            kelly_cfg=kcfg,
            brier=brier,
            cal_n=cal_n,
        )
        if k_stake is not None and k_stake > final + 1e-9:
            final = float(int(k_stake))
            k_notes = list(k_notes) + [f"kelly_applied:{final}"]
        audit["constraints_applied"] = list(audit.get("constraints_applied") or []) + list(k_notes)

    # Counterfactual P/L preserving historical payout rate on wins
    result = str(row.get("result") or "")
    pl_actual = fnum(row.get("p_l_nok")) or 0.0
    payout_actual = fnum(row.get("payout_nok"))
    if result == "Loss":
        pl_new = -final if final > 0 else 0.0
    elif result in ("Refunded", "Void", "Push"):
        pl_new = 0.0
    elif result == "Win":
        if stake_actual > 0 and payout_actual is not None and payout_actual > 0:
            rate = payout_actual / stake_actual  # total return multiple
            pl_new = round(final * rate - final, 2)
        elif stake_actual > 0 and odds > 1:
            pl_new = round(final * (odds - 1.0), 2)
        else:
            pl_new = pl_actual
    else:
        pl_new = pl_actual

    violations: list[str] = []
    if final < 0:
        violations.append("negative_stake")
    if 0 < final < floor - 1e-9:
        violations.append(f"below_nt_floor:{final}<{floor}")
    if final != whole_krone(final) and final > 0:
        violations.append(f"not_whole_krone:{final}")
    if final > remaining + 1e-6 and final > 0:
        violations.append(f"exceeds_room:{final}>{remaining}")
    if size_mode == "FROZEN" and final > 0:
        violations.append("stake_while_frozen")

    return {
        "bet_id": row.get("bet_id"),
        "match": row.get("match"),
        "selection": row.get("selection"),
        "sport": row.get("sport"),
        "result": result,
        "odds": odds,
        "p_model": p_model,
        "p_model_source": p_src,
        "stake_actual": stake_actual,
        "stake_replay": final,
        "delta_stake": round(final - stake_actual, 2),
        "pl_actual": pl_actual,
        "pl_replay": round(pl_new, 2),
        "delta_pl": round(pl_new - pl_actual, 2),
        "equity_at_place": equity,
        "liquid_at_place": round(liquid, 2),
        "open_stake_at_place": round(open_stake, 2),
        "unit": unit,
        "size_mode": size_mode,
        "dd_from_peak": round(dd, 4),
        "remaining_room": remaining,
        "kelly_stake": k_stake,
        "kelly_notes": k_notes,
        "constraints": audit.get("constraints_applied") or [],
        "violations": violations,
        "active_unit": decision.active_unit_nok,
    }


def replay_last_settled(
    cfg: dict[str, Any],
    *,
    n: int = 40,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Replay last N performance-settled tickets under current rules.
    """
    if rows is None:
        rows = load_bets(path_from_config(cfg, "bets"))
    baseline = float((cfg.get("bankroll") or {}).get("baseline_nok") or 500.0)

    cal_n, brier = 0, None
    try:
        from nt.calibrate import load_calibration_quality

        cq = load_calibration_quality(cfg)
        cal_n = int(cq.get("n") or 0)
        brier = cq.get("brier")
        if brier is not None:
            brier = float(brier)
    except Exception:
        pass

    settled = [r for r in rows if is_performance_settled(r.get("result"))]
    settled_sorted = sorted(settled, key=_sort_key)
    target = settled_sorted[-max(1, int(n)) :] if settled_sorted else []

    # Full chronological list for prior context
    all_sorted = sorted(rows, key=_sort_key)

    replays: list[dict[str, Any]] = []
    for row in target:
        place_ts = str(row.get("created_at") or row.get("date") or "")
        bid = str(row.get("bet_id") or "")
        # Prior performance settled (strictly before this place)
        prior = [
            r
            for r in settled_sorted
            if _sort_key(r) < _sort_key(row) and is_performance_settled(r.get("result"))
        ]
        # Also include settled that happened before place by settlement time but
        # created earlier — already covered by created_at sort for small books.
        open_rows = _open_at_place(all_sorted, place_ts, bid)
        rec = replay_stake_for_row(
            cfg,
            row,
            prior_settled=prior,
            open_at_place=open_rows,
            baseline=baseline,
            cal_n=cal_n,
            brier=brier,
        )
        replays.append(rec)

    n_viol = sum(1 for r in replays if r["violations"])
    stake_up = sum(1 for r in replays if r["delta_stake"] > 0.5)
    stake_down = sum(1 for r in replays if r["delta_stake"] < -0.5)
    stake_same = len(replays) - stake_up - stake_down
    kelly_applied = sum(1 for r in replays if any("kelly_applied" in str(x) for x in r.get("kelly_notes") or []))
    pl_actual = sum(r["pl_actual"] for r in replays)
    pl_replay = sum(r["pl_replay"] for r in replays)
    stake_actual = sum(r["stake_actual"] for r in replays)
    stake_replay = sum(r["stake_replay"] for r in replays)

    return {
        "n_requested": n,
        "n_available_settled": len(settled_sorted),
        "n_replayed": len(replays),
        "calibration": {"n": cal_n, "brier": brier},
        "summary": {
            "n_violations": n_viol,
            "stake_up": stake_up,
            "stake_down": stake_down,
            "stake_same": stake_same,
            "kelly_applied_n": kelly_applied,
            "stake_actual_sum": round(stake_actual, 2),
            "stake_replay_sum": round(stake_replay, 2),
            "pl_actual_sum": round(pl_actual, 2),
            "pl_replay_sum": round(pl_replay, 2),
            "delta_pl_sum": round(pl_replay - pl_actual, 2),
            "roi_actual": round(pl_actual / stake_actual, 4) if stake_actual else 0.0,
            "roi_replay": round(pl_replay / stake_replay, 4) if stake_replay else 0.0,
        },
        "rows": replays,
        "pass": n_viol == 0 and len(replays) > 0,
    }


def render_replay_markdown(report: dict[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [
        "# Historical replay validation",
        "",
        f"- Replayed: **{report.get('n_replayed')}** / available settled {report.get('n_available_settled')} (requested {report.get('n_requested')})",
        f"- Violations: **{s.get('n_violations')}**",
        f"- Stake Δ: up {s.get('stake_up')} · same {s.get('stake_same')} · down {s.get('stake_down')}",
        f"- Kelly applied: {s.get('kelly_applied_n')}",
        f"- Stake sum actual→replay: {s.get('stake_actual_sum')} → {s.get('stake_replay_sum')}",
        f"- P/L sum actual→replay: {s.get('pl_actual_sum')} → {s.get('pl_replay_sum')} (Δ {s.get('delta_pl_sum')})",
        f"- ROI actual→replay: {s.get('roi_actual')} → {s.get('roi_replay')}",
        f"- Calibration gate: n={report.get('calibration', {}).get('n')} brier={report.get('calibration', {}).get('brier')}",
        f"- **PASS:** {report.get('pass')}",
        "",
        "| bet_id | result | stake_act | stake_rep | Δ | pl_act | pl_rep | mode | unit | violations |",
        "|--------|--------|-----------|-----------|---|--------|--------|------|------|------------|",
    ]
    for r in report.get("rows") or []:
        viol = ",".join(r.get("violations") or []) or "—"
        lines.append(
            f"| `{r.get('bet_id')}` | {r.get('result')} | {r.get('stake_actual')} | {r.get('stake_replay')} | "
            f"{r.get('delta_stake')} | {r.get('pl_actual')} | {r.get('pl_replay')} | {r.get('size_mode')} | "
            f"{r.get('unit')} | {viol} |"
        )
    return "\n".join(lines) + "\n"
