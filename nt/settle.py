from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from nt.bankroll import compute_bankroll
from nt.bets_io import fnum, load_bets, utc_now, write_bets
from nt.config import path_from_config
from nt.pl import pl_from_outcome, pl_from_payout, payout_from_outcome
from nt.recommend import refresh_state


def _parse_results(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "results" in data:
            data = data["results"]
        if not isinstance(data, list):
            raise ValueError("YAML results must be a list or {results: [...]}")
        return data
    # JSON
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict) and "results" in data:
            data = data["results"]
        return data
    # Freeform blocks (user-friendly):
    #   Marco Fu
    #   win
    #   23.66 nok payout
    freeform = _parse_freeform_results(text)
    if freeform:
        return freeform

    # simple lines: bet_id,outcome  OR match|selection|outcome|payout
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            row: dict[str, Any] = {"match": parts[0], "selection": parts[1]}
            if len(parts) > 2:
                row["outcome"] = parts[2]
            if len(parts) > 3:
                row["payout_nok"] = fnum(parts[3])
            rows.append(row)
        elif "," in line:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                rows.append({"bet_id": parts[0], "outcome": parts[1], "payout_nok": fnum(parts[2]) if len(parts) > 2 else None})
    return rows


def _parse_freeform_results(text: str) -> list[dict[str, Any]]:
    """
    Parse loose multi-line result notes like:

        Marco Fu
        win
        23.66 nok payout

        Djurgården IF O2.5
        loss
    """
    import re

    lines = [ln.strip() for ln in text.splitlines()]
    # Only treat as freeform if we see win/loss keywords and no pipe-table rows
    body = "\n".join(lines).lower()
    if "|" in text or not any(k in body for k in ("win", "loss", "payout", "refund")):
        return []
    # Prefer structured if every non-empty line is bet_id,outcome style
    if all("," in ln and " " not in ln.split(",")[0] for ln in lines if ln and not ln.startswith("#")):
        return []

    blocks: list[list[str]] = []
    cur: list[str] = []
    for ln in lines:
        if not ln:
            if cur:
                blocks.append(cur)
                cur = []
            continue
        cur.append(ln)
    if cur:
        blocks.append(cur)

    out: list[dict[str, Any]] = []
    for block in blocks:
        if len(block) < 2:
            continue
        head = block[0]
        outcome = None
        payout = None
        for ln in block[1:]:
            low = ln.lower()
            if low in ("win", "won", "w", "loss", "lost", "l", "refund", "refunded", "void", "push"):
                outcome = ln
            m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*nok", low)
            if m:
                payout = fnum(m.group(1))
            else:
                try:
                    bare = fnum(ln)
                except (TypeError, ValueError):
                    bare = None
                if bare is not None and payout is None and outcome is not None:
                    payout = bare

        # Map shorthand heads to match/selection hints
        head_l = head.lower()
        # Extra non-outcome lines (e.g. O2.5 / BTTS / HUB) act as selection hints
        def _is_bare_number(s: str) -> bool:
            try:
                return fnum(s) is not None
            except (TypeError, ValueError):
                return False

        extras = [
            ln
            for ln in block[1:]
            if ln.lower() not in ("win", "won", "w", "loss", "lost", "l", "refund", "refunded", "void", "push")
            and not re.search(r"nok", ln.lower())
            and not _is_bare_number(ln)
        ]
        extra_l = " ".join(extras).lower()

        row: dict[str, Any] = {}
        if "fu" in head_l and "marco" in head_l or (head_l.strip() in ("marco fu", "fu marco")):
            row["match"] = "Fu, Marco"
            row["selection"] = "Fu, Marco to Win"
        elif "djurg" in head_l and ("o2.5" in head_l or "o2.5" in extra_l or "over 2.5" in head_l + extra_l):
            row["match"] = "Djurgården"
            row["selection"] = "Over 2.5"
        elif "djurg" in head_l and ("o3.5" in head_l or "o3.5" in extra_l or "over 3.5" in head_l + extra_l):
            row["match"] = "Djurgården"
            row["selection"] = "Over 3.5"
        else:
            # generic: head = team/match fragment; extras refine selection
            row["match"] = head
            sel = ""
            if "o2.5" in extra_l or "over 2.5" in extra_l:
                sel = "Over 2.5"
            elif "o3.5" in extra_l or "over 3.5" in extra_l:
                sel = "Over 3.5"
            elif "btts" in extra_l or "begge" in extra_l:
                # Match "BTTS Ja" / "BTTS Nei" pending selections
                if "nei" in extra_l or "no" in extra_l:
                    sel = "BTTS Nei"
                else:
                    sel = "BTTS"  # substring of "BTTS Ja"
            elif "dnb" in extra_l or "tilbakebetales" in extra_l:
                # Draw-no-bet / "Uavgjort tilbakebetales: Team"
                sel = "tilbakebetales"
            elif "hub" in extra_l or "to win" in extra_l or "vinner" in extra_l:
                # Prefer 1X2 / moneyline pending ("… to Win" or Vinner …)
                sel = "to Win"
            elif extras:
                # skip score lines like "Score 0-2"
                hint = next((e for e in extras if not e.lower().startswith("score")), extras[0])
                sel = "" if hint.lower().startswith("score") else hint
            row["selection"] = sel

        if outcome:
            row["outcome"] = outcome
        if payout is not None:
            row["payout_nok"] = payout
        if outcome or payout is not None:
            out.append(row)
    return out


def _match_bet(rows: list[dict[str, str]], item: dict[str, Any]) -> dict[str, str] | None:
    if item.get("bet_id"):
        for r in rows:
            if r.get("bet_id") == item["bet_id"]:
                return r
    match = (item.get("match") or "").strip().lower()
    selection = (item.get("selection") or "").strip().lower()
    # "Winner" / "Vinner" alone is a moneyline hint, not a selection substring
    moneyline_hint = selection in ("winner", "vinner", "to win", "hub", "win") or (
        selection.startswith("vinner") and len(selection) < 12
    )

    def _blob(r: dict[str, str]) -> str:
        return f"{r.get('match') or ''} {r.get('selection') or ''}".lower()

    def _match_hit(r: dict[str, str]) -> bool:
        if not match:
            return False
        m = (r.get("match") or "").lower()
        sel = (r.get("selection") or "").lower()
        if match in m or match in sel:
            return True
        # Token overlap for "Luciano Darderi" vs "Darderi, Luciano" / "Altmaier … vs Darderi …"
        tokens = [t for t in match.replace(",", " ").split() if len(t) > 2]
        if len(tokens) >= 2 and all(t in _blob(r) for t in tokens):
            return True
        return False

    from nt.bets_io import is_open_risk

    pending_all = [r for r in rows if is_open_risk(r.get("result"))]
    pending = [r for r in pending_all if _match_hit(r)]

    if selection and not moneyline_hint:
        narrowed = [r for r in pending if selection in (r.get("selection") or "").lower()]
        if narrowed:
            pending = narrowed
    elif moneyline_hint and pending:
        money = [
            r
            for r in pending
            if "to win" in (r.get("selection") or "").lower()
            or "vinner" in (r.get("selection") or "").lower()
        ]
        if money:
            pending = money

    if len(pending) == 1:
        return pending[0]
    if len(pending) > 1:
        exact = [r for r in pending if (r.get("selection") or "").lower() == selection]
        if len(exact) == 1:
            return exact[0]
        return pending[0]
    return None


def run_settle(cfg: dict[str, Any], results_path: Path) -> dict[str, Any]:
    items = _parse_results(results_path)
    path = path_from_config(cfg, "bets")
    rows = load_bets(path)
    now = utc_now()
    settled = []
    errors = []

    for item in items:
        bet = _match_bet(rows, item)
        if not bet:
            errors.append({"item": item, "error": "no matching pending bet"})
            continue
        from nt.bets_io import is_open_risk

        if not is_open_risk(bet.get("result")):
            errors.append(
                {
                    "bet_id": bet.get("bet_id"),
                    "error": f"not open for settle (result={bet.get('result')!r})",
                }
            )
            continue

        stake = fnum(bet.get("stake_nok")) or 0.0
        odds = fnum(bet.get("decimal_odds")) or 0.0
        payout = item.get("payout_nok")
        if payout is not None:
            payout = float(payout)
            pl = pl_from_payout(stake, payout)
            if payout <= 0:
                result = "Loss"
            elif abs(payout - stake) < 0.05:
                result = "Refunded"
            else:
                result = "Win"
        else:
            outcome = str(item.get("outcome") or item.get("result") or "").strip()
            if not outcome:
                errors.append({"bet_id": bet.get("bet_id"), "error": "need outcome or payout_nok"})
                continue
            pl = pl_from_outcome(stake, odds, outcome)
            payout = payout_from_outcome(stake, odds, outcome)
            ol = outcome.lower()
            if ol in ("loss", "l", "lost"):
                result = "Loss"
            elif ol in ("refund", "refunded", "void", "push"):
                result = "Refunded"
            else:
                result = "Win"

        bet["result"] = result
        bet["p_l_nok"] = f"{pl:.2f}".rstrip("0").rstrip(".")
        bet["payout_nok"] = f"{payout:.2f}".rstrip("0").rstrip(".")
        bet["updated_at"] = now

        # Rich settlement metadata (encoded into notes for ledger portability)
        rich_bits: list[str] = []
        score = item.get("score") or item.get("actual_score")
        if score:
            rich_bits.append(f"score:{score}")
        variance_tag = item.get("variance_tag") or item.get("feel")
        if variance_tag:
            rich_bits.append(f"feel:{variance_tag}")
        research_retro = item.get("research_quality_retro") or item.get("research_retro")
        if research_retro:
            rich_bits.append(f"research_retro:{research_retro}")
        conf_retro = item.get("confidence_retro")
        if conf_retro is not None and str(conf_retro).strip() != "":
            rich_bits.append(f"conf_retro:{conf_retro}")
        key_events = item.get("key_events")
        if key_events:
            rich_bits.append(f"events:{str(key_events)[:120]}")
        if item.get("auto_fetched"):
            rich_bits.append("auto_fetch:1")

        note = (item.get("notes") or item.get("settlement_notes") or "").strip()
        if rich_bits:
            rich_note = "settle{" + "; ".join(rich_bits) + "}"
            note = f"{note} | {rich_note}".strip(" |") if note else rich_note
        if note:
            prev = bet.get("notes") or ""
            bet["notes"] = (prev + " | " + note).strip(" |")[:500]

        settled.append(
            {
                "bet_id": bet["bet_id"],
                "result": result,
                "p_l_nok": pl,
                "payout_nok": payout,
                "score": score,
                "variance_tag": variance_tag,
                "research_quality_retro": research_retro,
                "confidence_retro": conf_retro,
                "key_events": key_events,
                "notes": note or None,
                "auto_fetched": bool(item.get("auto_fetched")),
                "match": bet.get("match"),
                "selection": bet.get("selection"),
                "sport": bet.get("sport"),
            }
        )

        # append learning line
        edges = path_from_config(cfg, "edges_jsonl")
        edges.parent.mkdir(parents=True, exist_ok=True)
        lesson = {
            "ts": now,
            "bet_id": bet["bet_id"],
            "match": bet.get("match"),
            "selection": bet.get("selection"),
            "odds": odds,
            "odds_band": bet.get("odds_band"),
            "result": result,
            "p_l": pl,
            "grade": bet.get("research_grade"),
            "phase": bet.get("phase"),
            "note": note or None,
            "score": score,
            "variance_tag": variance_tag,
            "research_quality_retro": research_retro,
            "auto_fetched": bool(item.get("auto_fetched")),
        }
        with open(edges, "a", encoding="utf-8") as f:
            f.write(json.dumps(lesson, ensure_ascii=False) + "\n")

        # Calibration: p_model vs outcome (optional; never blocks settle)
        try:
            from nt.calibrate import append_for_settled

            append_for_settled(cfg, bet)
        except Exception:
            pass

    write_bets(path, rows)
    bankroll, phase, risk = refresh_state(cfg)

    # Learning loop: recompute sport/market/band mults from full ledger
    learning_summary: dict[str, Any] = {}
    try:
        from nt.learning import run_learning

        learn = run_learning(cfg, rows)
        learning_summary = {
            "updated_at": learn.get("updated_at"),
            "n_settled": (learn.get("summary") or {}).get("n_settled"),
            "n_blocked_sports": (learn.get("summary") or {}).get("n_blocked_sports"),
            "lessons": len(learn.get("lessons") or []),
            "layers": (learn.get("summary") or {}).get("layers"),
        }
    except Exception as ex:  # noqa: BLE001
        learning_summary = {"error": str(ex)}

    # Post-settlement analysis + learning proposals (does not auto-apply mult deltas)
    review_report: dict[str, Any] = {}
    try:
        from nt.settlement_review import analyze_settled_batch

        if settled:
            review_report = analyze_settled_batch(cfg, settled, rows=rows)
    except Exception as ex:  # noqa: BLE001
        review_report = {"error": str(ex)}

    outbox = path_from_config(cfg, "outbox")
    outbox.mkdir(parents=True, exist_ok=True)
    receipt = outbox / "SETTLEMENT_RECEIPT.md"
    lines = [
        "# Settlement receipt",
        "",
        f"Settled: {len(settled)} | Errors: {len(errors)}",
        f"Equity: **{bankroll['equity_nok']:.2f}** | Phase: **{phase['phase_id']}** | "
        f"Daily cap: **{risk['daily_risk_cap_nok']:.2f}**",
        "",
    ]
    for s in settled:
        extra = ""
        if s.get("score"):
            extra += f" · score {s['score']}"
        if s.get("variance_tag"):
            extra += f" · feel={s['variance_tag']}"
        lines.append(f"- {s['bet_id']}: {s['result']} P/L {s['p_l_nok']:+.2f}{extra}")
    if learning_summary and not learning_summary.get("error"):
        lines.extend(
            [
                "",
                "## Learning loop",
                f"- Recomputed mults · settled sample **{learning_summary.get('n_settled')}** · "
                f"blocked sports **{learning_summary.get('n_blocked_sports')}** · "
                f"lessons **{learning_summary.get('lessons')}**",
                "- See `data/state/learning.json` and `data/state/edges_summary.md`",
            ]
        )
    if review_report and not review_report.get("error"):
        rs = review_report.get("summary") or {}
        lines.extend(
            [
                "",
                "## Post-settlement analysis",
                f"- Skill-weighted P/L **{rs.get('skill_weighted_pl'):+}** · "
                f"variance bucket **{rs.get('variance_pl'):+}**",
                f"- Proposals: **{len(review_report.get('proposals') or [])}** "
                f"(accept/reject in LuminaNT Learnings or `nt learn proposals`)",
                "- Full write-up: `outbox/SETTLEMENT_ANALYSIS.md`",
            ]
        )
        for n in (review_report.get("narrative") or [])[:4]:
            lines.append(f"- {n}")
    if errors:
        lines.append("")
        lines.append("## Errors")
        for e in errors:
            lines.append(f"- {e}")
    receipt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "settled": settled,
        "errors": errors,
        "equity": bankroll["equity_nok"],
        "phase": phase["phase_id"],
        "daily_cap": risk["daily_risk_cap_nok"],
        "learning": learning_summary,
        "review": {
            "summary": review_report.get("summary"),
            "narrative": review_report.get("narrative"),
            "n_proposals": len(review_report.get("proposals") or []),
            "error": review_report.get("error"),
        }
        if review_report
        else {},
    }


def run_settle_items(cfg: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    """Settle from in-memory result items (API / UI) without a results file."""
    import tempfile
    from pathlib import Path as P

    tmp = P(tempfile.mkstemp(suffix=".yaml", prefix="nt_settle_")[1])
    try:
        tmp.write_text(
            yaml.safe_dump({"results": items}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return run_settle(cfg, tmp)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def build_pending_settle_draft(
    cfg: dict[str, Any],
    *,
    auto_fetch: bool = True,
) -> dict[str, Any]:
    """
    List pending bets with smart defaults + optional auto-fetch suggestions.
    Used by LuminaNT Settle desk and `nt settle draft`.
    """
    from nt.bets_io import is_open_risk

    path = path_from_config(cfg, "bets")
    rows = load_bets(path)
    pending = [r for r in rows if is_open_risk(r.get("result"))]
    suggestions: dict[str, Any] = {}
    if auto_fetch and pending:
        try:
            from nt.results_fetch import suggest_results_for_pending

            for sug in suggest_results_for_pending(pending):
                bid = sug.get("bet_id")
                if bid:
                    suggestions[str(bid)] = sug
        except Exception as ex:  # noqa: BLE001
            suggestions["_error"] = str(ex)

    # Resolve fetcher names even without network (for UI labels)
    fetcher_for: dict[str, str] = {}
    try:
        from nt.fetchers.registry import resolve_fetcher

        for r in pending:
            bid = r.get("bet_id") or ""
            if bid:
                fetcher_for[bid] = resolve_fetcher(r).name
    except Exception:
        pass

    draft = []
    for r in pending:
        bid = r.get("bet_id") or ""
        sug = suggestions.get(bid) or {}
        outcome = sug.get("outcome")
        # normalize outcome to settle parser vocabulary
        if outcome in ("win", "loss", "push", "refund"):
            outcome_out = outcome
        else:
            outcome_out = None
        events = sug.get("events") or []
        key_events = "; ".join(str(e) for e in events[:4]) if events else ""
        reason = sug.get("reason")
        if not auto_fetch and not reason:
            reason = "Auto-fetch disabled (--no-fetch) — enter outcome manually"
        elif not sug and auto_fetch:
            reason = "No suggestion returned"
        draft.append(
            {
                "bet_id": bid,
                "date": r.get("date"),
                "match": r.get("match"),
                "selection": r.get("selection"),
                "decimal_odds": r.get("decimal_odds"),
                "stake_nok": r.get("stake_nok"),
                "sport": r.get("sport"),
                "market_type": r.get("market_type"),
                "research_grade": r.get("research_grade"),
                "phase": r.get("phase"),
                "suggested_outcome": outcome_out,
                "suggested_score": sug.get("score"),
                "suggested_confidence": sug.get("confidence"),
                "suggested_reason": reason,
                "auto_fetch_ok": bool(sug.get("auto") and not sug.get("needs_manual")),
                "needs_manual": sug.get("needs_manual", True) if sug else True,
                "fetch_source": sug.get("source"),
                "fetcher": sug.get("fetcher") or fetcher_for.get(bid),
                "match_confidence": sug.get("match_confidence"),
                "fetch_status": sug.get("status"),
                "fetch_finished": sug.get("finished"),
                "suggested_events": events,
                # Rich defaults for the form
                "outcome": outcome_out,
                "score": sug.get("score"),
                "variance_tag": "",
                "research_quality_retro": "",
                "confidence_retro": "",
                "key_events": key_events,
                "notes": "",
                "include": bool(
                    outcome_out
                    and float(sug.get("confidence") or 0) >= 0.55
                    and not sug.get("needs_manual")
                ),
            }
        )

    # Summarize by fetcher for CLI / UI
    by_fetcher: dict[str, int] = {}
    for d in draft:
        fk = str(d.get("fetcher") or "none")
        if d.get("suggested_outcome"):
            by_fetcher[fk] = by_fetcher.get(fk, 0) + 1

    return {
        "n_pending": len(pending),
        "n_auto_suggested": sum(1 for d in draft if d.get("suggested_outcome")),
        "n_high_confidence": sum(1 for d in draft if d.get("auto_fetch_ok")),
        "suggestions_by_fetcher": by_fetcher,
        "fetchers_available": _list_fetcher_names(),
        "draft": draft,
        "generated_at": utc_now(),
    }


def _list_fetcher_names() -> list[str]:
    try:
        from nt.results_fetch import list_fetchers

        return [f["name"] for f in list_fetchers()]
    except Exception:
        return []
