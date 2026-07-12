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


def _match_bet(rows: list[dict[str, str]], item: dict[str, Any]) -> dict[str, str] | None:
    if item.get("bet_id"):
        for r in rows:
            if r.get("bet_id") == item["bet_id"]:
                return r
    match = (item.get("match") or "").strip().lower()
    selection = (item.get("selection") or "").strip().lower()
    pending = [
        r
        for r in rows
        if r.get("result") == "Pending"
        and match in (r.get("match") or "").lower()
        and (not selection or selection in (r.get("selection") or "").lower())
    ]
    if len(pending) == 1:
        return pending[0]
    if len(pending) > 1:
        # exact selection
        exact = [r for r in pending if (r.get("selection") or "").lower() == selection]
        if len(exact) == 1:
            return exact[0]
    return pending[0] if len(pending) == 1 else None


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
        if bet.get("result") != "Pending":
            errors.append({"bet_id": bet.get("bet_id"), "error": "already settled"})
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
        note = (item.get("notes") or "").strip()
        if note:
            prev = bet.get("notes") or ""
            bet["notes"] = (prev + " | " + note).strip(" |")[:400]
        settled.append(
            {
                "bet_id": bet["bet_id"],
                "result": result,
                "p_l_nok": pl,
                "payout_nok": payout,
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
        }
        with open(edges, "a", encoding="utf-8") as f:
            f.write(json.dumps(lesson, ensure_ascii=False) + "\n")

    write_bets(path, rows)
    bankroll, phase, risk = refresh_state(cfg)

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
        lines.append(f"- {s['bet_id']}: {s['result']} P/L {s['p_l_nok']:+.2f}")
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
    }
