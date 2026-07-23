"""
Read-only validation: ControlSignals + PhaseState over historical settled book.

Measures how process_error-class losses would have triggered temp_gate_raise
and whether subsequent same-sport stakes would face raised min_ev / REDUCED floor.
Never mutates ledger.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nt.bets_io import fnum, is_performance_settled, load_bets
from nt.capital_v2 import (
    capital_v2_cfg,
    drawdown_from_peak,
    peak_equity_settlement,
    size_mode_from_dd,
)
from nt.config import path_from_config
from nt.phase import evaluate_phase
from nt.phase_factors import process_error_rate_14d
from nt.risk import evaluate_risk
from nt.settlement_review import settlement_reviews_path


def _parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        raw = s.replace("Z", "+00:00") if str(s).endswith("Z") else str(s)
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _sort_settled(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    settled = [r for r in rows if is_performance_settled(r.get("result"))]
    settled.sort(
        key=lambda r: (
            str(r.get("updated_at") or r.get("date") or ""),
            str(r.get("bet_id") or ""),
        )
    )
    return settled


def _load_reviews_by_bet(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    path = settlement_reviews_path(cfg)
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        bid = str(rec.get("bet_id") or "")
        if bid:
            out[bid] = rec
    return out


def _is_process_error_class(review: dict[str, Any] | None, row: dict[str, Any]) -> bool:
    if review:
        try:
            from nt.settlement_taxonomy import is_process_error_class

            if is_process_error_class(review.get("variance_class")):
                return True
        except Exception:
            if str(review.get("variance_class") or "") in (
                "process_error",
                "research_process_miss",
            ):
                return True
        if str(review.get("legacy_label") or "") == "process_error":
            return True
    notes = str(row.get("notes") or "").lower()
    if "feel:process_error" in notes or "research_retro:poor" in notes:
        return True
    if "research_retro:wrong" in notes or "research_retro:miss" in notes:
        return True
    return False


def _severity_rank(mode: str) -> int:
    m = (mode or "NORMAL").upper()
    return {"NORMAL": 0, "REDUCED": 1, "FROZEN": 2, "RESEARCH_ONLY": 2}.get(m, 0)


def validate_size_mode_floor_invariant(
    cfg: dict[str, Any],
    *,
    equity: float,
    settled_count: int,
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Assert: risk.size_mode severity >= capital size_mode (phase can only tighten).
    """
    phase = evaluate_phase(cfg, equity, settled_count, rows)
    risk = evaluate_risk(cfg, equity, phase, rows)
    capital = str(risk.get("size_mode_capital") or risk.get("size_mode") or "NORMAL").upper()
    effective = str(risk.get("size_mode") or "NORMAL").upper()
    floor = str(risk.get("size_mode_floor") or phase.get("size_mode_floor") or "").upper()
    ok = _severity_rank(effective) >= _severity_rank(capital)
    # If floor is REDUCED and capital NORMAL, effective must be REDUCED
    if floor == "REDUCED" and capital == "NORMAL" and not risk.get("stopped"):
        ok = ok and effective == "REDUCED"
    return {
        "ok": ok,
        "size_mode_capital": capital,
        "size_mode": effective,
        "size_mode_floor": floor or None,
        "research_only": bool(risk.get("research_only") or phase.get("research_only")),
        "phase_id": phase.get("phase_id"),
        "reasons": (risk.get("reasons") or [])[:8],
    }


def replay_closed_loop(
    cfg: dict[str, Any],
    *,
    n: int = 60,
    rows: list[dict[str, Any]] | None = None,
    ttl_days: float = 10.0,
) -> dict[str, Any]:
    """
    Walk last N settled tickets in settlement order.

    Simulates ControlSignals: after each process_error-class loss, sport gets
    an active gate for ttl_days. Subsequent same-sport tickets during the gate
    are counted as would_face_temp_gate (sized-down bar / higher min_ev).
    """
    if rows is None:
        rows = load_bets(path_from_config(cfg, "bets"))
    baseline = float((cfg.get("bankroll") or {}).get("baseline_nok") or 500.0)
    all_settled = _sort_settled(rows)
    target = all_settled[-max(1, int(n)) :] if all_settled else []
    reviews = _load_reviews_by_bet(cfg)

    # Active gates: sport -> expires_at datetime
    gates: dict[str, datetime] = {}
    process_error_events: list[dict[str, Any]] = []
    subsequent_under_gate = 0
    subsequent_under_gate_losses = 0
    subsequent_under_gate_wins = 0
    tickets_after_pe_same_sport: list[dict[str, Any]] = []

    for i, row in enumerate(target):
        bid = str(row.get("bet_id") or "")
        sport = (row.get("sport") or "unknown").strip().lower()
        ts = _parse_ts(str(row.get("updated_at") or row.get("date") or "")) or datetime.now(
            timezone.utc
        )
        result = str(row.get("result") or "")
        rev = reviews.get(bid)
        pe = _is_process_error_class(rev, row)

        # Was this ticket under an active gate at settle time?
        under = False
        exp = gates.get(sport)
        if exp and exp > ts:
            under = True
            subsequent_under_gate += 1
            if result == "Loss":
                subsequent_under_gate_losses += 1
            elif result == "Win":
                subsequent_under_gate_wins += 1
            tickets_after_pe_same_sport.append(
                {
                    "bet_id": bid,
                    "sport": sport,
                    "result": result,
                    "stake": fnum(row.get("stake_nok")),
                    "under_temp_gate": True,
                    "gate_expires": exp.isoformat(),
                }
            )

        if pe and result == "Loss":
            expires = ts + timedelta(days=float(ttl_days))
            # Stack: extend or set
            prev = gates.get(sport)
            if prev and prev > expires:
                expires = prev
            gates[sport] = expires
            process_error_events.append(
                {
                    "bet_id": bid,
                    "sport": sport,
                    "ts": ts.isoformat(),
                    "expires": expires.isoformat(),
                    "variance_class": (rev or {}).get("variance_class"),
                    "match": row.get("match"),
                }
            )

    # Live phase/risk invariant on full book
    from nt.bankroll import compute_bankroll

    b = compute_bankroll(cfg)
    inv = validate_size_mode_floor_invariant(
        cfg,
        equity=float(b["equity_nok"]),
        settled_count=int(b["settled_count"]),
        rows=rows,
    )

    pe_stats = process_error_rate_14d(cfg)

    # Thin-sample protection constants (must match settlement_review)
    thin = {
        "full_delta_min_n": 8,
        "full_delta_min_conf": 0.40,
        "policy": "full_delta_requires_n>=8_and_conf>=0.40",
    }

    # Counterfactual: PE losses that would emit gate even at n=1
    n_pe_losses = len(process_error_events)
    # "Blocked or sized down" proxy: subsequent same-sport tickets under gate
    # + if research_only / REDUCED floor would apply after rate > 0.25
    would_size_down = subsequent_under_gate
    would_block_high_odds = bool(
        (inv.get("research_only"))
        or pe_stats.get("force_process_health")
    )

    return {
        "n_requested": n,
        "n_settled_available": len(all_settled),
        "n_replayed": len(target),
        "process_error_class_losses": n_pe_losses,
        "process_error_events": process_error_events,
        "subsequent_tickets_under_temp_gate": subsequent_under_gate,
        "subsequent_under_gate_losses": subsequent_under_gate_losses,
        "subsequent_under_gate_wins": subsequent_under_gate_wins,
        "tickets_under_gate_detail": tickets_after_pe_same_sport[:40],
        "would_have_faced_raised_min_ev_or_confirmed": subsequent_under_gate,
        "live_process_error_rate_14d": pe_stats,
        "size_mode_invariant": inv,
        "thin_sample_policy": thin,
        "ttl_days_assumed": ttl_days,
        "pass": bool(inv.get("ok")) and n_pe_losses >= 0,
        "summary": {
            "pe_losses_emitted_gates": n_pe_losses,
            "later_same_sport_tickets_gated": subsequent_under_gate,
            "of_which_losses": subsequent_under_gate_losses,
            "of_which_wins": subsequent_under_gate_wins,
            "size_mode_floor_ok": inv.get("ok"),
            "live_size_mode": inv.get("size_mode"),
            "live_size_mode_capital": inv.get("size_mode_capital"),
        },
    }


def render_validation_markdown(report: dict[str, Any]) -> str:
    s = report.get("summary") or {}
    inv = report.get("size_mode_invariant") or {}
    pe = report.get("live_process_error_rate_14d") or {}
    lines = [
        "# Closed-loop + PhaseState validation",
        "",
        f"- Replayed settled: **{report.get('n_replayed')}** / available {report.get('n_settled_available')} (requested {report.get('n_requested')})",
        f"- Process-error-class **losses** that would emit temp_gate_raise: **{s.get('pe_losses_emitted_gates')}**",
        f"- Later same-sport tickets while gate active: **{s.get('later_same_sport_tickets_gated')}** "
        f"(losses {s.get('of_which_losses')} · wins {s.get('of_which_wins')})",
        f"- TTL assumed: **{report.get('ttl_days_assumed')}d**",
        f"- Thin-sample full mult delta: n≥{report.get('thin_sample_policy', {}).get('full_delta_min_n')} "
        f"conf≥{report.get('thin_sample_policy', {}).get('full_delta_min_conf')}",
        f"- Live process_error_rate_14d: **{pe.get('process_error_rate_14d')}** "
        f"(n_reviews={pe.get('n_reviews_14d')}, force={pe.get('force_process_health')})",
        f"- size_mode invariant (phase ≥ capital severity): **{inv.get('ok')}** "
        f"(capital={inv.get('size_mode_capital')} effective={inv.get('size_mode')} floor={inv.get('size_mode_floor')})",
        f"- **PASS:** {report.get('pass')}",
        "",
        "## Process-error events (would emit ControlSignal)",
        "",
    ]
    for e in report.get("process_error_events") or []:
        lines.append(
            f"- `{e.get('bet_id')}` · {e.get('sport')} · {e.get('match')} · exp {e.get('expires')}"
        )
    if not report.get("process_error_events"):
        lines.append("- (none in replay window)")
    lines.extend(["", "## Subsequent tickets under simulated gate", ""])
    for t in (report.get("tickets_under_gate_detail") or [])[:20]:
        lines.append(
            f"- `{t.get('bet_id')}` · {t.get('sport')} · {t.get('result')} · stake {t.get('stake')}"
        )
    if not report.get("tickets_under_gate_detail"):
        lines.append("- (none — no same-sport follow-on while gate active)")
    lines.append("")
    return "\n".join(lines)
