from __future__ import annotations

import json
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
    # Phase 2.4: secure transfer + day/week snapshots before risk (flag-gated)
    segments = None
    try:
        from nt.capital_runtime import capital_v2_enabled, sync_capital_v2_state

        if capital_v2_enabled(cfg):
            segments = sync_capital_v2_state(
                cfg,
                bankroll["equity_nok"],
                rows,
                persist=True,
                phase_daily_risk_ceil=float(phase.get("daily_risk_ceil") or 0.0) or None,
            )
    except Exception:
        segments = None
    if segments is not None:
        risk = evaluate_risk(cfg, bankroll["equity_nok"], phase, rows, segments=segments)
    else:
        risk = evaluate_risk(cfg, bankroll["equity_nok"], phase, rows)
    write_bankroll_state(cfg, bankroll)
    write_phase_state(cfg, phase)
    write_risk_state(cfg, risk)
    write_status(cfg, bankroll, phase, risk)
    # Keep learning mults in sync with ledger (cheap recompute)
    try:
        from nt.learning import run_learning

        if (cfg.get("learning") or {}).get("enabled", True):
            run_learning(cfg, rows)
    except Exception:
        pass
    return bankroll, phase, risk


def run_recommend(
    cfg: dict[str, Any],
    odds_path: Path,
    log_pending: bool = True,
    *,
    force_mechanical: bool = False,
) -> dict[str, Any]:
    """
    Build place slip from odds + evidence.

    By default refuses boards with zero p_model/evidence (wrong path).
    Use force_mechanical=True only for tests or explicit override.
    """
    bankroll, phase, risk = refresh_state(cfg)
    candidates = parse_odds_file(odds_path)
    attach_evidence(candidates, path_from_config(cfg, "evidence"))

    from nt.board import board_coverage
    from nt.defaults import research_cfg

    rcfg = research_cfg(cfg)
    coverage = board_coverage(candidates)
    require = bool(rcfg.get("require_research_for_recommend", True)) and not force_mechanical

    outbox = path_from_config(cfg, "outbox")
    outbox.mkdir(parents=True, exist_ok=True)
    ts = date.today().isoformat()
    place_path = outbox / f"PLACE_THESE_{ts}.md"
    reject_path = outbox / f"REJECTS_{ts}.md"

    if require and not coverage.get("ready_for_recommend"):
        # Hard gate: research-first workflow
        block_md = [
            f"# Bets to place — {ts}",
            "",
            "## BLOCKED — research required first",
            "",
            "This board has **zero** candidates with `p_model` / evidence packs.",
            "Running mechanical `recommend` without research is the **wrong path**.",
            "",
            "### Correct workflow",
            "",
            "```bash",
            f"python run_nt.py research board --odds {odds_path} --write-scaffolds",
            "# … internet research → fill evidence/*.json …",
            f"python run_nt.py research ready --odds {odds_path}",
            f"python run_nt.py recommend --odds {odds_path}",
            "```",
            "",
            f"- Candidates: {coverage.get('n_candidates')}",
            f"- Matches: {', '.join(coverage.get('matches') or [])}",
            f"- With evidence: {coverage.get('n_with_evidence')} | with p_model: {coverage.get('n_with_p_model')}",
            "",
            "Empty slip after research is success. Empty slip *instead of* research is not.",
            "",
            "Override (not recommended): `recommend --force-mechanical`",
            "",
        ]
        place_path.write_text("\n".join(block_md) + "\n", encoding="utf-8")
        (outbox / "PLACE_THESE.md").write_text(place_path.read_text(encoding="utf-8"), encoding="utf-8")
        reject_path.write_text(
            f"# Rejects — {ts}\n\n- workflow block: no research packs on board\n",
            encoding="utf-8",
        )
        return {
            "blocked": True,
            "block_reason": "no_research",
            "message": (
                "Recommend refused: no evidence/p_model on board. "
                f"Run: python run_nt.py research board --odds {odds_path} --write-scaffolds"
            ),
            "coverage": coverage,
            "n_candidates": len(candidates),
            "n_picked": 0,
            "n_rejects": len(candidates),
            "place_path": str(place_path),
            "logged_bet_ids": [],
            "phase": phase["phase_id"],
            "remaining_risk": risk["remaining_risk_nok"],
            "daily_cap": risk["daily_risk_cap_nok"],
            "equity": bankroll["equity_nok"],
            "workflow": "research_board → fill_evidence → recommend",
        }

    rows = load_bets(path_from_config(cfg, "bets"))
    from nt.learning import load_learning

    learning = load_learning(cfg)
    picked, rejects = build_portfolio(cfg, candidates, phase, risk, rows, learning=learning)

    lines = [
        f"# Bets to place — {ts}",
        "",
        f"Phase **{phase['phase_id']}** | Equity **{bankroll['equity_nok']:.2f}** | "
        f"Remaining risk **{risk['remaining_risk_nok']:.2f}** / cap **{risk['daily_risk_cap_nok']:.2f}**",
        "",
        f"Research coverage: {coverage.get('n_with_p_model')}/{coverage.get('n_candidates')} "
        f"candidates have p_model.",
        "",
        "High odds (>2.5) appear only with grade **A** evidence + elevated EV — never auto-banned.",
        "",
        "| # | Match | Selection | Odds | Stake NOK | EV | Grade | Band |",
        "|---|-------|-----------|------|-----------|----|-------|------|",
    ]
    if not picked:
        lines.append("| — | **NO BETS** | empty slip is success (after research) | — | — | — | — | — |")
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

    # Human summary (capped) + full machine-readable JSONL (Phase 2 audit B8)
    rej_lines = [
        f"# Rejects — {ts}",
        "",
        f"Total rejects: **{len(rejects)}** (full log: `REJECTS_{ts}.jsonl`)",
        "",
    ]
    for r in rejects[:100]:
        rej_lines.append(f"- {r}")
    if len(rejects) > 100:
        rej_lines.append(f"- … +{len(rejects) - 100} more (see JSONL)")
    reject_path.write_text("\n".join(rej_lines) + "\n", encoding="utf-8")
    rej_jsonl = outbox / f"REJECTS_{ts}.jsonl"
    rej_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in rejects)
        + ("\n" if rejects else ""),
        encoding="utf-8",
    )
    (outbox / "REJECTS_LATEST.jsonl").write_text(
        rej_jsonl.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (outbox / "REJECTS.md").write_text(reject_path.read_text(encoding="utf-8"), encoding="utf-8")

    logged = []
    if log_pending and picked:
        from nt.analytics import infer_market
        from nt.decisions import append_decision, append_evidence_link

        # `date` on the ledger = match calendar date (kickoff date CEST), never place-time.
        place_day = date.today().isoformat()
        now = utc_now()
        for r in picked:
            # Hard gate: refuse place-time process log without p_model / market_key
            if r.p_model is None:
                rejects.append(
                    {
                        "match": r.match,
                        "selection": r.selection,
                        "reason": "place hard-gate: missing p_model (process densify)",
                    }
                )
                continue
            mk = (r.market_key or "").strip() or infer_market(r.selection or "", r.market_type or "")
            mtype = (r.market_type or "").strip() or "unknown"
            match_date = (getattr(r, "match_date", None) or "").strip()[:10]
            if not match_date or len(match_date) < 10:
                match_date = place_day
            ko = (getattr(r, "kickoff", None) or "").strip()
            note = (r.notes or "")[:400]
            if ko and "kickoff=" not in note:
                note = (note + f"; kickoff={ko}").strip("; ")[:400]
            bid = make_bet_id(match_date, r.match, r.selection, r.decimal_odds, r.stake_nok, salt=now)
            rows.append(
                {
                    "bet_id": bid,
                    "date": match_date,
                    "match": r.match,
                    "selection": r.selection,
                    "decimal_odds": fmt_num(r.decimal_odds, 3),
                    "stake_nok": fmt_num(r.stake_nok, 2),
                    "result": "Pending",
                    "p_l_nok": "",
                    "payout_nok": "",
                    "sport": r.sport,
                    "market_type": mtype,
                    "odds_band": r.odds_band or odds_band(r.decimal_odds),
                    "research_grade": r.grade,
                    "phase": phase["phase_id"],
                    "notes": note,
                    "source": "recommend",
                    "created_at": now,
                    "updated_at": now,
                }
            )
            ep = (getattr(r, "evidence_path", None) or "").strip()
            dec = append_decision(
                cfg,
                {
                    "bet_id": bid,
                    "date": match_date,
                    "match": r.match,
                    "selection": r.selection,
                    "decimal_odds": r.decimal_odds,
                    "stake_nok": r.stake_nok,
                    "p_model": float(r.p_model),
                    "p_model_source": "engine",
                    "ev": r.ev,
                    "ev_source": "engine",
                    "grade": r.grade,
                    "sport": r.sport,
                    "market_type": mtype,
                    "market_type_raw": mtype,
                    "market_key": mk,
                    "odds_band": r.odds_band,
                    "phase": phase["phase_id"],
                    "high_odds": r.high_odds,
                    "explore": r.explore,
                    "learning_stake_mult": r.learning_stake_mult,
                    "learning_ev_boost": r.learning_ev_boost,
                    "reasons": r.reasons,
                    "notes": r.notes,
                    "implied_prob": round(1.0 / r.decimal_odds, 4) if r.decimal_odds else None,
                    "evidence_path": ep,
                    "evidence_match": "hard" if ep else "none",
                    "evidence_confidence": 1.0 if ep else 0.0,
                    "backfill": False,
                },
            )
            if ep:
                append_evidence_link(
                    cfg,
                    {
                        "bet_id": bid,
                        "evidence_path": ep,
                        "match_method": "place_hard",
                        "confidence": 1.0,
                        "p_model_at_link": float(r.p_model),
                        "backfill": False,
                    },
                )
            logged.append(bid)
            _ = dec  # normalized write confirmed
        write_bets(path_from_config(cfg, "bets"), rows)
        refresh_state(cfg)

    # Phase 2.4: append-only stake_decisions.jsonl when capital_v2.enabled
    # (place path includes bet_id; dry-run still audits recommended stakes)
    try:
        from nt.capital_runtime import capital_v2_enabled, persist_stake_decisions_for_picks

        if capital_v2_enabled(cfg) and picked:
            persist_stake_decisions_for_picks(
                cfg,
                picked,
                bet_ids=logged if logged else None,
                phase_id=phase.get("phase_id"),
                risk=risk,
            )
    except Exception:
        pass

    return {
        "blocked": False,
        "coverage": coverage,
        "n_candidates": len(candidates),
        "n_picked": len(picked),
        "n_rejects": len(rejects),
        "place_path": str(place_path),
        "logged_bet_ids": logged,
        "phase": phase["phase_id"],
        "remaining_risk": risk["remaining_risk_nok"],
        "daily_cap": risk["daily_risk_cap_nok"],
        "equity": bankroll["equity_nok"],
        "force_mechanical": force_mechanical,
    }
