from __future__ import annotations

"""
Side-car decision log for recommended / researched bets.

Stored as append-only JSONL so the UI can show p_model, EV, learning mults,
and process quality without overloading bets.csv.

Also recovers meta from bets.csv `notes` when the side-car was never written
(legacy recommend rows).
"""

import json
import re
from pathlib import Path
from typing import Any

from nt.bets_io import utc_now
from nt.config import path_from_config


DECISION_SCHEMA_VERSION = 1
DEFAULT_BET_IDS_CAP = 500


def decisions_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("decisions_jsonl"):
        return path_from_config(cfg, "decisions_jsonl")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "bet_decisions.jsonl"


def evidence_links_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("evidence_links_jsonl"):
        return path_from_config(cfg, "evidence_links_jsonl")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "evidence_links.jsonl"


def normalize_decision_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Additive process schema for place-time decisions.

    Ensures market_key / provenance fields when possible. Does not invent p_model.
    """
    from nt.analytics import infer_market

    rec = dict(record)
    rec.setdefault("schema_version", DECISION_SCHEMA_VERSION)
    rec.setdefault("ts", utc_now())

    sel = str(rec.get("selection") or "")
    mtype = str(rec.get("market_type") or rec.get("market_type_raw") or "")
    if not rec.get("market_key"):
        rec["market_key"] = infer_market(sel, mtype)
    if mtype and not rec.get("market_type_raw"):
        rec["market_type_raw"] = mtype

    # Provenance defaults (honest nulls preferred over silent invent)
    if rec.get("p_model") is not None and not rec.get("p_model_source"):
        rec["p_model_source"] = "engine"
    if rec.get("ev") is not None and not rec.get("ev_source"):
        rec["ev_source"] = "engine"

    ep = (rec.get("evidence_path") or "").strip()
    if ep:
        rec["evidence_path"] = ep
        rec.setdefault("evidence_match", "hard")
        rec.setdefault("evidence_confidence", 1.0)
    else:
        rec.setdefault("evidence_match", "none")
        rec.setdefault("evidence_confidence", 0.0)

    return rec


def append_decision(cfg: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """Append a normalized decision record. Returns the written record."""
    path = decisions_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = normalize_decision_record(record)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def append_evidence_link(cfg: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """
    Append bet_id → evidence_path hard/soft link (process side-car; not financial SSOT).
    """
    path = evidence_links_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(record)
    rec.setdefault("ts", utc_now())
    rec.setdefault("match_method", "place_hard")
    rec.setdefault("confidence", 1.0 if rec.get("match_method") == "place_hard" else 0.0)
    rec.setdefault("backfill", False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def load_evidence_links(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Latest primary evidence link per bet_id (highest confidence, then latest)."""
    path = evidence_links_path(cfg)
    if not path.is_file():
        return {}
    best: dict[str, dict[str, Any]] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                bid = str(row.get("bet_id") or "")
                if not bid:
                    continue
                prev = best.get(bid)
                if prev is None:
                    best[bid] = row
                    continue
                prev_c = float(prev.get("confidence") or 0)
                new_c = float(row.get("confidence") or 0)
                if new_c >= prev_c:
                    best[bid] = row
    except OSError:
        return {}
    return best


def load_decisions(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return latest decision record per bet_id."""
    path = decisions_path(cfg)
    if not path.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                bid = row.get("bet_id")
                if bid:
                    out[str(bid)] = row
    except OSError:
        return {}
    return out


def get_decision(cfg: dict[str, Any], bet_id: str) -> dict[str, Any] | None:
    return load_decisions(cfg).get(bet_id)


def _fnum(x: Any) -> float | None:
    if x is None or x == "":
        return None
    try:
        return float(str(x).replace(",", ".").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def parse_notes_meta(notes: str | None) -> dict[str, Any]:
    """
    Recover structured fields from portfolio/recommend notes strings.

    Examples:
      EV=0.055; EXPLORE; learn_EV+0.021; learn_stake×1.028; band <1.5 EV+0.009
      p_model=0.62; grade A; learn_stake×0.95
    """
    text = (notes or "").strip()
    out: dict[str, Any] = {
        "ev": None,
        "p_model": None,
        "explore": False,
        "learning_ev_boost": None,
        "learning_stake_mult": None,
        "reasons": [],
        "recovered_from_notes": bool(text),
    }
    if not text:
        out["recovered_from_notes"] = False
        return out

    # EV=0.055 or EV=+5.5% (treat >1 as percent)
    m = re.search(r"\bEV\s*=\s*([+-]?\d+(?:[.,]\d+)?)\s*%?", text, re.I)
    if m:
        ev = _fnum(m.group(1))
        if ev is not None:
            if abs(ev) > 1.0:
                ev = ev / 100.0
            out["ev"] = round(ev, 4)

    m = re.search(r"\bp_model\s*=\s*([+-]?\d+(?:[.,]\d+)?)", text, re.I)
    if m:
        p = _fnum(m.group(1))
        if p is not None:
            if p > 1.0:
                p = p / 100.0
            out["p_model"] = round(p, 4)

    if re.search(r"\bEXPLORE\b", text, re.I):
        out["explore"] = True

    # learn_EV+0.021 or learn_EV=0.021
    m = re.search(r"learn_EV\s*[=:]?\s*([+-]?\d+(?:[.,]\d+)?)", text, re.I)
    if m:
        v = _fnum(m.group(1))
        if v is not None:
            if abs(v) > 1.0:
                v = v / 100.0
            out["learning_ev_boost"] = round(v, 4)

    # learn_stake×1.028 or learn_stake x1.028 or learn_stake*=1.028
    m = re.search(r"learn_stake\s*[×x*=]+\s*([+-]?\d+(?:[.,]\d+)?)", text, re.I)
    if m:
        v = _fnum(m.group(1))
        if v is not None and v > 0:
            out["learning_stake_mult"] = round(v, 4)

    # Split reasons on ; for display
    parts = [p.strip() for p in re.split(r"[;|]", text) if p.strip()]
    out["reasons"] = parts[:8]
    return out


def decision_from_row(row: dict[str, str], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Build a decision payload from a ledger row + optional existing side-car.
    Notes fill gaps; existing structured fields win.
    """
    notes_meta = parse_notes_meta(row.get("notes"))
    base: dict[str, Any] = {
        "bet_id": row.get("bet_id") or "",
        "date": row.get("date") or "",
        "match": row.get("match") or "",
        "selection": row.get("selection") or "",
        "sport": (row.get("sport") or "").strip(),
        "market_type": row.get("market_type") or "",
        "odds_band": row.get("odds_band") or "",
        "phase": row.get("phase") or "",
        "grade": (row.get("research_grade") or "").upper() or None,
        "notes": row.get("notes") or "",
        "source": row.get("source") or "",
    }
    try:
        base["decimal_odds"] = float(str(row.get("decimal_odds") or 0).replace(",", "."))
    except ValueError:
        base["decimal_odds"] = None
    try:
        base["stake_nok"] = float(str(row.get("stake_nok") or 0).replace(",", "."))
    except ValueError:
        base["stake_nok"] = None

    if base.get("decimal_odds") and base["decimal_odds"] > 1.01:
        base["implied_prob"] = round(1.0 / float(base["decimal_odds"]), 4)

    # Merge: existing first, then notes fill None
    ex = dict(existing or {})
    for key in (
        "p_model",
        "ev",
        "explore",
        "learning_ev_boost",
        "learning_stake_mult",
        "reasons",
        "grade",
        "high_odds",
        "market_key",
        "ev_source",
        "p_model_source",
        "learning_from",
        "recovered_from_notes",
        "backfill",
        "backfill_note",
        "ts",
    ):
        if ex.get(key) is not None and ex.get(key) != "":
            base[key] = ex[key]

    if base.get("p_model") is None and notes_meta.get("p_model") is not None:
        base["p_model"] = notes_meta["p_model"]
        base["p_model_source"] = "notes"
    if base.get("ev") is None and notes_meta.get("ev") is not None:
        base["ev"] = notes_meta["ev"]
        base["ev_source"] = "notes"
    if not base.get("explore") and notes_meta.get("explore"):
        base["explore"] = True
    if base.get("learning_ev_boost") is None and notes_meta.get("learning_ev_boost") is not None:
        base["learning_ev_boost"] = notes_meta["learning_ev_boost"]
        base["learning_from"] = "notes"
    if base.get("learning_stake_mult") is None and notes_meta.get("learning_stake_mult") is not None:
        base["learning_stake_mult"] = notes_meta["learning_stake_mult"]
        base["learning_from"] = "notes"
    if not base.get("reasons") and notes_meta.get("reasons"):
        base["reasons"] = notes_meta["reasons"]

    # Mark recovery whenever notes supplied the only EV/p/learning we have
    if notes_meta.get("recovered_from_notes") and (
        base.get("ev_source") == "notes"
        or base.get("p_model_source") == "notes"
        or base.get("learning_from") == "notes"
        or base.get("backfill")
        or not existing
    ):
        base["recovered_from_notes"] = True

    if not existing:
        base["backfill"] = True
        base["backfill_note"] = "Reconstructed from ledger notes (side-car was missing)"
        base["recovered_from_notes"] = True

    return base


def resolve_decision(
    cfg: dict[str, Any] | None,
    row: dict[str, str],
    *,
    decisions_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """
    Best available decision for a row: side-car + notes enrichment.
    Always returns a dict when row has useful notes or a decision record.
    """
    bid = str(row.get("bet_id") or "")
    existing = None
    if decisions_map is not None and bid:
        existing = decisions_map.get(bid)
    elif cfg and bid:
        existing = get_decision(cfg, bid)

    notes = (row.get("notes") or "").strip()
    if existing is None and not notes and (row.get("source") or "") not in ("recommend", "grok", "manual"):
        # Archive / empty — still return thin shell for scoring honesty
        if (row.get("source") or "") == "era_archive":
            return {
                "bet_id": bid,
                "grade": (row.get("research_grade") or "").upper() or None,
                "source": "era_archive",
                "recovered_from_notes": False,
            }
        return None

    return decision_from_row(row, existing=existing)


def score_process(decision: dict[str, Any] | None, row: dict[str, str]) -> dict[str, Any]:
    """Ex-ante process quality from stored decision + row (+ notes recovery)."""
    # Ensure notes enrichment even if caller passed raw decision
    if decision is None or decision.get("recovered_from_notes") or decision.get("ev") is None:
        decision = decision_from_row(row, existing=decision)

    grade = (row.get("research_grade") or (decision or {}).get("grade") or "").upper()
    has_p = decision is not None and decision.get("p_model") is not None
    has_ev = decision is not None and decision.get("ev") is not None
    explore = bool((decision or {}).get("explore"))
    source = (row.get("source") or "").strip()
    recovered = bool((decision or {}).get("recovered_from_notes") or (decision or {}).get("backfill"))

    if has_p and has_ev and grade in ("A", "B"):
        label = "Solid process"
        score = "good"
        detail = f"Grade {grade} · model p + EV stored"
    elif has_ev and grade in ("A", "B") and recovered:
        label = "Recovered from notes"
        score = "ok"
        detail = f"Grade {grade} · EV from notes (no full p_model side-car)"
    elif has_ev and grade:
        label = "Partial process"
        score = "ok"
        detail = f"Grade {grade} · EV present · p_model {'ok' if has_p else 'missing'}"
    elif has_p and grade:
        label = "Partial process"
        score = "ok"
        detail = f"Grade {grade} · model p only"
    elif source == "recommend" and (has_ev or notes_has_signal(row.get("notes"))):
        label = "Engine shortlist"
        score = "ok"
        detail = "Recommend path · meta recovered from notes (not full Grok research pack)"
    elif source == "recommend":
        label = "Recommend (thin meta)"
        score = "weak"
        detail = "Logged by recommend with almost no recoverable meta"
    elif source == "era_archive":
        label = "Archive era"
        score = "archive"
        detail = "Pre-process history — accounting more than process grade"
    elif source in ("grok", "manual"):
        label = "Manual / Grok"
        score = "ok" if (has_ev or has_p) else "weak"
        detail = "Logged outside auto-engine" + (" · meta present" if (has_ev or has_p) else " · thin meta")
    else:
        label = "Unknown process"
        score = "weak"
        detail = "No decision dossier"

    if explore:
        detail += " · EXPLORE"
    if recovered and "recovered" not in detail.lower() and "notes" not in detail.lower():
        detail += " · notes recovery"

    return {
        "label": label,
        "score": score,
        "detail": detail,
        "grade": grade or "—",
        "recovered": recovered,
    }


def notes_has_signal(notes: str | None) -> bool:
    t = (notes or "").strip()
    if not t:
        return False
    return bool(re.search(r"\bEV\s*=", t, re.I) or re.search(r"learn_", t, re.I) or "EXPLORE" in t.upper())


def learning_summary_for_ui(decision: dict[str, Any] | None, row: dict[str, str], live_sport: dict | None = None) -> dict[str, str]:
    """Honest learning lines for the dossier (no contradictions)."""
    dec = decision_from_row(row, existing=decision) if (decision or row.get("notes")) else (decision or {})
    bits: list[str] = []
    if dec.get("learning_stake_mult") is not None:
        bits.append(f"stake ×{float(dec['learning_stake_mult']):.3f}")
    if dec.get("learning_ev_boost") is not None:
        bits.append(f"learn EV {float(dec['learning_ev_boost'])*100:+.1f}pp")
    if dec.get("explore"):
        bits.append("EXPLORE")

    if bits:
        if dec.get("learning_from") == "notes" or dec.get("recovered_from_notes") or dec.get("backfill"):
            src = "recovered from notes"
        else:
            src = "decision log"
        at_place = f"At place ({src}): " + " · ".join(bits)
    elif (row.get("source") or "") == "era_archive":
        at_place = "Archive bet — no learning snapshot at place (expected)"
    elif notes_has_signal(row.get("notes")):
        at_place = "Notes have signal but could not parse stake/EV mults"
    else:
        at_place = "No learning mults recorded at place time"

    if live_sport:
        after = (
            f"Sport now ×{live_sport.get('stake_mult', 1.0)} "
            f"({live_sport.get('status', '—')}) · live learning.json"
        )
    else:
        after = "Sport mult n/a in live learning"

    return {"at_place": at_place, "live_now": after}


def score_outcome(
    row: dict[str, str],
    decision: dict[str, Any] | None,
) -> dict[str, Any]:
    """Ex-post label: good/bad/lucky vs process (simple, honest)."""
    result = (row.get("result") or "").strip()
    if result == "Pending":
        return {"label": "Open", "score": "pending", "detail": "Not settled yet"}
    if result == "Refunded":
        return {"label": "Void", "score": "neutral", "detail": "Refunded / void"}

    try:
        pl = float(str(row.get("p_l_nok") or "0").replace(",", "."))
    except ValueError:
        pl = 0.0

    process = score_process(decision, row)
    won = result == "Win" or pl > 0.005
    lost = result == "Loss" or pl < -0.005

    if won and process["score"] == "good":
        return {"label": "Good bet (won)", "score": "good", "detail": "Positive process and positive result"}
    if lost and process["score"] == "good":
        return {"label": "Bad variance", "score": "variance", "detail": "Process OK — result against us"}
    if won and process["score"] in ("weak", "archive"):
        return {"label": "Lucky / thin process", "score": "lucky", "detail": "Won without strong stored process"}
    if lost and process["score"] in ("weak", "archive"):
        return {"label": "Weak process + loss", "score": "bad", "detail": "Loss with thin decision record"}
    if won:
        return {"label": "Won", "score": "good", "detail": f"P/L {pl:+.2f}"}
    if lost:
        return {"label": "Lost", "score": "bad", "detail": f"P/L {pl:+.2f}"}
    return {"label": result or "—", "score": "neutral", "detail": ""}


def backfill_decisions_from_notes(
    cfg: dict[str, Any],
    rows: list[dict[str, str]] | None = None,
    *,
    sources: tuple[str, ...] = ("recommend", "grok", "manual"),
    only_missing: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Append decision records reconstructed from ledger notes for rows missing side-car.

    Always densifies market_key via infer_market. Idempotent when only_missing=True
    (skips bet_ids already in the file). dry_run=True writes nothing.
    """
    from nt.analytics import infer_market
    from nt.bets_io import load_bets

    if rows is None:
        rows = load_bets(path_from_config(cfg, "bets"))

    existing = load_decisions(cfg)
    written = 0
    skipped = 0
    would_write: list[str] = []
    for r in rows:
        src = (r.get("source") or "").strip()
        if sources and src not in sources:
            continue
        bid = str(r.get("bet_id") or "")
        if not bid:
            skipped += 1
            continue
        if only_missing and bid in existing:
            skipped += 1
            continue
        notes = (r.get("notes") or "").strip()
        if not notes and src != "recommend":
            skipped += 1
            continue
        rec = decision_from_row(r, existing=None)
        rec["ts"] = utc_now()
        rec["backfill"] = True
        rec["market_key"] = infer_market(
            r.get("selection") or "", r.get("market_type") or ""
        )
        rec["market_type_raw"] = r.get("market_type") or ""
        rec["schema_version"] = DECISION_SCHEMA_VERSION
        if rec.get("p_model") is not None and not rec.get("p_model_source"):
            rec["p_model_source"] = "notes"
        if dry_run:
            would_write.append(bid)
            written += 1
            continue
        append_decision(cfg, rec)
        existing[bid] = rec
        written += 1

    return {
        "written": written,
        "skipped": skipped,
        "dry_run": dry_run,
        "would_write_ids": would_write[:50] if dry_run else [],
        "path": str(decisions_path(cfg)),
    }


def densify_market_keys(
    cfg: dict[str, Any],
    rows: list[dict[str, str]] | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Ensure every ledger row with a selection has a decision side-car market_key.

    Does not invent p_model. Skips bet_ids that already have market_key in decisions.
    """
    from nt.analytics import infer_market
    from nt.bets_io import load_bets

    if rows is None:
        rows = load_bets(path_from_config(cfg, "bets"))
    existing = load_decisions(cfg)
    written = 0
    skipped = 0
    for r in rows:
        bid = str(r.get("bet_id") or "")
        if not bid:
            skipped += 1
            continue
        prev = existing.get(bid) or {}
        if (prev.get("market_key") or "").strip():
            skipped += 1
            continue
        mk = infer_market(r.get("selection") or "", r.get("market_type") or "")
        rec = {
            "bet_id": bid,
            "date": r.get("date") or "",
            "match": r.get("match") or "",
            "selection": r.get("selection") or "",
            "sport": (r.get("sport") or "").strip(),
            "market_type": r.get("market_type") or "",
            "market_type_raw": r.get("market_type") or "",
            "market_key": mk,
            "odds_band": r.get("odds_band") or "",
            "phase": r.get("phase") or "",
            "grade": (r.get("research_grade") or "").upper() or None,
            "source": r.get("source") or "",
            "backfill": True,
            "backfill_note": "market_key densify only (no p_model invented)",
            "schema_version": DECISION_SCHEMA_VERSION,
        }
        # Preserve any existing process fields if present
        for k in ("p_model", "ev", "explore", "learning_stake_mult", "learning_ev_boost", "p_model_source"):
            if prev.get(k) is not None and prev.get(k) != "":
                rec[k] = prev[k]
        if dry_run:
            written += 1
            continue
        append_decision(cfg, rec)
        existing[bid] = rec
        written += 1
    return {"written": written, "skipped": skipped, "dry_run": dry_run}
