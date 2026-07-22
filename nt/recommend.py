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
            segments = sync_capital_v2_state(cfg, bankroll["equity_nok"], rows, persist=True)
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
    allow_low_coverage: bool = False,
) -> dict[str, Any]:
    """
    Build place slip from odds + evidence.

    By default refuses boards with zero p_model/evidence (wrong path).
    Use force_mechanical=True only for tests or explicit override.

    Coverage Health soft-gate: when level=critical, block unless
    allow_low_coverage=True (or soft_gate disabled in config).
    """
    bankroll, phase, risk = refresh_state(cfg)
    candidates = parse_odds_file(odds_path)
    attach_evidence(candidates, path_from_config(cfg, "evidence"))

    from nt.board import board_coverage, shortlist_board
    from nt.coverage_health import (
        soft_gate_blocks_recommend,
        update_coverage_health_on_recommend,
    )
    from nt.defaults import research_cfg

    rcfg = research_cfg(cfg)
    coverage = board_coverage(candidates)
    shortlist = shortlist_board(candidates, cfg)
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
        # Still write coverage health for DeskStrip (starvation taxonomy)
        try:
            cov_health = update_coverage_health_on_recommend(
                cfg,
                candidates,
                shortlist=shortlist,
                n_picked=0,
                can_bet=bool(risk.get("can_bet")),
                emit_coverage_signal=True,
            )
        except Exception:
            cov_health = None
        return {
            "blocked": True,
            "block_reason": "no_research",
            "message": (
                "Recommend refused: no evidence/p_model on board. "
                f"Run: python run_nt.py research board --odds {odds_path} --write-scaffolds"
            ),
            "coverage": coverage,
            "coverage_health": cov_health,
            "starvation_kind": (cov_health or {}).get("starvation_kind"),
            "funnel": (cov_health or {}).get("funnel"),
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

    # Pre-pass Coverage Health for soft-gate (before portfolio spend)
    try:
        pre_health = update_coverage_health_on_recommend(
            cfg,
            candidates,
            shortlist=shortlist,
            n_picked=0,
            can_bet=bool(risk.get("can_bet")),
            emit_coverage_signal=False,
            auto_revoke=True,
        )
    except Exception:
        pre_health = None

    if (
        pre_health
        and soft_gate_blocks_recommend(pre_health, cfg)
        and not allow_low_coverage
        and not force_mechanical
    ):
        block_md = [
            f"# Bets to place — {ts}",
            "",
            "## BLOCKED — Coverage Health critical",
            "",
            "Research coverage is **critical** (mid-price lines unresearched / thin deep packs).",
            "Soft-gate refuses recommend so empty slip is not mistaken for honest no-edge.",
            "",
            f"- level: **{pre_health.get('level')}**",
            f"- shortlist_deep_pct: {pre_health.get('shortlist_deep_pct')}",
            f"- mid_unresearched_n: {pre_health.get('mid_unresearched_n')}",
            f"- starvation_kind: {pre_health.get('starvation_kind')}",
            "",
            "Deep-research the engine deep queue (preferred mid-band), then re-run recommend.",
            "Ops override: `recommend --allow-low-coverage`",
            "",
        ]
        place_path.write_text("\n".join(block_md) + "\n", encoding="utf-8")
        (outbox / "PLACE_THESE.md").write_text(place_path.read_text(encoding="utf-8"), encoding="utf-8")
        reject_path.write_text(
            f"# Rejects — {ts}\n\n- coverage soft-gate: critical\n",
            encoding="utf-8",
        )
        # Emit force_coverage after soft-gate block
        try:
            cov_health = update_coverage_health_on_recommend(
                cfg,
                candidates,
                shortlist=shortlist,
                n_picked=0,
                can_bet=bool(risk.get("can_bet")),
                emit_coverage_signal=True,
                auto_revoke=False,
            )
        except Exception:
            cov_health = pre_health
        return {
            "blocked": True,
            "block_reason": "coverage_critical",
            "message": (
                "Recommend refused: Coverage Health critical. "
                "Deep-research mid-price queue or pass --allow-low-coverage."
            ),
            "coverage": coverage,
            "coverage_health": cov_health,
            "starvation_kind": (cov_health or {}).get("starvation_kind") or "coverage_critical",
            "funnel": (cov_health or {}).get("funnel"),
            "n_raw_ev_pass": (cov_health or {}).get("n_raw_ev_pass"),
            "median_raw_ev": (cov_health or {}).get("median_raw_ev"),
            "clearable_track_share": (cov_health or {}).get("clearable_track_share"),
            "second_pass_ran": (cov_health or {}).get("second_pass_ran"),
            "n_candidates": len(candidates),
            "n_picked": 0,
            "n_rejects": len(candidates),
            "place_path": str(place_path),
            "logged_bet_ids": [],
            "phase": phase["phase_id"],
            "remaining_risk": risk["remaining_risk_nok"],
            "daily_cap": risk["daily_risk_cap_nok"],
            "equity": bankroll["equity_nok"],
            "allow_low_coverage": False,
        }

    rows = load_bets(path_from_config(cfg, "bets"))
    from nt.learning import load_learning

    learning = load_learning(cfg)
    picked, rejects = build_portfolio(cfg, candidates, phase, risk, rows, learning=learning)

    # Full run-stake audit (HV v3) — from build_portfolio side channel
    from nt.defaults import recommend_cfg
    from nt.portfolio import compute_run_stake_audit

    used_nok = sum(float(r.stake_nok) for r in picked)
    run_audit = getattr(build_portfolio, "_run_stake_audit", None)
    if not isinstance(run_audit, dict):
        rec_cfg = recommend_cfg(cfg)
        run_audit = compute_run_stake_audit(
            remaining_risk_nok=float(risk.get("remaining_risk_nok") or 0.0),
            equity_nok=float(bankroll.get("equity_nok") or risk.get("equity_nok") or 0.0),
            run_pct=float(rec_cfg["max_run_stake_pct_of_equity"]),
            used_nok=used_nok,
        )
        run_audit["soft_pack_applied"] = False
        run_audit["target_bets_per_run"] = int(rec_cfg["target_bets_per_run"])
        run_audit["n_picked"] = len(picked)
        run_audit["soft_pack_seats_hit"] = False
    else:
        run_audit = dict(run_audit)
        run_audit["run_stake_used_nok"] = used_nok
        run_audit.setdefault("n_picked", len(picked))

    lines = [
        f"# Bets to place — {ts}",
        "",
        f"Phase **{phase['phase_id']}** | Equity **{bankroll['equity_nok']:.2f}** | "
        f"Remaining risk **{risk['remaining_risk_nok']:.2f}** / cap **{risk['daily_risk_cap_nok']:.2f}**",
        "",
        (
            f"Run stake: used **{float(run_audit.get('run_stake_used_nok') or 0):.0f}** / "
            f"cap **{float(run_audit.get('run_stake_cap_nok') or 0):.0f}** "
            f"(equity cap **{float(run_audit.get('run_stake_equity_cap_nok') or 0):.0f}**, "
            f"remaining risk **{float(run_audit.get('run_stake_remaining_risk_nok') or 0):.0f}**) · "
            f"binding: **{run_audit.get('run_stake_binding') or 'n/a'}**"
        ),
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
    if run_audit.get("soft_pack_applied"):
        lines.append(
            f"- soft_pack_applied (mode): target={run_audit.get('target_bets_per_run')} "
            f"picked={run_audit.get('n_picked')} "
            f"seats_hit={run_audit.get('soft_pack_seats_hit')}"
        )

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

    # Coverage Health + clearability funnel (post-portfolio n_picked)
    no_p_share = None
    if rejects:
        def _is_no_pmodel_reject(r: Any) -> bool:
            if not isinstance(r, dict):
                return False
            reason = str(r.get("reason") or "").lower()
            return (
                "no p_model" in reason
                or "missing p_model" in reason
                or "without p_model" in reason
                or reason.strip() in ("no research", "no evidence")
            )

        no_p = sum(1 for r in rejects if _is_no_pmodel_reject(r))
        no_p_share = no_p / max(1, len(rejects))

    try:
        cov_health = update_coverage_health_on_recommend(
            cfg,
            candidates,
            shortlist=shortlist,
            n_picked=len(picked),
            can_bet=bool(risk.get("can_bet")),
            no_pmodel_reject_share=no_p_share,
            emit_coverage_signal=True,
            auto_revoke=True,
        )
    except Exception:
        cov_health = pre_health

    funnel = (cov_health or {}).get("funnel") or {}
    return {
        "blocked": False,
        "coverage": coverage,
        "coverage_health": cov_health,
        "starvation_kind": (cov_health or {}).get("starvation_kind"),
        "funnel": funnel,
        "n_raw_ev_pass": (cov_health or {}).get("n_raw_ev_pass", funnel.get("n_raw_ev_pass")),
        "median_raw_ev": (cov_health or {}).get("median_raw_ev", funnel.get("median_raw_ev")),
        "clearable_track_share": (cov_health or {}).get(
            "clearable_track_share", funnel.get("clearable_track_share")
        ),
        "second_pass_ran": (cov_health or {}).get("second_pass_ran", funnel.get("second_pass_ran")),
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
        # HV v3 run-stake audit (flat + nested for PLACE/JSON consumers)
        "run_stake_cap_nok": run_audit.get("run_stake_cap_nok"),
        "run_stake_equity_cap_nok": run_audit.get("run_stake_equity_cap_nok"),
        "run_stake_remaining_risk_nok": run_audit.get("run_stake_remaining_risk_nok"),
        "run_stake_used_nok": run_audit.get("run_stake_used_nok"),
        "run_stake_binding": run_audit.get("run_stake_binding"),
        "soft_pack_applied": bool(run_audit.get("soft_pack_applied")),
        "soft_pack_seats_hit": bool(run_audit.get("soft_pack_seats_hit")),
        "target_bets_per_run": run_audit.get("target_bets_per_run"),
        "run_stake": dict(run_audit),
        "allow_low_coverage": bool(allow_low_coverage),
    }
