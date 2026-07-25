"""
Settlement Lessons v1 — post-settle root-cause + soft awareness.

Engine always fills non-empty ``main_reason`` (auto-template when agent packet
is thin). Soft notes only (TTL); never permanent hard-reject lists.

Live ledger only: peers/window use ``filter_live_rows`` (no era_archive).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nt.bets_io import utc_now
from nt.config import path_from_config
from nt.live_ledger import filter_live_rows
from nt.market_family import market_family as corr_market_family

SCHEMA_VERSION = 1

OUTCOME_DRIVERS = frozenset(
    {
        "form_miss",
        "h2h_miss",
        "total_line_miss",
        "variance",
        "research_quality",
        "supported",
        "mixed",
    }
)

_EMPTY_PAYLOAD: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "updated_at": "",
    "settled_at": "",
    "batch_id": "",
    "live_ledger_only": True,
    "source": "data/bets.csv",
    "n_settled": 0,
    "bets": [],
    "soft_awareness": [],
}


def settlement_lessons_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    learn = (cfg or {}).get("learning") or {}
    sl = dict(learn.get("settlement_lessons") or {})
    sl.setdefault("enabled", True)
    sl.setdefault("recent_window", 12)
    sl.setdefault("max_soft_notes", 8)
    sl.setdefault("soft_ev_penalty_repeat_loss", 0.008)
    sl.setdefault("ttl_hours", 72)
    sl.setdefault("live_ledger_only", True)
    return sl


def settlement_lessons_json_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("settlement_lessons_json"):
        return path_from_config(cfg, "settlement_lessons_json")
    if paths.get("state_dir"):
        return path_from_config(cfg, "state_dir") / "settlement_lessons.json"
    return Path("data/state/settlement_lessons.json")


def settlement_lessons_md_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("settlement_lessons_md"):
        return path_from_config(cfg, "settlement_lessons_md")
    outbox = path_from_config(cfg, "outbox") if paths.get("outbox") else Path("outbox")
    return outbox / "SETTLEMENT_LESSONS.md"


def empty_lessons_payload() -> dict[str, Any]:
    return dict(_EMPTY_PAYLOAD)


def load_settlement_lessons(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """
    Load schema v1 settlement_lessons.json.

    Missing file / invalid JSON / wrong schema → empty payload (no throw).
    """
    if not cfg:
        return empty_lessons_payload()
    path = settlement_lessons_json_path(cfg)
    if not path.is_file():
        return empty_lessons_payload()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return empty_lessons_payload()
    if not isinstance(raw, dict):
        return empty_lessons_payload()
    ver = raw.get("schema_version")
    try:
        if int(ver) != SCHEMA_VERSION:
            return empty_lessons_payload()
    except (TypeError, ValueError):
        return empty_lessons_payload()
    out = empty_lessons_payload()
    out.update({k: raw.get(k, out.get(k)) for k in out})
    out["bets"] = list(raw.get("bets") or [])
    out["soft_awareness"] = list(raw.get("soft_awareness") or [])
    out["schema_version"] = SCHEMA_VERSION
    return out


def parse_line(selection: str, market_type: str = "") -> float | None:
    """Extract O/U line from selection (comma decimals OK)."""
    text = f"{selection or ''} {market_type or ''}".replace(",", ".")
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    if not nums:
        return None
    half = [float(x) for x in nums if "." in x and x.endswith(("0", "5"))]
    if half:
        return half[-1]
    try:
        return float(nums[-1])
    except ValueError:
        return None


def _parse_score_total(score: str, family: str) -> float | None:
    """
    Heuristic total from score string.

    Tennis set scores: sum of set games (e.g. 6-4 3-6 4-6 → 29).
    Football-style: sum of goals from first ``N-M`` pair.
    """
    s = (score or "").strip()
    if not s:
        return None
    pairs = re.findall(r"(\d+)\s*[-–]\s*(\d+)", s)
    if not pairs:
        return None
    fam = (family or "").lower()
    if "tennis" in fam or len(pairs) >= 2:
        total = 0.0
        for a, b in pairs:
            total += int(a) + int(b)
        return total
    a, b = pairs[0]
    return float(int(a) + int(b))


def score_vs_line_clause(
    *,
    family: str,
    selection: str,
    market_type: str = "",
    actual_score: str = "",
    line: float | None = None,
) -> str:
    """Optional ``; score_vs_line=…`` clause when totals family + parseable."""
    fam = (family or "").lower()
    if "total" not in fam and "totals" not in fam:
        return ""
    ln = line if line is not None else parse_line(selection, market_type)
    if ln is None:
        return ""
    est = _parse_score_total(actual_score, fam)
    if est is None:
        return ""
    side = "over" if est > ln else "under" if est < ln else "push"
    unit = "games" if "tennis" in fam else "goals" if "football" in fam else "total"
    return f"; score_vs_line={side} (est_{unit}={est:g} {'>' if side == 'over' else '<' if side == 'under' else '=='} {ln:g})"


def auto_main_reason(
    *,
    result: str,
    market_family: str,
    actual_score: str = "",
    line: float | None = None,
    variance_class: str = "",
    predictability: str = "",
    process_root_cause: str = "",
    research_quality_retro: str = "",
    selection: str = "",
    market_type: str = "",
) -> str:
    """Engine auto-template — always non-empty."""
    ln = line if line is not None else parse_line(selection, market_type)
    line_s = f"{ln:g}" if ln is not None else "n/a"
    base = (
        f"{result or 'n/a'}: family={market_family or 'other'}; "
        f"score={actual_score or 'n/a'}; line={line_s}; "
        f"taxonomy={variance_class or 'unknown'}; "
        f"pred={predictability or 'n/a'}; "
        f"root={process_root_cause or 'n/a'}; "
        f"retro={research_quality_retro or 'n/a'}"
    )
    clause = score_vs_line_clause(
        family=market_family,
        selection=selection,
        market_type=market_type,
        actual_score=actual_score,
        line=ln,
    )
    text = (base + clause).strip()
    return text[:240] if len(text) > 240 else text


def resolve_main_reason(
    bet: dict[str, Any],
    *,
    market_family: str,
    line: float | None = None,
) -> str:
    """Priority: explicit agent/UI reason → auto-template."""
    for key in ("main_reason", "settlement_notes", "notes"):
        raw = bet.get(key)
        if isinstance(raw, str) and raw.strip() and not raw.strip().startswith("settle{"):
            # Prefer short free-text; skip pure engine settle{} blobs as main_reason source
            t = raw.strip()
            if "settle{" in t and len(t) > 40:
                # may still have agent prefix before settle{
                prefix = t.split("settle{", 1)[0].strip(" |")
                if prefix and len(prefix) >= 8:
                    return prefix[:240]
                continue
            return t[:240]
    packet = bet.get("post_settlement_packet") if isinstance(bet.get("post_settlement_packet"), dict) else {}
    for key in ("main_reason", "notes", "settlement_notes"):
        raw = packet.get(key) if packet else None
        if isinstance(raw, str) and raw.strip():
            return raw.strip()[:240]
    return auto_main_reason(
        result=str(bet.get("result") or ""),
        market_family=market_family,
        actual_score=str(
            bet.get("actual_score") or bet.get("score") or packet.get("actual_score") or ""
        ),
        line=line,
        variance_class=str(
            bet.get("variance_class") or packet.get("variance_class") or ""
        ),
        predictability=str(
            bet.get("predictability") or packet.get("predictability") or ""
        ),
        process_root_cause=str(
            bet.get("process_root_cause") or packet.get("process_root_cause") or ""
        ),
        research_quality_retro=str(
            bet.get("research_quality_retro")
            or bet.get("research_retro")
            or packet.get("research_quality_retro")
            or ""
        ),
        selection=str(bet.get("selection") or ""),
        market_type=str(bet.get("market_type") or ""),
    )


def infer_outcome_driver(bet: dict[str, Any], *, market_family: str = "") -> str:
    """
    Pure-heuristic priority (first match wins).

    Returns one of OUTCOME_DRIVERS.
    """
    packet = (
        bet.get("post_settlement_packet")
        if isinstance(bet.get("post_settlement_packet"), dict)
        else {}
    )
    vc = str(
        bet.get("variance_class") or packet.get("variance_class") or ""
    ).strip().lower()
    retro = str(
        bet.get("research_quality_retro")
        or bet.get("research_retro")
        or packet.get("research_quality_retro")
        or ""
    ).strip().lower()
    tag = str(bet.get("variance_tag") or bet.get("feel") or "").strip().lower()
    result = str(bet.get("result") or "").strip()
    root = str(
        bet.get("process_root_cause") or packet.get("process_root_cause") or ""
    ).strip().lower()
    notes = " ".join(
        str(x)
        for x in (
            bet.get("notes"),
            bet.get("settlement_notes"),
            bet.get("key_events"),
            bet.get("main_reason"),
            packet.get("notes"),
            packet.get("classification_notes"),
        )
        if x
    ).lower()
    blob = f"{root} {notes}"

    # 1 research_quality
    if vc == "research_process_miss" or retro in ("poor", "wrong", "miss"):
        return "research_quality"

    # 2 variance
    p_model = bet.get("p_model")
    try:
        p_f = float(p_model) if p_model is not None else None
    except (TypeError, ValueError):
        p_f = None
    if vc == "true_randomness" or (
        result == "Loss" and p_f is not None and p_f >= 0.65 and tag in ("variance", "expected_variance")
    ):
        return "variance"
    if tag == "variance" and result == "Loss":
        return "variance"

    # 3 total_line_miss — score clearly wrong side of line
    fam = market_family or str(bet.get("market_family") or "")
    score = str(bet.get("actual_score") or bet.get("score") or packet.get("actual_score") or "")
    sel = str(bet.get("selection") or "")
    ln = parse_line(sel, str(bet.get("market_type") or ""))
    if ln is not None and score and ("total" in fam.lower() or "totals" in fam.lower()):
        est = _parse_score_total(score, fam)
        if est is not None:
            sel_l = sel.lower()
            want_over = bool(re.search(r"\bover\b", sel_l)) and not re.search(
                r"\bunder\b", sel_l.split("over")[0] if "over" in sel_l else sel_l
            )
            # Prefer explicit Over/Under token near end
            if re.search(r"\bunder\b", sel_l) and not re.search(
                r":\s*over\b", sel_l
            ):
                want_over = False
            if re.search(r":\s*over\b|\bover\s+\d", sel_l):
                want_over = True
            if re.search(r":\s*under\b|\bunder\s+\d", sel_l):
                want_over = False
            if want_over and est < ln:
                return "total_line_miss"
            if (not want_over) and est > ln:
                return "total_line_miss"

    # 4 form_miss
    if re.search(
        r"\bform\b|last\s*[- ]?5|ranking|seed|elo|momentum|streak",
        blob,
    ):
        return "form_miss"

    # 5 h2h_miss
    if re.search(r"\bh2h\b|head\s*[- ]?to\s*[- ]?head|innbyrdes", blob):
        return "h2h_miss"

    # 6 Win + process-aligned
    if result == "Win" and vc not in ("research_process_miss",) and retro not in (
        "poor",
        "wrong",
        "miss",
    ):
        return "supported"

    return "mixed"


def _row_family(row: dict[str, Any]) -> str:
    return corr_market_family(
        sport=str(row.get("sport") or ""),
        selection=str(row.get("selection") or ""),
        market_type=str(row.get("market_type") or ""),
        market_key=str(row.get("market_key") or ""),
    )


def _row_ts(row: dict[str, Any]) -> str:
    return str(row.get("updated_at") or row.get("created_at") or row.get("date") or "")


def recent_live_window(
    live_rows: list[dict[str, Any]],
    *,
    n: int = 12,
) -> list[dict[str, Any]]:
    """
    Last N settled-or-pending from live rows only.

    Excludes Abandoned. Order: updated_at / date descending.
    """
    keep_results = {
        "win",
        "loss",
        "refunded",
        "pending",
        "confirmedplaced",
    }
    filtered: list[dict[str, Any]] = []
    for r in live_rows or []:
        res = str(r.get("result") or "").strip().lower()
        if res == "abandoned":
            continue
        if res not in keep_results:
            continue
        filtered.append(r)
    filtered.sort(key=_row_ts, reverse=True)
    return filtered[: max(0, int(n))]


def detect_pattern_flag(
    bet: dict[str, Any],
    *,
    family: str,
    window: list[dict[str, Any]],
) -> str:
    bet_id = str(bet.get("bet_id") or "")
    peers = [
        w
        for w in window
        if _row_family(w) == family and str(w.get("bet_id") or "") != bet_id
    ]
    result = str(bet.get("result") or "")
    if peers and result == "Loss" and any(
        str(p.get("result") or "") == "Loss" for p in peers
    ):
        return "repeat_type_loss"
    if peers and result == "Win" and any(
        str(p.get("result") or "") == "Win" for p in peers
    ):
        return "repeat_type_win"
    if len(peers) >= 2:
        return "cluster_same_family"
    return "none"


def _soft_note_for(family: str, pattern_flag: str) -> str:
    if pattern_flag == "repeat_type_loss":
        return (
            f"Prefer {family} only with stronger hold-rate / H2H support; "
            "raise evidence bar, do not auto-ban"
        )
    if pattern_flag == "cluster_same_family":
        return f"Cluster of recent {family} — diversify shapes; soft caution only"
    return f"Soft note on {family}"


def _parse_iso(ts: str) -> datetime | None:
    s = (ts or "").strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def soft_note_expired(sa: dict[str, Any], *, now: datetime | None = None) -> bool:
    if sa.get("expired") is True:
        return True
    exp = _parse_iso(str(sa.get("expires_at") or ""))
    if exp is None:
        return False
    now = now or datetime.now(timezone.utc)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return now >= exp


def active_soft_awareness(
    lessons: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sa in (lessons or {}).get("soft_awareness") or []:
        if not isinstance(sa, dict):
            continue
        if soft_note_expired(sa, now=now):
            continue
        out.append(sa)
    return out


def lessons_soft_adjustments(
    family: str,
    lessons: dict[str, Any] | None,
    cfg: dict[str, Any] | None,
) -> tuple[float, str]:
    """
    Soft EV penalty for family matching active soft_awareness.

    Independent of similar-recent hits (works with similar_count=0).
    Never hard-rejects.
    """
    sl = settlement_lessons_cfg(cfg)
    if not sl.get("enabled", True):
        return 0.0, ""
    pen_unit = float(sl.get("soft_ev_penalty_repeat_loss") or 0.008)
    fam = (family or "").strip()
    if not fam:
        return 0.0, ""
    pen = 0.0
    reasons: list[str] = []
    for sa in active_soft_awareness(lessons):
        if str(sa.get("family") or "").strip() != fam:
            continue
        pf = str(sa.get("pattern_flag") or "")
        note = str(sa.get("note") or "")
        if pf in ("repeat_type_loss", "cluster_same_family") or "caution" in note.lower():
            pen += pen_unit
            reasons.append(f"lessons_soft: {fam} ({pf or 'caution'})")
    return pen, "; ".join(reasons)


def _batch_id(ts: str) -> str:
    # settle_20260725T184000Z
    compact = re.sub(r"[^0-9TZ]", "", (ts or "").upper())
    if not compact:
        compact = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"settle_{compact}"


def build_settlement_lessons(
    cfg: dict[str, Any],
    settled_batch: list[dict[str, Any]],
    live_rows: list[dict[str, Any]] | None = None,
    *,
    persist: bool = True,
) -> dict[str, Any]:
    """
    Build schema v1 lessons for a settled batch (≥1 terminal).

    ``live_rows`` should be full ledger rows; era_archive is filtered here.
    """
    sl = settlement_lessons_cfg(cfg)
    if not sl.get("enabled", True):
        return empty_lessons_payload()
    if not settled_batch:
        return empty_lessons_payload()

    now_s = utc_now()
    now_dt = _parse_iso(now_s) or datetime.now(timezone.utc)
    ttl_h = float(sl.get("ttl_hours") or 72)
    window_n = int(sl.get("recent_window") or 12)
    max_notes = int(sl.get("max_soft_notes") or 8)

    if live_rows is None:
        try:
            from nt.bets_io import load_bets

            live_rows = load_bets(path_from_config(cfg, "bets"))
        except Exception:
            live_rows = []

    live = filter_live_rows(live_rows)
    window = recent_live_window(live, n=window_n)

    bet_entries: list[dict[str, Any]] = []
    family_loss_counts: dict[str, int] = {}

    for bet in settled_batch:
        fam = _row_family(bet)
        if not fam or fam == "other":
            fam = corr_market_family(
                sport=str(bet.get("sport") or ""),
                selection=str(bet.get("selection") or ""),
                market_type=str(bet.get("market_type") or ""),
            )
        line = parse_line(str(bet.get("selection") or ""), str(bet.get("market_type") or ""))
        packet = (
            bet.get("post_settlement_packet")
            if isinstance(bet.get("post_settlement_packet"), dict)
            else {}
        )
        score = str(
            bet.get("actual_score") or bet.get("score") or packet.get("actual_score") or ""
        )
        vc = str(bet.get("variance_class") or packet.get("variance_class") or "")
        main_reason = resolve_main_reason(bet, market_family=fam, line=line)
        driver = infer_outcome_driver(bet, market_family=fam)
        if driver not in OUTCOME_DRIVERS:
            driver = "mixed"
        pattern = detect_pattern_flag(bet, family=fam, window=window)
        soft_note = ""
        if pattern in ("repeat_type_loss", "cluster_same_family"):
            soft_note = _soft_note_for(fam, pattern)
        if str(bet.get("result") or "") == "Loss":
            family_loss_counts[fam] = family_loss_counts.get(fam, 0) + 1

        bet_entries.append(
            {
                "bet_id": str(bet.get("bet_id") or ""),
                "match": str(bet.get("match") or ""),
                "selection": str(bet.get("selection") or ""),
                "sport": str(bet.get("sport") or ""),
                "market_family": fam,
                "result": str(bet.get("result") or ""),
                "main_reason": main_reason,
                "outcome_driver": driver,
                "pattern_flag": pattern,
                "soft_note": soft_note,
                "variance_class": vc or "unknown",
                "learning_weight": bet.get("learning_weight")
                if bet.get("learning_weight") is not None
                else packet.get("learning_weight"),
                "line": line,
                "actual_score": score or None,
            }
        )

    # Soft awareness: previous non-expired + new from patterns / batch cluster
    prev = load_settlement_lessons(cfg)
    merged: dict[str, dict[str, Any]] = {}
    for sa in active_soft_awareness(prev, now=now_dt):
        fam = str(sa.get("family") or "").strip()
        if fam:
            merged[fam] = dict(sa)

    expires_at = (now_dt + timedelta(hours=ttl_h)).strftime("%Y-%m-%dT%H:%M:%SZ")
    created_at = now_s if now_s.endswith("Z") else now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    for entry in bet_entries:
        pf = entry.get("pattern_flag") or "none"
        fam = entry.get("market_family") or ""
        if pf == "repeat_type_loss" and fam:
            merged[fam] = {
                "family": fam,
                "note": (
                    f"temporary caution — recent losses same family ({fam}); "
                    "raise evidence bar, do not auto-ban"
                ),
                "pattern_flag": "repeat_type_loss",
                "created_at": created_at,
                "expires_at": expires_at,
                "expired": False,
            }

    for fam, n_loss in family_loss_counts.items():
        if n_loss >= 2:
            existing = merged.get(fam)
            if not existing or existing.get("pattern_flag") != "repeat_type_loss":
                merged[fam] = {
                    "family": fam,
                    "note": (
                        f"temporary caution — {n_loss} losses same family in batch; "
                        "raise evidence bar, do not auto-ban"
                    ),
                    "pattern_flag": "cluster_same_family",
                    "created_at": created_at,
                    "expires_at": expires_at,
                    "expired": False,
                }

    soft_list = list(merged.values())
    # Prefer freshest / loss patterns; cap
    soft_list.sort(
        key=lambda s: (
            0 if s.get("pattern_flag") == "repeat_type_loss" else 1,
            str(s.get("created_at") or ""),
        )
    )
    soft_list = soft_list[:max_notes]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": created_at,
        "settled_at": created_at,
        "batch_id": _batch_id(created_at),
        "live_ledger_only": bool(sl.get("live_ledger_only", True)),
        "source": "data/bets.csv",
        "n_settled": len(bet_entries),
        "bets": bet_entries,
        "soft_awareness": soft_list,
    }

    if persist:
        write_settlement_lessons(cfg, payload)

    return payload


def write_settlement_lessons(cfg: dict[str, Any], payload: dict[str, Any]) -> dict[str, str]:
    """Persist JSON SSOT + human MD. Returns paths written."""
    jpath = settlement_lessons_json_path(cfg)
    mpath = settlement_lessons_md_path(cfg)
    jpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    jpath.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    mpath.write_text(render_settlement_lessons_md(payload), encoding="utf-8")
    return {"json": str(jpath), "md": str(mpath)}


def render_settlement_lessons_md(payload: dict[str, Any]) -> str:
    lines = [
        "# Settlement Lessons",
        "",
        f"Batch: **{payload.get('batch_id') or '—'}** · "
        f"Settled at: **{payload.get('settled_at') or '—'}** · "
        f"n=**{payload.get('n_settled') or 0}** · "
        f"schema v{payload.get('schema_version') or SCHEMA_VERSION}",
        "",
        f"Live ledger only: **{payload.get('live_ledger_only', True)}** · "
        f"source: `{payload.get('source') or 'data/bets.csv'}`",
        "",
        "## Per-bet",
        "",
    ]
    bets = payload.get("bets") or []
    if not bets:
        lines.append("_No settled bets in this batch._")
    for b in bets:
        lines.append(
            f"### {b.get('result')} · `{b.get('bet_id')}` · {b.get('market_family')}"
        )
        lines.append(f"- **Match:** {(b.get('match') or '')[:80]}")
        lines.append(f"- **Selection:** {(b.get('selection') or '')[:100]}")
        lines.append(f"- **Main reason:** {b.get('main_reason')}")
        lines.append(f"- **Driver:** `{b.get('outcome_driver')}`")
        lines.append(f"- **Pattern:** `{b.get('pattern_flag')}`")
        if b.get("actual_score"):
            lines.append(f"- **Score:** {b.get('actual_score')}")
        if b.get("soft_note"):
            lines.append(f"- **Soft note:** {b.get('soft_note')}")
        lines.append("")

    lines.extend(["## Soft awareness (TTL)", ""])
    sa_list = payload.get("soft_awareness") or []
    if not sa_list:
        lines.append("_No active soft notes._")
    for sa in sa_list:
        exp = "EXPIRED" if sa.get("expired") else f"expires {sa.get('expires_at')}"
        lines.append(
            f"- **{sa.get('family')}** (`{sa.get('pattern_flag')}`) — "
            f"{sa.get('note')} · {exp}"
        )
    lines.append("")
    lines.append(
        "_Soft notes only — never permanent hard rejects. "
        "Portfolio applies `lessons_soft:` demotion independently of similar-recent._"
    )
    lines.append("")
    return "\n".join(lines)


def run_settlement_lessons_safe(
    cfg: dict[str, Any],
    settled_batch: list[dict[str, Any]],
    live_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Non-blocking wrapper for settle: never raises; returns summary or error.
    """
    try:
        if not settled_batch:
            return {"ok": True, "skipped": True, "reason": "empty_batch"}
        sl = settlement_lessons_cfg(cfg)
        if not sl.get("enabled", True):
            return {"ok": True, "skipped": True, "reason": "disabled"}
        payload = build_settlement_lessons(
            cfg, settled_batch, live_rows=live_rows, persist=True
        )
        return {
            "ok": True,
            "batch_id": payload.get("batch_id"),
            "n_settled": payload.get("n_settled"),
            "n_soft": len(payload.get("soft_awareness") or []),
            "paths": {
                "json": str(settlement_lessons_json_path(cfg)),
                "md": str(settlement_lessons_md_path(cfg)),
            },
        }
    except Exception as ex:  # noqa: BLE001
        return {"ok": False, "error": str(ex)}
