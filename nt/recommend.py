from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from nt.bankroll import compute_bankroll, write_bankroll_state
from nt.bets_io import (
    fmt_num,
    load_bets,
    make_bet_id,
    odds_band,
    utc_now,
    write_bets,
)
from nt.config import path_from_config
from nt.odds_parse import attach_evidence, parse_odds_file
from nt.phase import evaluate_phase, load_phase_state, write_phase_state
from nt.portfolio import build_portfolio
from nt.risk import evaluate_risk, write_risk_state
from nt.status import write_status


def refresh_state(cfg: dict[str, Any]) -> tuple[dict, dict, dict]:
    bankroll = compute_bankroll(cfg)
    prev = load_phase_state(cfg)
    current_id = prev["phase_id"] if prev else None
    phase = evaluate_phase(
        cfg,
        bankroll["equity_nok"],
        bankroll["settled_count"],
        current_phase=current_id,
    )
    rows = load_bets(path_from_config(cfg, "bets"))
    risk = evaluate_risk(cfg, bankroll["equity_nok"], phase, rows)
    write_bankroll_state(cfg, bankroll)
    write_phase_state(cfg, phase)
    write_risk_state(cfg, risk)
    write_status(cfg, bankroll, phase, risk)
    return bankroll, phase, risk


def run_recommend(cfg: dict[str, Any], odds_path: Path, log_pending: bool = True) -> dict[str, Any]:
    bankroll, phase, risk = refresh_state(cfg)
    candidates = parse_odds_file(odds_path)
    attach_evidence(candidates, path_from_config(cfg, "evidence"))

    rows = load_bets(path_from_config(cfg, "bets"))
    picked, rejects = build_portfolio(cfg, candidates, phase, risk, rows)

    outbox = path_from_config(cfg, "outbox")
    outbox.mkdir(parents=True, exist_ok=True)
    ts = date.today().isoformat()
    place_path = outbox / f"PLACE_THESE_{ts}.md"
    reject_path = outbox / f"REJECTS_{ts}.md"

    lines = [
        f"# Bets to place — {ts}",
        "",
        f"Phase **{phase['phase_id']}** | Equity **{bankroll['equity_nok']:.2f}** | "
        f"Remaining risk **{risk['remaining_risk_nok']:.2f}** / cap **{risk['daily_risk_cap_nok']:.2f}**",
        "",
        "High odds (>2.5) appear only with grade **A** evidence + elevated EV — never auto-banned.",
        "",
        "| # | Match | Selection | Odds | Stake NOK | EV | Grade | Band |",
        "|---|-------|-----------|------|-----------|----|-------|------|",
    ]
    if not picked:
        lines.append("| — | **NO BETS** | empty slip is success | — | — | — | — | — |")
        if risk.get("reasons"):
            lines.append("")
            lines.append("Risk block: " + "; ".join(risk["reasons"]))
    else:
        for i, r in enumerate(picked, 1):
            lines.append(
                f"| {i} | {r.match} | {r.selection} | {r.decimal_odds:.2f} | "
                f"{r.stake_nok:.0f} | {r.ev:.3f} | {r.grade} | {r.odds_band} |"
            )

    lines.extend(["", "## Notes", ""])
    for r in picked:
        flag = " **HIGH ODDS**" if r.high_odds else ""
        lines.append(f"- {r.match} / {r.selection}:{flag} {r.notes}")

    place_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # stable latest pointer
    (outbox / "PLACE_THESE.md").write_text(place_path.read_text(encoding="utf-8"), encoding="utf-8")

    rej_lines = [f"# Rejects — {ts}", ""]
    for r in rejects[:100]:
        rej_lines.append(f"- {r}")
    reject_path.write_text("\n".join(rej_lines) + "\n", encoding="utf-8")

    logged = []
    if log_pending and picked:
        today = date.today().isoformat()
        now = utc_now()
        for r in picked:
            bid = make_bet_id(today, r.match, r.selection, r.decimal_odds, r.stake_nok, salt=now)
            rows.append(
                {
                    "bet_id": bid,
                    "date": today,
                    "match": r.match,
                    "selection": r.selection,
                    "decimal_odds": fmt_num(r.decimal_odds, 3),
                    "stake_nok": fmt_num(r.stake_nok, 2),
                    "result": "Pending",
                    "p_l_nok": "",
                    "payout_nok": "",
                    "sport": r.sport,
                    "market_type": r.market_type,
                    "odds_band": r.odds_band or odds_band(r.decimal_odds),
                    "research_grade": r.grade,
                    "phase": phase["phase_id"],
                    "notes": r.notes[:400],
                    "source": "recommend",
                    "created_at": now,
                    "updated_at": now,
                }
            )
            logged.append(bid)
        write_bets(path_from_config(cfg, "bets"), rows)
        refresh_state(cfg)

    return {
        "n_candidates": len(candidates),
        "n_picked": len(picked),
        "n_rejects": len(rejects),
        "place_path": str(place_path),
        "logged_bet_ids": logged,
        "phase": phase["phase_id"],
        "remaining_risk": risk["remaining_risk_nok"],
        "daily_cap": risk["daily_risk_cap_nok"],
        "equity": bankroll["equity_nok"],
    }
