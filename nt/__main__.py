from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from nt.bankroll import compute_bankroll
from nt.bets_io import load_bets, validate_bets
from nt.config import load_config, path_from_config
from nt.phase import evaluate_phase, load_phase_state
from nt.recommend import refresh_state, run_recommend
from nt.risk import evaluate_risk
from nt.settle import run_settle


def cmd_status(_: argparse.Namespace) -> int:
    cfg = load_config()
    bankroll, phase, risk = refresh_state(cfg)
    print(f"Equity:     {bankroll['equity_nok']:.2f} NOK")
    print(f"Pending:    {bankroll['pending_at_risk_nok']:.2f} NOK")
    print(f"Phase:      {phase['phase_id']} ({phase.get('label','')})")
    print(f"Daily cap:  {risk['daily_risk_cap_nok']:.2f} NOK (remaining {risk['remaining_risk_nok']:.2f})")
    print(f"Can bet:    {risk['can_bet']}")
    print(f"Status:     {path_from_config(cfg, 'status')}")
    return 0


def cmd_validate(_: argparse.Namespace) -> int:
    cfg = load_config()
    rows = load_bets(path_from_config(cfg, "bets"))
    errors = validate_bets(rows)
    bankroll = compute_bankroll(cfg)
    print(f"Rows: {len(rows)} | Errors: {len(errors)}")
    print(f"Equity: {bankroll['equity_nok']:.2f} (baseline {bankroll['baseline_nok']} + PL {bankroll['realized_pl_nok']:+.2f})")
    for e in errors[:20]:
        print(" ERROR:", e)
    return 1 if errors else 0


def cmd_recommend(args: argparse.Namespace) -> int:
    cfg = load_config()
    odds = Path(args.odds)
    if not odds.exists():
        print(f"Odds file not found: {odds}", file=sys.stderr)
        return 2
    result = run_recommend(
        cfg,
        odds,
        log_pending=not args.dry_run,
        force_mechanical=bool(getattr(args, "force_mechanical", False)),
    )
    print(json.dumps(result, indent=2, default=str))
    print(f"\nPlace slip: {result['place_path']}")
    if result.get("blocked"):
        print(f"\n*** BLOCKED: {result.get('message')} ***", file=sys.stderr)
        return 3
    if args.dry_run:
        print("(dry-run: pending bets not logged)")
    return 0


def cmd_settle(args: argparse.Namespace) -> int:
    from nt.settle import build_pending_settle_draft, run_settle_items

    cfg = load_config()

    if getattr(args, "list_fetchers", False):
        from nt.results_fetch import list_fetchers

        print(json.dumps({"fetchers": list_fetchers()}, indent=2))
        return 0

    # Subcommands via flags: draft / apply-json
    if getattr(args, "draft", False):
        draft = build_pending_settle_draft(cfg, auto_fetch=not getattr(args, "no_fetch", False))
        print(json.dumps(draft, indent=2, default=str))
        return 0

    if getattr(args, "items_json", None):
        path = Path(args.items_json)
        if not path.exists():
            print(f"Items JSON not found: {path}", file=sys.stderr)
            return 2
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("results") or data.get("items") or []
        result = run_settle_items(cfg, items)
        print(json.dumps(result, indent=2, default=str))
        return 0 if not result.get("errors") else 1

    path = Path(args.results) if args.results else None
    if not path or not path.exists():
        print("Results file not found. Use --results PATH or --draft / --items-json", file=sys.stderr)
        return 2
    result = run_settle(cfg, path)
    print(json.dumps(result, indent=2, default=str))
    return 0 if not result["errors"] else 1


def cmd_refresh(_: argparse.Namespace) -> int:
    cfg = load_config()
    bankroll, phase, risk = refresh_state(cfg)
    print(json.dumps({"bankroll": bankroll, "phase": phase, "risk": risk}, indent=2))
    return 0


def cmd_capital(args: argparse.Namespace) -> int:
    """capital_v2 operator tools: status / unfreeze / unlock-secure / segments."""
    from nt.capital_runtime import capital_v2_enabled, manual_unlock_secure, unfreeze_capital
    from nt.capital_segments import load_segments, segments_path
    from nt.capital_v2 import capital_v2_cfg

    cfg = load_config()
    v2 = capital_v2_cfg(cfg)
    sub = getattr(args, "capital_cmd", None) or ""

    if sub == "status":
        segs = load_segments(cfg)
        bankroll, phase, risk = refresh_state(cfg)
        print(
            json.dumps(
                {
                    "capital_v2_enabled": capital_v2_enabled(cfg),
                    "rule_bundle_version": v2.get("rule_bundle_version"),
                    "config_enabled_flag": bool((cfg.get("capital_v2") or {}).get("enabled")),
                    "secure_nok": segs.get("secure_nok"),
                    "unit_hwm_reset_equity_nok": segs.get("unit_hwm_reset_equity_nok"),
                    "secure_lock_settled_count": segs.get("secure_lock_settled_count"),
                    "last_manual_unlock_at": segs.get("last_manual_unlock_at"),
                    "freeze": segs.get("freeze"),
                    "day_snapshot": segs.get("day_snapshot"),
                    "week_snapshot": segs.get("week_snapshot"),
                    "risk": {
                        k: risk.get(k)
                        for k in (
                            "size_mode",
                            "remaining_risk_nok",
                            "drawdown_from_peak",
                            "daily_loss_limit_nok",
                            "weekly_loss_limit_nok",
                            "portfolio_open_room_nok",
                            "working_equity_nok",
                            "riskable_liquid_nok",
                            "can_bet",
                            "stopped",
                        )
                        if k in risk
                    },
                    "equity_nok": bankroll.get("equity_nok"),
                    "phase_id": phase.get("phase_id"),
                    "segments_path": str(segments_path(cfg)),
                },
                indent=2,
                default=str,
            )
        )
        return 0

    if sub == "unfreeze":
        if not bool(args.confirm):
            print(
                "Refusing unfreeze without --confirm (manual freeze clear is fail-closed).",
                file=sys.stderr,
            )
            return 2
        result = unfreeze_capital(
            cfg,
            reason=str(args.reason or "manual_unfreeze"),
            actor=str(args.actor or "cli"),
        )
        # Recompute risk so freeze_manual clears in risk.json when v2 enabled
        bankroll, phase, risk = refresh_state(cfg)
        result["risk_size_mode"] = risk.get("size_mode")
        result["can_bet"] = risk.get("can_bet")
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if sub in ("unlock-secure", "unlock_secure"):
        if not bool(args.confirm):
            print(
                "Refusing unlock-secure without --confirm (releases secure → working).",
                file=sys.stderr,
            )
            return 2
        result = manual_unlock_secure(
            cfg,
            reason=str(args.reason or "manual_unlock"),
            actor=str(args.actor or "cli"),
            force=bool(getattr(args, "force", False)),
        )
        if result.get("ok"):
            # refresh may re-evaluate capital; defer_secure_skim skips same-tick re-skim
            bankroll, phase, risk = refresh_state(cfg)
            result["riskable_liquid_nok"] = risk.get("riskable_liquid_nok")
            result["working_equity_nok"] = risk.get("working_equity_nok")
            result["secure_nok_after_refresh"] = risk.get("secure_nok")
            try:
                from nt.capital_segments import load_segments as _load_segs

                segs_after = _load_segs(cfg)
                sync = segs_after.get("_last_sync") or {}
                result["secure_unlock"] = sync.get("secure_unlock")
                result["secure_transfer"] = sync.get("secure_transfer")
                result["skim_deferred_after_unlock"] = sync.get(
                    "skim_deferred_after_unlock"
                )
            except Exception:
                pass
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if sub == "segments":
        segs = load_segments(cfg)
        print(json.dumps(segs, indent=2, default=str))
        return 0

    print(f"Unknown capital subcommand: {sub}", file=sys.stderr)
    return 2


def cmd_place_ack(args: argparse.Namespace) -> int:
    """Pending → ConfirmedPlaced (ticket confirmed live on Norsk Tipping)."""
    from nt.ledger_ops import place_ack

    cfg = load_config()
    ids = [x.strip() for x in (args.ids or "").split(",") if x.strip()] if args.ids else None
    if not ids and not args.match:
        print("Provide --ids bet_id[,bet_id...] and/or --match substring", file=sys.stderr)
        return 2
    result = place_ack(
        cfg,
        ids=ids,
        match_substr=args.match,
        dry_run=bool(args.dry_run),
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


def cmd_abandon(args: argparse.Namespace) -> int:
    """Pending/ConfirmedPlaced → Abandoned (never placed; frees risk; P/L 0; keeps audit row)."""
    from nt.ledger_ops import abandon

    cfg = load_config()
    ids = [x.strip() for x in (args.ids or "").split(",") if x.strip()] if args.ids else None
    if not ids and not args.match:
        print("Provide --ids bet_id[,bet_id...] and/or --match substring", file=sys.stderr)
        return 2
    result = abandon(
        cfg,
        ids=ids,
        match_substr=args.match,
        reason=args.reason or "missed_prematch",
        dry_run=bool(args.dry_run),
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


def cmd_learn(args: argparse.Namespace) -> int:
    """Recompute sport/market/band multipliers from the ledger."""
    from nt.learning import learning_path, run_learning
    from nt.settlement_review import apply_learning_proposal, load_learning_proposals

    cfg = load_config()

    if getattr(args, "proposals", False):
        payload = load_learning_proposals(cfg)
        print(json.dumps(payload, indent=2, default=str))
        return 0

    if getattr(args, "accept", None):
        res = apply_learning_proposal(cfg, args.accept, action="accept")
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1

    if getattr(args, "reject", None):
        res = apply_learning_proposal(cfg, args.reject, action="reject")
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1

    payload = run_learning(cfg)
    summary = payload.get("summary") or {}
    print(
        json.dumps(
            {
                "updated_at": payload.get("updated_at"),
                "n_settled": summary.get("n_settled"),
                "era_roi": summary.get("era_roi"),
                "n_blocked_sports": summary.get("n_blocked_sports"),
                "best_sports": summary.get("best_sports"),
                "worst_sports": summary.get("worst_sports"),
                "layers": summary.get("layers"),
                "lessons": payload.get("lessons"),
                "path": str(learning_path(cfg)),
            },
            indent=2,
        )
    )
    return 0


def cmd_backfill_decisions(args: argparse.Namespace) -> int:
    """Rebuild missing bet_decisions.jsonl rows from ledger notes (+ optional market_key densify)."""
    from nt.decisions import backfill_decisions_from_notes, densify_market_keys

    cfg = load_config()
    dry = bool(getattr(args, "dry_run", False))
    result = backfill_decisions_from_notes(cfg, dry_run=dry)
    densify = densify_market_keys(cfg, dry_run=dry)
    print(
        json.dumps(
            {"notes_backfill": result, "market_key_densify": densify},
            indent=2,
            default=str,
        )
    )
    if dry:
        print("(dry-run: no side-car writes)")
    return 0


def cmd_backfill_evidence_pmodel(args: argparse.Namespace) -> int:
    """Soft-match evidence packs → p_model (default dry-run; never touches bets.csv)."""
    from nt.forensic import audit_evidence_pmodel, write_audit_markdown

    cfg = load_config()
    # Default dry-run=True unless --write is passed
    dry = not bool(getattr(args, "write", False))
    min_c = float(getattr(args, "min_confidence", 0.85) or 0.85)
    report = audit_evidence_pmodel(
        cfg,
        min_confidence=min_c,
        dry_run=dry,
        include_borderline=True,
    )
    outbox = path_from_config(cfg, "outbox")
    md_path = outbox / "AUDIT_evidence_pmodel.md"
    json_path = outbox / "AUDIT_evidence_pmodel.json"
    write_audit_markdown(report, md_path)
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    # Compact console summary
    c = report["coverage"]
    r = report["results"]
    print(
        json.dumps(
            {
                "dry_run": report["dry_run"],
                "min_confidence": report["min_confidence"],
                "coverage": c,
                "results": r,
                "by_method": report.get("by_method"),
                "false_positive_risk": report.get("false_positive_risk", {}).get("level"),
                "audit_md": str(md_path),
                "audit_json": str(json_path),
            },
            indent=2,
        )
    )
    print(f"\nFull audit: {md_path}")
    if dry:
        print("(dry-run: no side-car writes — pass --write only after review)")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    from nt.analyze import run_analyze

    cfg = load_config()
    report = run_analyze(cfg, write_outbox=not args.no_write)
    # Print markdown (human) + optional compact JSON footer
    print(report.get("markdown") or json.dumps(report, indent=2, default=str))
    if args.json:
        slim = {k: v for k, v in report.items() if k != "markdown"}
        print("\n--- JSON ---\n" + json.dumps(slim, indent=2, default=str))
    if report.get("path"):
        print(f"\nWrote: {report['path']}")
    return 0


def cmd_project(args: argparse.Namespace) -> int:
    from nt.project import run_project

    cfg = load_config()
    result = run_project(
        cfg,
        years=args.years,
        sims=args.sims,
        roi=args.roi,
        bets_per_week=args.bets_per_week,
        avg_odds=args.avg_odds,
        seed=args.seed,
        write_outbox=not args.no_write,
    )
    print(result.get("markdown") or json.dumps(result, indent=2, default=str))
    if result.get("path"):
        print(f"\nWrote: {result['path']}")
    return 0


def cmd_edges(args: argparse.Namespace) -> int:
    from nt.edges import query_edges, render_edges_md, summarize_edges

    cfg = load_config()
    rows = query_edges(
        cfg,
        last=args.last,
        result=args.result,
        phase=args.phase,
        grade=args.grade,
        q=args.query,
        sport=args.sport,
    )
    if args.json:
        print(json.dumps({"summary": summarize_edges(rows), "rows": rows}, indent=2, default=str))
    else:
        print(render_edges_md(rows, title=f"Edges (last matched, n={len(rows)})"))
    return 0


def cmd_research(args: argparse.Namespace) -> int:
    from nt.research import (
        checklist_for,
        critique_pack,
        list_sources,
        p_model_report,
        render_sources_md,
        scaffold_evidence,
        write_research_pack,
    )

    cfg = load_config()
    sub = args.research_cmd

    if sub == "sources":
        print(render_sources_md(args.sport))
        return 0

    if sub == "checklist":
        print(json.dumps({"sport": args.sport, "checklist": checklist_for(args.sport)}, indent=2))
        return 0

    if sub == "scaffold":
        if not args.match or not args.selection:
            print("--match and --selection required", file=sys.stderr)
            return 2
        result = scaffold_evidence(
            cfg,
            match=args.match,
            selection=args.selection,
            p_model=args.p_model,
            league=args.league or "",
            sport=args.sport,
            odds=args.odds_ref,
            write=args.write,
            filename=args.filename,
            overwrite=bool(getattr(args, "overwrite", False)),
        )
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if sub in ("write-pack", "write_pack"):
        if not args.match or not args.selection:
            print("--match and --selection required", file=sys.stderr)
            return 2
        if args.p_model is None:
            print("--p-model required for write-pack", file=sys.stderr)
            return 2
        result = write_research_pack(
            cfg,
            match=args.match,
            selection=args.selection,
            p_model=float(args.p_model),
            sport=args.sport or "football",
            odds=args.odds_ref,
            summary=args.summary or "",
            failure_modes=args.failure_modes or "",
            availability_status=args.availability_status or "predicted",
            availability_notes=args.availability_notes or "",
            context_risk=args.context_risk or "low",
            script_lean=args.script_lean or "neutral",
            selection_vs_script=args.selection_vs_script or "agree",
            base_rate_conflict=bool(args.base_rate_conflict),
            league=args.league or "",
            notes=args.notes or "",
            filename=args.filename,
            overwrite=not bool(args.no_overwrite),
        )
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    if sub == "p-model":
        if args.odds is None or args.p is None:
            print("--odds and --p required", file=sys.stderr)
            return 2
        print(json.dumps(p_model_report(cfg, float(args.odds), float(args.p)), indent=2))
        return 0

    if sub == "critique":
        path = Path(args.path)
        if not path.exists():
            print(f"Not found: {path}", file=sys.stderr)
            return 2
        odds = float(args.odds) if args.odds is not None else 1.90
        print(json.dumps(critique_pack(cfg, path, odds=odds), indent=2, default=str))
        return 0

    if sub == "combo-policy":
        from nt.combos import combo_policy_summary

        bankroll, phase, _risk = refresh_state(cfg)
        print(json.dumps(combo_policy_summary(cfg, phase), indent=2))
        return 0

    if sub == "market-scan":
        from nt.market_coverage import render_scan_markdown, run_market_coverage

        odds = Path(args.odds)
        if not odds.exists():
            print(f"Odds file not found: {odds}", file=sys.stderr)
            return 2
        payload = run_market_coverage(
            cfg,
            odds,
            match=getattr(args, "match", None) or None,
            write=not getattr(args, "no_write", False),
            high_volume_threshold=int(
                getattr(args, "threshold", None) or 40
            ),
            top_n_matches=int(getattr(args, "top", None) or 5),
        )
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, default=str))
        else:
            scans = payload.get("scans") or (
                [payload["scan"]] if payload.get("scan") else []
            )
            if not scans:
                print(json.dumps(payload, indent=2, default=str))
            else:
                for sc in scans:
                    print(render_scan_markdown(sc))
                    print()
                print(
                    f"Matches scanned: {len(scans)} · "
                    f"high-volume in file: {payload.get('n_high_volume_matches', 0)}"
                )
                if payload.get("written"):
                    print("Wrote:", *payload["written"][:6], sep="\n  ")
        return 0

    if sub == "board":
        from nt.board import run_board_research
        from nt.defaults import research_cfg
        from nt.market_coverage import run_market_coverage

        odds = Path(args.odds)
        if not odds.exists():
            print(f"Odds file not found: {odds}", file=sys.stderr)
            return 2
        rcfg = research_cfg(cfg)
        # Market Coverage Agent: auto-scan high-volume matches before shortlist
        coverage_payload = None
        if not getattr(args, "skip_market_scan", False):
            try:
                coverage_payload = run_market_coverage(
                    cfg,
                    odds,
                    match=None,
                    write=not args.no_write,
                    high_volume_threshold=int(
                        rcfg.get("high_volume_market_threshold") or 40
                    ),
                    top_n_matches=int(rcfg.get("market_scan_top_n") or 5),
                )
            except Exception as ex:  # noqa: BLE001
                coverage_payload = {"error": str(ex)}
        result = run_board_research(
            cfg,
            odds,
            write_scaffolds=bool(args.write_scaffolds),
            write_report=not args.no_write,
            max_per_match=int(args.max_per_match or rcfg.get("board_max_per_match") or 5),
            max_total=int(args.max_total or rcfg.get("board_max_total") or 16),
            market_coverage=coverage_payload,
        )
        # Human-first: print markdown report
        print(result.get("markdown") or json.dumps(result, indent=2, default=str))
        if args.json:
            slim = {k: v for k, v in result.items() if k != "markdown"}
            print("\n--- JSON ---\n" + json.dumps(slim, indent=2, default=str))
        if result.get("report_path"):
            print(f"\nWrote: {result['report_path']}")
        return 0

    if sub == "ready":
        from nt.board import research_readiness

        odds = Path(args.odds)
        if not odds.exists():
            print(f"Odds file not found: {odds}", file=sys.stderr)
            return 2
        result = research_readiness(cfg, odds)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("allow_recommend") else 1

    if sub == "light":
        from nt.board import run_board_research
        from nt.defaults import research_cfg
        from nt.light_research import merge_deep_status, render_light_markdown, run_light_research

        odds = Path(args.odds)
        if not odds.exists():
            print(f"Odds file not found: {odds}", file=sys.stderr)
            return 2
        rcfg = research_cfg(cfg)
        # Build shortlist without nested auto-light to avoid double-run noise
        # Temporarily disable auto light inside board
        cfg2 = dict(cfg)
        res_sec = dict(cfg2.get("research") or {})
        tiers = dict(res_sec.get("tiers") or {})
        tiers["auto_light_on_board"] = False
        res_sec["tiers"] = tiers
        cfg2["research"] = res_sec
        board = run_board_research(
            cfg2,
            odds,
            write_scaffolds=False,
            write_report=False,
            max_per_match=int(rcfg.get("board_max_per_match") or 6),
            max_total=int(rcfg.get("board_max_total") or 24),
            market_coverage=None,
        )
        shortlist = board.get("shortlist") or []
        payload = run_light_research(
            cfg,
            odds,
            shortlist,
            write=not getattr(args, "no_write", False),
        )
        if getattr(args, "merge_deep", False):
            payload = merge_deep_status(cfg)
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, default=str))
        else:
            print(render_light_markdown(payload))
            if payload.get("md_path"):
                print(f"\nWrote: {payload['md_path']}")
        return 0 if payload.get("coverage_ok", True) else 1

    if sub in ("scan-merge", "scan_merge"):
        from nt.scan_merge import run_scan_merge

        odds = Path(args.odds)
        if not odds.exists():
            print(f"Odds file not found: {odds}", file=sys.stderr)
            return 2
        payload = run_scan_merge(
            cfg,
            odds,
            agent_a=getattr(args, "agent_a", None) or None,
            agent_b=getattr(args, "agent_b", None) or None,
            agent_c=getattr(args, "agent_c", None) or None,
            agent_d=getattr(args, "agent_d", None) or None,
            agents_dir=getattr(args, "agents_dir", None) or None,
            out=getattr(args, "out", None) or None,
            out_json=getattr(args, "out_json", None) or None,
            use_live_open=not bool(getattr(args, "no_live_open", False)),
            write=not bool(getattr(args, "no_write", False)),
        )
        if getattr(args, "json", False):
            slim = {k: v for k, v in payload.items() if k != "markdown"}
            print(json.dumps(slim, indent=2, default=str))
        else:
            print(payload.get("markdown") or json.dumps(payload, indent=2, default=str))
            if payload.get("md_path"):
                print(f"\nWrote: {payload['md_path']}")
            if payload.get("json_path"):
                print(f"JSON:  {payload['json_path']}")
        return 0

    if sub in ("scan-depth", "scan_depth"):
        from nt.scan_merge import run_scan_depth

        odds = Path(args.odds)
        if not odds.exists():
            print(f"Odds file not found: {odds}", file=sys.stderr)
            return 2
        min_lines = getattr(args, "min_lines", None)
        payload = run_scan_depth(
            cfg,
            odds,
            min_lines=int(min_lines) if min_lines is not None else None,
        )
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, default=str))
        else:
            print(f"# scan-depth — {odds.name}")
            print(f"total_lines: {payload.get('total_lines')}")
            print(f"match_n: {payload.get('match_n')}")
            print(f"max_lines_per_match: {payload.get('max_lines_per_match')}")
            print(f"min_lines: {payload.get('min_lines')}")
            print(f"spawn_agent_d: {payload.get('spawn_agent_d')}")
            print(f"agent_d: {payload.get('agent_d')}")
            over = payload.get("matches_over_threshold") or []
            if over:
                print("matches_over_threshold:")
                per = payload.get("per_match") or {}
                for m in over:
                    print(f"  - {m}: {per.get(m)}")
            else:
                print("matches_over_threshold: (none)")
        return 0

    if sub in ("match-intel", "match_intel"):
        from nt.match_intel.pipeline import run_match_intel_batch

        odds = Path(args.odds) if getattr(args, "odds", None) else None
        if odds is not None and not odds.exists():
            print(f"Odds file not found: {odds}", file=sys.stderr)
            return 2
        match_list: list[str] = []
        raw_matches = getattr(args, "matches", None) or getattr(args, "match", None)
        if raw_matches:
            if isinstance(raw_matches, list):
                match_list = [str(x).strip() for x in raw_matches if str(x).strip()]
            else:
                # support "A vs B" or "A vs B; C vs D"
                for part in re.split(r"[;|]", str(raw_matches)):
                    part = part.strip()
                    if part:
                        match_list.append(part)
        if not odds and not match_list:
            print("--odds or --matches required", file=sys.stderr)
            return 2
        out_dir = getattr(args, "out_dir", None) or None
        # CLI network / URL overrides (PR-1); committed config stays allow_network: false
        allow_net = None
        if bool(getattr(args, "allow_network", False)):
            allow_net = True
        elif bool(getattr(args, "no_network", False)):
            allow_net = False
        # Optional fetch prefer override
        fetch_prefer = getattr(args, "fetch", None)
        if fetch_prefer:
            research = dict(cfg.get("research") or {})
            mi_cfg = dict(research.get("match_intel") or {})
            fetch_cfg = dict(mi_cfg.get("fetch") or {})
            fetch_cfg["prefer"] = str(fetch_prefer).strip().lower()
            mi_cfg["fetch"] = fetch_cfg
            research["match_intel"] = mi_cfg
            cfg = dict(cfg)
            cfg["research"] = research
        payload = run_match_intel_batch(
            cfg,
            odds_path=odds,
            matches=match_list or None,
            sport=getattr(args, "sport", None) or None,
            out_dir=out_dir,
            force=bool(getattr(args, "force", False)),
            write=not bool(getattr(args, "no_write", False)),
            fixture_dir=getattr(args, "fixture_dir", None) or None,
            max_matches=getattr(args, "max_matches", None),
            url=getattr(args, "url", None) or None,
            allow_network=allow_net,
            write_aliases=bool(getattr(args, "write_aliases", False)) or None,
        )
        if getattr(args, "json", False):
            slim = {
                "ok": payload.get("ok"),
                "summary": payload.get("summary"),
                "cards": [
                    {
                        "match": c.get("match"),
                        "match_key": c.get("match_key"),
                        "sport": c.get("sport"),
                        "coverage": c.get("coverage"),
                        "path": c.get("_path"),
                        "errors": (c.get("extraction") or {}).get("errors"),
                        "process_miss": (c.get("extraction") or {}).get("process_miss"),
                        "process_miss_reason": (c.get("extraction") or {}).get(
                            "process_miss_reason"
                        ),
                        "kickoff_local": c.get("kickoff_local"),
                    }
                    for c in (payload.get("cards") or [])
                ],
            }
            print(json.dumps(slim, indent=2, default=str))
        else:
            summary = payload.get("summary") or {}
            grades = summary.get("grades") or {}
            print("# match-intel")
            print(f"n: {summary.get('n', 0)}")
            print(
                "grades: "
                + " ".join(f"{g}={grades.get(g, 0)}" for g in ("A", "B", "C", "D", "F"))
            )
            print(f"process_miss_n: {summary.get('process_miss_n', 0)}")
            errs = summary.get("errors") or {}
            if errs:
                print(
                    "errors: "
                    + " ".join(f"{k}={v}" for k, v in sorted(errs.items(), key=lambda x: (-x[1], x[0])))
                )
            if summary.get("out_dir"):
                print(f"out_dir: {summary['out_dir']}")
            if summary.get("index_path"):
                print(f"index: {summary['index_path']}")
            for c in payload.get("cards") or []:
                cov = c.get("coverage") or {}
                ext = c.get("extraction") or {}
                pm = " process_miss" if ext.get("process_miss") else ""
                reason = ext.get("process_miss_reason") or ""
                pm_s = f"{pm}({reason})" if pm and reason else pm
                print(
                    f"  {cov.get('grade', '?')}  score={cov.get('score', 0):.2f}  "
                    f"{c.get('match')}  [{c.get('sport')}]{pm_s}"
                )
                if c.get("_path"):
                    print(f"      → {c['_path']}")
        return 0 if payload.get("ok") else 1

    if sub in ("apply-quality-veto", "apply_quality_veto"):
        from nt.research_quality_gate import apply_quality_veto

        day = getattr(args, "date", None) or date.today().isoformat()
        veto_file = getattr(args, "veto_file", None) or None
        dry_run = bool(getattr(args, "dry_run", False))
        payload = apply_quality_veto(
            cfg,
            day,
            dry_run=dry_run,
            veto_file=veto_file,
        )
        print(json.dumps(payload, indent=2, default=str))
        if payload.get("applied_path"):
            print(f"\nApplied marker: {payload['applied_path']}")
        return 0 if payload.get("ok") else 1

    if sub in ("assert-can-bet", "assert_can_bet"):
        return cmd_assert_can_bet(args)

    print(f"Unknown research subcommand: {sub}", file=sys.stderr)
    return 2


def cmd_assert_can_bet(args: argparse.Namespace) -> int:
    """
    Exit 0 if risk can_bet is true, else exit 1 and print reasons.

    Default: refresh_state (same path as status). ``--no-refresh`` reads risk.json.
    """
    from nt.research_quality_gate import assert_can_bet_exit_code, assert_can_bet_snapshot

    cfg = load_config()
    refresh = not bool(getattr(args, "no_refresh", False))
    snap = assert_can_bet_snapshot(cfg, refresh=refresh)
    print(json.dumps(snap, indent=2, default=str))
    code = assert_can_bet_exit_code(snap)
    if code != 0:
        reasons = snap.get("reasons") or []
        print(
            f"\n*** can_bet=false — halt research/place ***"
            + (f"\nreasons: {reasons}" if reasons else ""),
            file=sys.stderr,
        )
    return code


def cmd_risk(args: argparse.Namespace) -> int:
    """risk assert-can-bet (design §5.1 alias of research assert-can-bet)."""
    sub = getattr(args, "risk_cmd", None)
    if sub in ("assert-can-bet", "assert_can_bet"):
        return cmd_assert_can_bet(args)
    print(f"Unknown risk subcommand: {sub}", file=sys.stderr)
    return 2


def cmd_simulate_tennis(args: argparse.Namespace) -> int:
    """Tennis sim → suggested p_model (does not place bets)."""
    from nt.sim_tennis import TennisSimInputs, simulate_tennis

    inp = TennisSimInputs(
        match=getattr(args, "match", "") or "",
        player_a=getattr(args, "player_a", "") or getattr(args, "home", "") or "",
        player_b=getattr(args, "player_b", "") or getattr(args, "away", "") or "",
        hold_a=float(getattr(args, "hold_a", 0.78) or 0.78),
        hold_b=float(getattr(args, "hold_b", 0.78) or 0.78),
        best_of=int(getattr(args, "best_of", 3) or 3),
        elo_diff=getattr(args, "elo_diff", None),
        source_quality=getattr(args, "source_quality", "medium") or "medium",
        notes=getattr(args, "notes", "") or "",
        selection=getattr(args, "selection", None),
        odds_ref=getattr(args, "odds_ref", None),
    )
    result = simulate_tennis(inp)
    print(json.dumps(result, indent=2, ensure_ascii=False) if getattr(args, "json", False) else (
        f"# Tennis sim (suggestion only)\n\n"
        f"**Match:** {result['match']}\n"
        f"**p_model:** {result['p_model']} · conf {result['confidence']}\n"
        f"**Markets:** {result['markets']}\n"
        f"**Warnings:** {result['warnings']}\n"
        f"\n_{result['disclaimer']}_\n"
    ))
    return 0


def cmd_simulate_basketball(args: argparse.Namespace) -> int:
    """Basketball sim → suggested p_model (does not place bets)."""
    from nt.sim_basketball import BasketballSimInputs, simulate_basketball

    inp = BasketballSimInputs(
        match=getattr(args, "match", "") or "",
        home=getattr(args, "home", "") or "",
        away=getattr(args, "away", "") or "",
        mean_margin=float(getattr(args, "margin", 0.0) or 0.0),
        margin_sd=float(getattr(args, "margin_sd", 12.0) or 12.0),
        mean_total=float(getattr(args, "mean_total", 220.0) or 220.0),
        total_sd=float(getattr(args, "total_sd", 18.0) or 18.0),
        handicap_line=getattr(args, "handicap_line", None),
        total_line=getattr(args, "total_line", None),
        source_quality=getattr(args, "source_quality", "medium") or "medium",
        notes=getattr(args, "notes", "") or "",
        selection=getattr(args, "selection", None),
        odds_ref=getattr(args, "odds_ref", None),
    )
    if not inp.match and inp.home and inp.away:
        inp.match = f"{inp.home} vs {inp.away}"
    result = simulate_basketball(inp)
    print(json.dumps(result, indent=2, ensure_ascii=False) if getattr(args, "json", False) else (
        f"# Basketball sim (suggestion only)\n\n"
        f"**Match:** {result['match']}\n"
        f"**p_model:** {result['p_model']} · conf {result['confidence']}\n"
        f"**Markets:** {result['markets']}\n"
        f"**Warnings:** {result['warnings']}\n"
        f"\n_{result['disclaimer']}_\n"
    ))
    return 0


def cmd_control_signals(args: argparse.Namespace) -> int:
    """List / emit / revoke ControlSignals (temp_gate_raise)."""
    from nt.control_signals import (
        emit_temp_gate_raise,
        load_active_signals,
        revoke_signals,
    )

    cfg = load_config()
    sub = getattr(args, "cs_cmd", None) or ""
    if sub == "list":
        active = load_active_signals(cfg)
        payload = {"n": len(active), "signals": active}
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"# ControlSignals · {len(active)} active\n")
            for s in active:
                print(
                    f"- {s.get('sport')}/{s.get('market') or '—'} "
                    f"min_ev+{s.get('min_ev_raise')} force_confirmed={s.get('force_confirmed_lineup')} "
                    f"src={s.get('source')} exp={s.get('expires_at')} bet={s.get('bet_id') or '—'}"
                )
        return 0
    if sub == "emit":
        out = emit_temp_gate_raise(
            cfg,
            sport=str(getattr(args, "sport", "") or ""),
            market=str(getattr(args, "market", "") or ""),
            bet_id=str(getattr(args, "bet_id", "") or ""),
            source=str(getattr(args, "source", "manual") or "manual"),
            process_root_cause=str(getattr(args, "reason", "") or ""),
        )
        print(json.dumps(out, indent=2, default=str))
        return 0 if out.get("ok") else 1
    if sub == "revoke":
        out = revoke_signals(
            cfg,
            sport=str(getattr(args, "sport", "") or ""),
            market=str(getattr(args, "market", "") or ""),
            revoke_all=bool(getattr(args, "all", False)),
            actor=str(getattr(args, "actor", "cli") or "cli"),
            reason=str(getattr(args, "reason", "manual_expire") or "manual_expire"),
        )
        print(json.dumps(out, indent=2, default=str))
        return 0 if out.get("ok") else 1
    print(f"Unknown control-signals subcommand: {sub}", file=sys.stderr)
    return 2


def cmd_failures(args: argparse.Namespace) -> int:
    """Indexed past-failure rebuild / query."""
    from nt.failure_index import query_failures, rebuild_failure_index

    cfg = load_config()
    sub = getattr(args, "failures_cmd", None) or getattr(args, "subcmd", None)
    if sub == "rebuild" or getattr(args, "rebuild", False):
        out = rebuild_failure_index(cfg)
        print(json.dumps(out, indent=2))
        return 0
    rows = query_failures(
        cfg,
        q=getattr(args, "q", "") or "",
        sport=getattr(args, "sport", None),
        kind=getattr(args, "kind", None),
        limit=int(getattr(args, "limit", 20) or 20),
    )
    if getattr(args, "json", False):
        print(json.dumps({"n": len(rows), "hits": rows}, indent=2, ensure_ascii=False))
    else:
        print(f"# Failures query · {len(rows)} hits\n")
        for r in rows:
            print(
                f"- [{r.get('kind')}] {r.get('match')} / {r.get('selection')} "
                f"· {r.get('sport')} · {r.get('bet_id') or r.get('id')}"
            )
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Football match simulation → suggested p_model for evidence."""
    sport = (getattr(args, "sport", None) or "football").lower()
    if sport in ("tennis",):
        return cmd_simulate_tennis(args)
    if sport in ("basketball", "nba", "wnba"):
        return cmd_simulate_basketball(args)
    from nt.sim_football import (
        SimInputs,
        load_sim_input_file,
        p_model_for_selection,
        render_sim_markdown,
        result_to_dict,
        save_sim_audit,
        simulate_match,
        write_evidence_from_sim,
    )

    cfg = load_config()
    if args.input:
        path = Path(args.input)
        if not path.exists():
            print(f"Input not found: {path}", file=sys.stderr)
            return 2
        inp = load_sim_input_file(path)
    else:
        if args.lambda_home is None and args.home_xg_for is None:
            print(
                "Provide --input YAML/JSON, or --lambda-home/--lambda-away, "
                "or xG flags (--home-xg-for …).",
                file=sys.stderr,
            )
            return 2
        inp = SimInputs(
            match=args.match or "",
            home=args.home or "",
            away=args.away or "",
            lambda_home=args.lambda_home,
            lambda_away=args.lambda_away,
            home_xg_for=args.home_xg_for,
            home_xg_against=args.home_xg_against,
            away_xg_for=args.away_xg_for,
            away_xg_against=args.away_xg_against,
            league_avg_xg=args.league_avg_xg if args.league_avg_xg is not None else 1.35,
            home_advantage=args.home_advantage if args.home_advantage is not None else 1.08,
            form_home=args.form_home if args.form_home is not None else 1.0,
            form_away=args.form_away if args.form_away is not None else 1.0,
            motivation_home=args.motivation_home if args.motivation_home is not None else 1.0,
            motivation_away=args.motivation_away if args.motivation_away is not None else 1.0,
            rest_home=args.rest_home if args.rest_home is not None else 1.0,
            rest_away=args.rest_away if args.rest_away is not None else 1.0,
            injury_home=args.injury_home if args.injury_home is not None else 1.0,
            injury_away=args.injury_away if args.injury_away is not None else 1.0,
            rho=args.rho if args.rho is not None else -0.05,
            league=args.league or "",
            source_quality=args.source_quality or "medium",
            notes=args.notes or "",
        )
        if not inp.match and inp.home and inp.away:
            inp.match = f"{inp.home} vs {inp.away}"

    try:
        result = simulate_match(inp, cfg)
    except Exception as e:
        print(f"Simulation error: {e}", file=sys.stderr)
        return 1

    save_sim_audit(cfg, result)
    md = render_sim_markdown(result, cfg)

    if not args.no_write:
        outbox = path_from_config(cfg, "outbox")
        outbox.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in result.match)[:50]
        report_path = outbox / f"SIM_{safe}_{date.today().isoformat()}.md"
        report_path.write_text(md, encoding="utf-8")
        (outbox / "SIM_LATEST.md").write_text(md, encoding="utf-8")
    else:
        report_path = None

    if args.write_evidence:
        if not args.selection:
            print("--write-evidence requires --selection", file=sys.stderr)
            return 2
        try:
            ev_path = write_evidence_from_sim(
                cfg,
                result,
                selection=args.selection,
                decimal_odds=args.odds_ref,
                filename=args.evidence_filename,
            )
            print(f"Evidence seeded: {ev_path}")
        except Exception as e:
            print(f"Evidence write failed: {e}", file=sys.stderr)
            return 1

    if args.json:
        print(json.dumps(result_to_dict(result), indent=2, default=str))
    else:
        print(md)
        if args.selection:
            p = p_model_for_selection(result, args.selection)
            print(f"\n### Mapped p_model for selection {args.selection!r}: {p}")
    if report_path:
        print(f"\nWrote: {report_path}")
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    from nt.calibrate import rebuild_calibration, run_calibration_report

    cfg = load_config()
    sub = args.calibrate_cmd

    if sub == "report":
        report = run_calibration_report(cfg, write_outbox=not args.no_write)
        print(report.get("markdown") or json.dumps(report, indent=2, default=str))
        if args.json:
            slim = {k: v for k, v in report.items() if k != "markdown"}
            print("\n--- JSON ---\n" + json.dumps(slim, indent=2, default=str))
        return 0

    if sub == "rebuild":
        report = rebuild_calibration(cfg, write=True)
        # also write human report
        full = run_calibration_report(cfg, write_outbox=not args.no_write)
        print(full.get("markdown") or json.dumps(report, indent=2, default=str))
        print(f"\nRebuilt n={report.get('n_written')} → {report.get('path')}")
        return 0

    print(f"Unknown calibrate subcommand: {sub}", file=sys.stderr)
    return 2


def cmd_agent(args: argparse.Namespace) -> int:
    from nt.agent import ask, list_tools, run_tool, status_brief

    cfg = load_config()
    sub = args.agent_cmd

    if sub == "tools":
        print(json.dumps({"tools": list_tools()}, indent=2))
        return 0

    if sub == "status-brief":
        print(status_brief(cfg))
        return 0

    if sub == "critique-evidence":
        path = args.path
        result = run_tool(cfg, "grade_evidence_file", {"path": path, "odds": args.odds or 1.90})
        print(json.dumps(result, indent=2, default=str))
        return 0

    if sub == "ask":
        q = args.question or ""
        if not q:
            print("Provide a question", file=sys.stderr)
            return 2
        print(ask(cfg, q, context_path=args.context))
        return 0

    if sub == "tool":
        name = args.name
        raw = args.args or "{}"
        try:
            tool_args = json.loads(raw)
        except json.JSONDecodeError:
            print("Invalid JSON for --args", file=sys.stderr)
            return 2
        print(json.dumps(run_tool(cfg, name, tool_args), indent=2, default=str))
        return 0

    print(f"Unknown agent subcommand: {sub}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nt", description="NT Betting Tracker CLI — code is law")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show equity, phase, daily risk").set_defaults(func=cmd_status)
    sub.add_parser("validate", help="Validate bets ledger").set_defaults(func=cmd_validate)
    sub.add_parser("refresh", help="Recompute state files").set_defaults(func=cmd_refresh)
    p_cap = sub.add_parser(
        "capital",
        help="capital_v2 status / unfreeze / unlock-secure / segments",
    )
    cap = p_cap.add_subparsers(dest="capital_cmd", required=True)
    cap.add_parser("status", help="Show capital_v2 enable flag, freeze, secure, risk rooms").set_defaults(
        func=cmd_capital
    )
    cap.add_parser("segments", help="Dump capital_segments.json structure").set_defaults(func=cmd_capital)
    p_uf = cap.add_parser(
        "unfreeze",
        help="Clear manual freeze flag (requires --confirm); writes freeze_audit",
    )
    p_uf.add_argument(
        "--confirm",
        action="store_true",
        help="Required — explicit operator confirmation",
    )
    p_uf.add_argument("--reason", default="manual_unfreeze")
    p_uf.add_argument("--actor", default="cli")
    p_uf.set_defaults(func=cmd_capital)
    p_us = cap.add_parser(
        "unlock-secure",
        help="Release secure bucket → working (7d manual cooldown; requires --confirm)",
    )
    p_us.add_argument(
        "--confirm",
        action="store_true",
        help="Required — explicit operator confirmation",
    )
    p_us.add_argument("--reason", default="manual_unlock")
    p_us.add_argument("--actor", default="cli")
    p_us.add_argument(
        "--force",
        action="store_true",
        help="Bypass manual unlock cooldown (ops only)",
    )
    p_us.set_defaults(func=cmd_capital)
    p_learn = sub.add_parser(
        "learn",
        help="Recompute learning mults; list/accept/reject proposals",
    )
    p_learn.add_argument(
        "--proposals",
        action="store_true",
        help="Show pending learning proposals from settlement review",
    )
    p_learn.add_argument("--accept", default=None, help="Accept proposal id")
    p_learn.add_argument("--reject", default=None, help="Reject proposal id")
    p_learn.set_defaults(func=cmd_learn)
    p_bf = sub.add_parser(
        "backfill-decisions",
        help="Backfill bet_decisions.jsonl from bets.csv notes + densify market_key",
    )
    p_bf.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be written without appending side-cars",
    )
    p_bf.set_defaults(func=cmd_backfill_decisions)

    p_evp = sub.add_parser(
        "backfill-evidence-pmodel",
        help="Soft-match evidence/*.json → p_model in decisions (default DRY-RUN)",
    )
    p_evp.add_argument(
        "--write",
        action="store_true",
        help="Actually append side-cars (default is dry-run / audit only)",
    )
    p_evp.add_argument(
        "--min-confidence",
        type=float,
        default=0.85,
        help="Minimum match confidence to auto-write (default 0.85)",
    )
    p_evp.set_defaults(func=cmd_backfill_evidence_pmodel)

    p_rec = sub.add_parser(
        "recommend",
        help="Evidence + odds → place slip (refuses zero-research boards unless --force-mechanical)",
    )
    p_rec.add_argument("--odds", required=True, help="Path to odds csv/md/txt")
    p_rec.add_argument("--dry-run", action="store_true", help="Do not append Pending rows")
    p_rec.add_argument(
        "--force-mechanical",
        action="store_true",
        help="Allow recommend with zero evidence (wrong path; tests/emergency only)",
    )
    p_rec.set_defaults(func=cmd_recommend)

    p_ack = sub.add_parser(
        "place-ack",
        help="Confirm open Pending tickets as ConfirmedPlaced (live on NT)",
    )
    p_ack.add_argument("--ids", default="", help="Comma-separated bet_id list")
    p_ack.add_argument("--match", default="", help="Match/selection substring filter")
    p_ack.add_argument("--dry-run", action="store_true", help="Preview without writing ledger")
    p_ack.set_defaults(func=cmd_place_ack)

    p_ab = sub.add_parser(
        "abandon",
        help="Abandon open Pending/ConfirmedPlaced (never placed; frees risk; P/L 0)",
    )
    p_ab.add_argument("--ids", default="", help="Comma-separated bet_id list")
    p_ab.add_argument("--match", default="", help="Match/selection substring filter")
    p_ab.add_argument(
        "--reason",
        default="missed_prematch",
        help="Why abandoned (audit note)",
    )
    p_ab.add_argument("--dry-run", action="store_true", help="Preview without writing ledger")
    p_ab.set_defaults(func=cmd_abandon)

    p_set = sub.add_parser(
        "settle",
        help="Settle bets (+ post-analysis + learning). File, draft, or items JSON.",
    )
    p_set.add_argument("--results", default=None, help="Path to results yaml/json/txt")
    p_set.add_argument(
        "--draft",
        action="store_true",
        help="List pending bets with auto-fetch suggestions (no write)",
    )
    p_set.add_argument(
        "--no-fetch",
        action="store_true",
        help="With --draft: skip auto result fetch",
    )
    p_set.add_argument(
        "--items-json",
        default=None,
        help="Settle from JSON list/file {results:[...]} with rich fields",
    )
    p_set.add_argument(
        "--list-fetchers",
        action="store_true",
        help="List registered multi-sport result fetchers",
    )
    p_set.set_defaults(func=cmd_settle)

    # --- v5 additive commands ---
    p_an = sub.add_parser("analyze", help="Performance attribution + process report (read-only)")
    p_an.add_argument("--no-write", action="store_true", help="Do not write outbox report")
    p_an.add_argument("--json", action="store_true", help="Also print JSON payload")
    p_an.set_defaults(func=cmd_analyze)

    p_pr = sub.add_parser("project", help="Monte Carlo bankroll projection (does not touch ledger)")
    p_pr.add_argument("--years", type=float, default=None)
    p_pr.add_argument("--sims", type=int, default=None)
    p_pr.add_argument("--roi", type=float, default=None, help="Assumed ROI on stake e.g. 0.02")
    p_pr.add_argument("--bets-per-week", type=float, default=None)
    p_pr.add_argument("--avg-odds", type=float, default=None)
    p_pr.add_argument("--seed", type=int, default=None)
    p_pr.add_argument("--no-write", action="store_true")
    p_pr.set_defaults(func=cmd_project)

    p_ed = sub.add_parser("edges", help="Query data/edges.jsonl")
    p_ed.add_argument("--last", type=int, default=30)
    p_ed.add_argument("--result", default=None)
    p_ed.add_argument("--phase", default=None)
    p_ed.add_argument("--grade", default=None)
    p_ed.add_argument("--sport", default=None)
    p_ed.add_argument("--query", default=None, help="Substring match on match/selection/note")
    p_ed.add_argument("--json", action="store_true")
    p_ed.set_defaults(func=cmd_edges)

    # Simulation (optional research tools → p_model suggestions; never places)
    p_sim = sub.add_parser(
        "simulate",
        help="Quant sim → suggested p_model (football|tennis|basketball; does not place)",
    )
    p_sim.add_argument(
        "--sport",
        default="football",
        choices=["football", "tennis", "basketball"],
        help="Sport model (default football)",
    )
    p_sim.add_argument("--input", default=None, help="YAML/JSON SimInputs file")
    p_sim.add_argument("--match", default="")
    p_sim.add_argument("--home", default="")
    p_sim.add_argument("--away", default="")
    # tennis
    p_sim.add_argument("--player-a", default="", dest="player_a")
    p_sim.add_argument("--player-b", default="", dest="player_b")
    p_sim.add_argument("--hold-a", type=float, default=0.78, dest="hold_a")
    p_sim.add_argument("--hold-b", type=float, default=0.78, dest="hold_b")
    p_sim.add_argument("--best-of", type=int, default=3, dest="best_of")
    p_sim.add_argument("--elo-diff", type=float, default=None, dest="elo_diff")
    # basketball
    p_sim.add_argument("--margin", type=float, default=0.0)
    p_sim.add_argument("--margin-sd", type=float, default=12.0, dest="margin_sd")
    p_sim.add_argument("--mean-total", type=float, default=220.0, dest="mean_total")
    p_sim.add_argument("--total-sd", type=float, default=18.0, dest="total_sd")
    p_sim.add_argument("--handicap-line", type=float, default=None, dest="handicap_line")
    p_sim.add_argument("--total-line", type=float, default=None, dest="total_line")
    p_sim.add_argument("--lambda-home", type=float, default=None)
    p_sim.add_argument("--lambda-away", type=float, default=None)
    p_sim.add_argument("--home-xg-for", type=float, default=None)
    p_sim.add_argument("--home-xg-against", type=float, default=None)
    p_sim.add_argument("--away-xg-for", type=float, default=None)
    p_sim.add_argument("--away-xg-against", type=float, default=None)
    p_sim.add_argument("--league-avg-xg", type=float, default=None)
    p_sim.add_argument("--home-advantage", type=float, default=None)
    p_sim.add_argument("--form-home", type=float, default=None)
    p_sim.add_argument("--form-away", type=float, default=None)
    p_sim.add_argument("--motivation-home", type=float, default=None)
    p_sim.add_argument("--motivation-away", type=float, default=None)
    p_sim.add_argument("--rest-home", type=float, default=None)
    p_sim.add_argument("--rest-away", type=float, default=None)
    p_sim.add_argument("--injury-home", type=float, default=None)
    p_sim.add_argument("--injury-away", type=float, default=None)
    p_sim.add_argument("--rho", type=float, default=None, help="Dixon-Coles rho (default -0.05)")
    p_sim.add_argument("--league", default="")
    p_sim.add_argument("--source-quality", default="medium", choices=["low", "medium", "high"])
    p_sim.add_argument("--notes", default="")
    p_sim.add_argument("--selection", default=None, help="Map p_model for this NT selection")
    p_sim.add_argument("--odds-ref", type=float, default=None)
    p_sim.add_argument("--write-evidence", action="store_true", help="Seed evidence/*.json (fill sources!)")
    p_sim.add_argument("--evidence-filename", default=None)
    p_sim.add_argument("--json", action="store_true")
    p_sim.add_argument("--no-write", action="store_true")
    p_sim.set_defaults(func=cmd_simulate)

    p_fail = sub.add_parser("failures", help="Indexed past failures (rebuild / query)")
    p_fail_sub = p_fail.add_subparsers(dest="failures_cmd")
    p_fail_rb = p_fail_sub.add_parser("rebuild", help="Rebuild failure_index.json")
    p_fail_rb.set_defaults(func=cmd_failures, failures_cmd="rebuild")
    p_fail_q = p_fail_sub.add_parser("query", help="Query failure index")
    p_fail_q.add_argument("--q", default="", help="Token query (AND)")
    p_fail_q.add_argument("--sport", default=None)
    p_fail_q.add_argument("--kind", default=None, help="bet|edge|evidence|review")
    p_fail_q.add_argument("--limit", type=int, default=20)
    p_fail_q.add_argument("--json", action="store_true")
    p_fail_q.set_defaults(func=cmd_failures, failures_cmd="query")

    p_cs = sub.add_parser(
        "control-signals",
        help="ControlSignals: list / emit / revoke temp_gate_raise",
    )
    cs = p_cs.add_subparsers(dest="cs_cmd", required=True)
    cs_list = cs.add_parser("list", help="List active temp_gate_raise signals")
    cs_list.add_argument("--json", action="store_true")
    cs_list.set_defaults(func=cmd_control_signals, cs_cmd="list")
    cs_em = cs.add_parser("emit", help="Emit temp_gate_raise (manual / force_review)")
    cs_em.add_argument("--sport", required=True)
    cs_em.add_argument("--market", default="")
    cs_em.add_argument("--bet-id", default="", dest="bet_id")
    cs_em.add_argument(
        "--source",
        default="manual",
        help="manual | force_review | process_error",
    )
    cs_em.add_argument("--reason", default="")
    cs_em.set_defaults(func=cmd_control_signals, cs_cmd="emit")
    cs_rv = cs.add_parser("revoke", help="Expire/revoke matching active signals")
    cs_rv.add_argument("--sport", default="")
    cs_rv.add_argument("--market", default="")
    cs_rv.add_argument("--all", action="store_true", help="Revoke all active")
    cs_rv.add_argument("--actor", default="cli")
    cs_rv.add_argument("--reason", default="manual_expire")
    cs_rv.set_defaults(func=cmd_control_signals, cs_cmd="revoke")

    p_cal = sub.add_parser("calibrate", help="p_model vs outcome calibration")
    cal = p_cal.add_subparsers(dest="calibrate_cmd", required=True)
    cal_rep = cal.add_parser("report", help="Brier, bias, reliability bins")
    cal_rep.add_argument("--no-write", action="store_true")
    cal_rep.add_argument("--json", action="store_true")
    cal_rep.set_defaults(func=cmd_calibrate)
    cal_rb = cal.add_parser("rebuild", help="Rebuild calibration.jsonl from ledger + decisions")
    cal_rb.add_argument("--no-write", action="store_true")
    cal_rb.set_defaults(func=cmd_calibrate)

    p_rs = sub.add_parser(
        "research",
        help="Research workflow: board shortlist, ready check, sources, scaffold, p-model",
    )
    rs = p_rs.add_subparsers(dest="research_cmd", required=True)

    rs_board = rs.add_parser(
        "board",
        help="PRIMARY: parse odds → research shortlist → report (+ optional scaffolds)",
    )
    rs_board.add_argument("--odds", required=True, help="Odds dump path")
    rs_board.add_argument(
        "--write-scaffolds",
        action="store_true",
        help="Write evidence/*.json templates for shortlist rows",
    )
    rs_board.add_argument("--max-per-match", type=int, default=None)
    rs_board.add_argument("--max-total", type=int, default=None)
    rs_board.add_argument("--no-write", action="store_true", help="Do not write outbox report")
    rs_board.add_argument("--json", action="store_true")
    rs_board.add_argument(
        "--skip-market-scan",
        action="store_true",
        help="Skip Market Coverage Agent (high-volume board scan)",
    )
    rs_board.set_defaults(func=cmd_research)

    rs_light = rs.add_parser(
        "light",
        help="Stage 1 Light Research: assess ≥70–85% of shortlist; emit deep queue",
    )
    rs_light.add_argument("--odds", required=True, help="Odds dump path")
    rs_light.add_argument("--no-write", action="store_true")
    rs_light.add_argument("--json", action="store_true")
    rs_light.add_argument(
        "--merge-deep",
        action="store_true",
        help="Refresh light batch with current deep evidence packs",
    )
    rs_light.set_defaults(func=cmd_research)

    rs_ms = rs.add_parser(
        "market-scan",
        help="Market Coverage Agent: tiered scan of all lines on high-volume matches",
    )
    rs_ms.add_argument("--odds", required=True, help="Odds dump path")
    rs_ms.add_argument(
        "--match",
        default=None,
        help="Focus one match (substring). Default: auto high-volume / top line counts",
    )
    rs_ms.add_argument(
        "--threshold",
        type=int,
        default=40,
        help="Lines per match to treat as high-volume (default 40)",
    )
    rs_ms.add_argument(
        "--top",
        type=int,
        default=5,
        help="Max matches to scan in auto mode",
    )
    rs_ms.add_argument("--json", action="store_true", help="Print full JSON")
    rs_ms.add_argument("--no-write", action="store_true", help="Do not write outbox reports")
    rs_ms.set_defaults(func=cmd_research)

    rs_ready = rs.add_parser("ready", help="Check if recommend is allowed for an odds file")
    rs_ready.add_argument("--odds", required=True)
    rs_ready.set_defaults(func=cmd_research)

    rs_src = rs.add_parser("sources", help="Print recommended sources for a sport")
    rs_src.add_argument("--sport", default="football")
    rs_src.set_defaults(func=cmd_research)

    rs_cl = rs.add_parser("checklist", help="Research checklist keys")
    rs_cl.add_argument("--sport", default="football")
    rs_cl.set_defaults(func=cmd_research)

    rs_sc = rs.add_parser("scaffold", help="Build evidence pack template")
    rs_sc.add_argument("--match", required=True)
    rs_sc.add_argument("--selection", required=True)
    rs_sc.add_argument("--p-model", type=float, default=None)
    rs_sc.add_argument("--league", default="")
    rs_sc.add_argument("--sport", default="football")
    rs_sc.add_argument("--odds-ref", type=float, default=None)
    rs_sc.add_argument("--write", action="store_true", help="Write under evidence/")
    rs_sc.add_argument("--overwrite", action="store_true", help="Overwrite existing pack")
    rs_sc.add_argument("--filename", default=None)
    rs_sc.set_defaults(func=cmd_research)

    rs_wp = rs.add_parser(
        "write-pack",
        help="Write a filled evidence pack (p_model + gates) under evidence/",
    )
    rs_wp.add_argument("--match", required=True)
    rs_wp.add_argument("--selection", required=True)
    rs_wp.add_argument("--p-model", type=float, required=True)
    rs_wp.add_argument("--sport", default="football")
    rs_wp.add_argument("--odds-ref", type=float, default=None)
    rs_wp.add_argument("--league", default="")
    rs_wp.add_argument("--summary", default="")
    rs_wp.add_argument("--failure-modes", default="")
    rs_wp.add_argument(
        "--availability-status",
        default="predicted",
        choices=["confirmed", "predicted", "stable_guess", "missing"],
    )
    rs_wp.add_argument("--availability-notes", default="")
    rs_wp.add_argument(
        "--context-risk",
        default="low",
        choices=["low", "medium", "high", "unknown"],
    )
    rs_wp.add_argument("--script-lean", default="neutral")
    rs_wp.add_argument(
        "--selection-vs-script",
        default="agree",
        choices=["agree", "conflict", "neutral", "unknown"],
    )
    rs_wp.add_argument("--base-rate-conflict", action="store_true")
    rs_wp.add_argument("--notes", default="")
    rs_wp.add_argument("--filename", default=None)
    rs_wp.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Fail if pack already exists (default overwrites)",
    )
    rs_wp.set_defaults(func=cmd_research)

    rs_pm = rs.add_parser("p-model", help="Haircut EV calculator")
    rs_pm.add_argument("--odds", type=float, required=True)
    rs_pm.add_argument("--p", type=float, required=True)
    rs_pm.set_defaults(func=cmd_research)

    rs_cr = rs.add_parser("critique", help="Grade + quality notes for an evidence file")
    rs_cr.add_argument("path")
    rs_cr.add_argument("--odds", type=float, default=1.90)
    rs_cr.set_defaults(func=cmd_research)

    rs_co = rs.add_parser("combo-policy", help="Show combo/singles policy for current phase")
    rs_co.set_defaults(func=cmd_research)

    rs_sm = rs.add_parser(
        "scan-merge",
        help="Stage 1b multi-agent scan merge (A/B/C/+D → shortlist 8–15 + primary worklist)",
    )
    rs_sm.add_argument("--odds", required=True, help="Odds dump path (full board)")
    rs_sm.add_argument("--agent-a", default=None, help="Agent A JSONL/JSON path")
    rs_sm.add_argument("--agent-b", default=None, help="Agent B JSONL/JSON path")
    rs_sm.add_argument("--agent-c", default=None, help="Agent C JSONL/JSON path")
    rs_sm.add_argument(
        "--agent-d",
        default=None,
        help="Agent D JSONL/JSON path (long-tail; optional / conditional spawn)",
    )
    rs_sm.add_argument(
        "--agents-dir",
        default=None,
        help="Directory with scan_agent_{a,b,c,d}* artifacts (auto-discover)",
    )
    rs_sm.add_argument(
        "--out",
        default=None,
        help="Write MULTI_AGENT_SHORTLIST.md here (default: outbox/)",
    )
    rs_sm.add_argument(
        "--out-json",
        default=None,
        help="Optional JSON payload path (default: alongside --out)",
    )
    rs_sm.add_argument("--json", action="store_true", help="Print full JSON payload")
    rs_sm.add_argument("--no-write", action="store_true", help="Do not write outbox artifacts")
    rs_sm.add_argument(
        "--no-live-open",
        action="store_true",
        help="Skip live ledger open-occupancy load",
    )
    rs_sm.set_defaults(func=cmd_research)

    rs_sd = rs.add_parser(
        "scan-depth",
        help="Per-match odds line counts + Agent D spawn predicate (lines >= min_lines, default 41)",
    )
    rs_sd.add_argument("--odds", required=True, help="Odds dump path (full board)")
    rs_sd.add_argument(
        "--min-lines",
        type=int,
        default=None,
        help="Override research.adaptive_scan_agent_d_min_lines (default 41)",
    )
    rs_sd.add_argument("--json", action="store_true", help="Print JSON payload")
    rs_sd.set_defaults(func=cmd_research)

    rs_mi = rs.add_parser(
        "match-intel",
        help="Build Match Intelligence Cards (MIC) from odds board / match list (free sources)",
    )
    rs_mi.add_argument(
        "--odds",
        default=None,
        help="Odds dump path (unique matches become MIC worklist)",
    )
    rs_mi.add_argument(
        "--matches",
        "--match",
        dest="matches",
        default=None,
        help='Explicit match(es), e.g. "Team A vs Team B" or "A vs B; C vs D"',
    )
    rs_mi.add_argument(
        "--sport",
        default=None,
        help="Sport filter / override (default: inferred per match; v1 full pipeline = football)",
    )
    rs_mi.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (default: research.match_intel.out_dir)",
    )
    rs_mi.add_argument(
        "--force",
        action="store_true",
        help="Ignore TTL cache and rebuild cards",
    )
    rs_mi.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write outbox/match_intel JSON",
    )
    rs_mi.add_argument(
        "--fixture-dir",
        default=None,
        help="Offline HTML fixture directory (tests / operator paste)",
    )
    rs_mi.add_argument(
        "--max-matches",
        type=int,
        default=None,
        help="Cap board matches (default: config max_board_matches)",
    )
    rs_mi.add_argument(
        "--allow-network",
        action="store_true",
        default=False,
        help="Enable live fetch (overrides research.match_intel.allow_network=false)",
    )
    rs_mi.add_argument(
        "--no-network",
        action="store_true",
        default=False,
        help="Force offline (ignore config allow_network if true)",
    )
    rs_mi.add_argument(
        "--url",
        default=None,
        help="Explicit match page URL (skips discovery). Used for all matches in the run.",
    )
    rs_mi.add_argument(
        "--fetch",
        default=None,
        choices=["firecrawl", "playwright", "http"],
        help="Override research.match_intel.fetch.prefer backend",
    )
    rs_mi.add_argument(
        "--write-aliases",
        action="store_true",
        default=False,
        help="Persist high-confidence discovered URLs to research.match_intel.alias_path",
    )
    rs_mi.add_argument("--json", action="store_true", help="Print JSON summary")
    rs_mi.set_defaults(func=cmd_research)

    rs_aqv = rs.add_parser(
        "apply-quality-veto",
        help="Stage 3.1z: apply Quality Challenger hard_veto (null p_model on packs)",
    )
    rs_aqv.add_argument(
        "--date",
        default=None,
        help="Calendar day YYYY-MM-DD (default: today); reads outbox/quality_veto_{date}.json",
    )
    rs_aqv.add_argument(
        "--veto-file",
        default=None,
        help="Override path to quality_veto JSON (default: outbox/quality_veto_{date}.json)",
    )
    rs_aqv.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve + report only; do not mutate packs or write applied marker",
    )
    rs_aqv.set_defaults(func=cmd_research)

    rs_acb = rs.add_parser(
        "assert-can-bet",
        help="Exit 0 if can_bet true else 1; prints risk gate fields (SSOT risk.json)",
    )
    rs_acb.add_argument(
        "--no-refresh",
        action="store_true",
        help="Read data/state/risk.json only (default: refresh_state like status)",
    )
    rs_acb.set_defaults(func=cmd_research)

    p_risk = sub.add_parser(
        "risk",
        help="Risk gates (assert-can-bet early exit after settle/refresh)",
    )
    risk_sub = p_risk.add_subparsers(dest="risk_cmd", required=True)
    risk_acb = risk_sub.add_parser(
        "assert-can-bet",
        help="Exit 0 if can_bet true else 1; same evaluate_risk path as status",
    )
    risk_acb.add_argument(
        "--no-refresh",
        action="store_true",
        help="Read data/state/risk.json only (default: refresh_state like status)",
    )
    risk_acb.set_defaults(func=cmd_risk)

    p_ag = sub.add_parser("agent", help="Optional AI assist (never places bets)")
    ag = p_ag.add_subparsers(dest="agent_cmd", required=True)

    ag.add_parser("tools", help="List agent tools").set_defaults(func=cmd_agent)
    ag.add_parser("status-brief", help="One-line status").set_defaults(func=cmd_agent)

    ag_ce = ag.add_parser("critique-evidence", help="Grade evidence via agent tool")
    ag_ce.add_argument("path")
    ag_ce.add_argument("--odds", type=float, default=1.90)
    ag_ce.set_defaults(func=cmd_agent)

    ag_ask = ag.add_parser("ask", help="Ask agent (LLM if enabled+keyed, else offline brief)")
    ag_ask.add_argument("question")
    ag_ask.add_argument("--context", default=None, help="Optional evidence path")
    ag_ask.set_defaults(func=cmd_agent)

    ag_tool = ag.add_parser("tool", help="Run a single agent tool")
    ag_tool.add_argument("name")
    ag_tool.add_argument("--args", default="{}", help="JSON object of arguments")
    ag_tool.set_defaults(func=cmd_agent)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
