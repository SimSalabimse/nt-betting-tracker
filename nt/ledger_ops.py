"""
Ledger place-confirmation and abandon operations.

Pending = recommend *intent* (counts as open risk until abandoned or settled).
ConfirmedPlaced = user confirmed ticket is live on Norsk Tipping.
Abandoned = never placed / voided intent (P/L 0, free risk seat).
"""
from __future__ import annotations

from typing import Any

from nt.bets_io import (
    fmt_num,
    is_open_risk,
    is_terminal,
    load_bets,
    utc_now,
    write_bets,
)
from nt.config import path_from_config
from nt.recommend import refresh_state


def _find_open(
    rows: list[dict[str, str]],
    *,
    ids: list[str] | None = None,
    match_substr: str | None = None,
) -> list[dict[str, str]]:
    open_rows = [r for r in rows if is_open_risk(r.get("result"))]
    if ids:
        idset = {i.strip() for i in ids if i and i.strip()}
        return [r for r in open_rows if (r.get("bet_id") or "") in idset]
    if match_substr:
        q = match_substr.strip().lower()
        return [
            r
            for r in open_rows
            if q in (r.get("match") or "").lower()
            or q in (r.get("selection") or "").lower()
        ]
    return []


def place_ack(
    cfg: dict[str, Any],
    *,
    ids: list[str] | None = None,
    match_substr: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Pending → ConfirmedPlaced (ticket confirmed live on NT).

    Still counts as open risk until Win/Loss/Refunded.
    """
    path = path_from_config(cfg, "bets")
    rows = load_bets(path)
    targets = _find_open(rows, ids=ids, match_substr=match_substr)
    if not targets:
        return {
            "ok": False,
            "error": "no open Pending/ConfirmedPlaced bets matched",
            "updated": [],
        }

    now = utc_now()
    updated: list[dict[str, str]] = []
    by_id = {r.get("bet_id"): r for r in rows}
    for t in targets:
        bid = t.get("bet_id") or ""
        row = by_id.get(bid)
        if not row:
            continue
        prev = row.get("result") or ""
        if prev == "ConfirmedPlaced":
            updated.append({"bet_id": bid, "result": prev, "note": "already confirmed"})
            continue
        if prev != "Pending":
            continue
        row["result"] = "ConfirmedPlaced"
        row["updated_at"] = now
        notes = (row.get("notes") or "").strip()
        tag = "place-ack: ConfirmedPlaced on NT"
        if tag not in notes:
            row["notes"] = (notes + f" | {tag}").strip(" |")
        updated.append({"bet_id": bid, "result": "ConfirmedPlaced", "prev": prev})

    if not dry_run and any(u.get("result") == "ConfirmedPlaced" and u.get("prev") == "Pending" for u in updated):
        write_bets(path, rows, backup=True)
        refresh_state(cfg)

    return {
        "ok": True,
        "dry_run": dry_run,
        "action": "place-ack",
        "updated": updated,
        "n": len(updated),
    }


def abandon(
    cfg: dict[str, Any],
    *,
    ids: list[str] | None = None,
    match_substr: str | None = None,
    reason: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Pending/ConfirmedPlaced → Abandoned.

    P/L = 0, does not count as pending risk, does not count as phase settled sample.
    Preserves full row for audit (never deletes history).
    """
    path = path_from_config(cfg, "bets")
    rows = load_bets(path)
    targets = _find_open(rows, ids=ids, match_substr=match_substr)
    if not targets:
        return {
            "ok": False,
            "error": "no open Pending/ConfirmedPlaced bets matched",
            "updated": [],
        }

    now = utc_now()
    reason_s = (reason or "unspecified").strip()
    updated: list[dict[str, str]] = []
    by_id = {r.get("bet_id"): r for r in rows}
    for t in targets:
        bid = t.get("bet_id") or ""
        row = by_id.get(bid)
        if not row or not is_open_risk(row.get("result")):
            continue
        if is_terminal(row.get("result")):
            continue
        prev = row.get("result") or ""
        row["result"] = "Abandoned"
        row["p_l_nok"] = fmt_num(0.0, 2)
        # No NT payout — stake never left bankroll (or returned conceptually)
        row["payout_nok"] = ""
        row["updated_at"] = now
        notes = (row.get("notes") or "").strip()
        tag = f"abandon: {reason_s}"
        row["notes"] = (notes + f" | {tag}").strip(" |")[:800]
        updated.append(
            {
                "bet_id": bid,
                "match": row.get("match"),
                "selection": row.get("selection"),
                "prev": prev,
                "result": "Abandoned",
                "reason": reason_s,
            }
        )

    if not dry_run and updated:
        write_bets(path, rows, backup=True)
        refresh_state(cfg)

    return {
        "ok": True,
        "dry_run": dry_run,
        "action": "abandon",
        "updated": updated,
        "n": len(updated),
    }
