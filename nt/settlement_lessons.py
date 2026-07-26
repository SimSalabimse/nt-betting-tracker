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

try:
    from nt.live_ledger import filter_live_rows  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover — ESR diversify may not be on branch yet

    def filter_live_rows(rows):  # type: ignore[misc]
        if not rows:
            return []
        out = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            if str(r.get("source") or "").strip().lower() == "era_archive":
                continue
            out.append(r)
        return out


try:
    from nt.market_family import market_family as corr_market_family  # type: ignore
except ImportError:  # pragma: no cover

    def corr_market_family(  # type: ignore[misc]
        *,
        sport: str = "",
        selection: str = "",
        market_type: str = "",
        market_key: str = "",
    ) -> str:
        """Minimal family key when market_family module absent."""
        s = f"{sport} {selection} {market_type} {market_key}".lower()
        sport_s = (sport or "other").strip().lower() or "other"
        if "handikap" in s or "handicap" in s:
            return f"{sport_s}_handicap"
        if "total" in s or "over" in s or "under" in s:
            return f"{sport_s}_totals"
        if "vinner" in s or "to win" in s or "moneyline" in s:
            return f"{sport_s}_ml"
        return f"{sport_s}_other"

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


def _strip_engine_blobs(text: str) -> str:
    """Remove settle{…} / psp{…} engine payloads; keep free-text prefix only."""
    t = (text or "").strip()
    if not t:
        return ""
    for marker in ("settle{", "psp{"):
        if marker in t:
            t = t.split(marker, 1)[0]
    return t.strip(" |;")


def resolve_main_reason(
    bet: dict[str, Any],
    *,
    market_family: str,
    line: float | None = None,
) -> str:
    """Priority: explicit agent/UI reason → auto-template."""
    for key in ("main_reason", "settlement_notes", "notes"):
        raw = bet.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        t = raw.strip()
        # Pure engine blobs → fall through to auto-template
        if t.startswith("settle{") or t.startswith("psp{"):
            continue
        # Always strip engine payloads from composite notes (any length)
        if "settle{" in t or "psp{" in t:
            prefix = _strip_engine_blobs(t)
            if prefix and len(prefix) >= 8:
                return prefix[:240]
            continue
        return t[:240]
    packet = (
        bet.get("post_settlement_packet")
        if isinstance(bet.get("post_settlement_packet"), dict)
        else {}
    )
    for key in ("main_reason", "notes", "settlement_notes"):
        raw = packet.get(key) if packet else None
        if not isinstance(raw, str) or not raw.strip():
            continue
        t = raw.strip()
        if t.startswith("settle{") or t.startswith("psp{"):
            continue
        if "settle{" in t or "psp{" in t:
            prefix = _strip_engine_blobs(t)
            if prefix and len(prefix) >= 8:
                return prefix[:240]
            continue
        return t[:240]
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

    # 3 total_line_miss — score clearly wrong side of line (require explicit O/U token)
    fam = market_family or str(bet.get("market_family") or "")
    score = str(bet.get("actual_score") or bet.get("score") or packet.get("actual_score") or "")
    sel = str(bet.get("selection") or "")
    ln = parse_line(sel, str(bet.get("market_type") or ""))
    if ln is not None and score and ("total" in fam.lower() or "totals" in fam.lower()):
        est = _parse_score_total(score, fam)
        if est is not None:
            sel_l = sel.lower()
            has_over = bool(
                re.search(r":\s*over\b|\bover\s+\d|\bover\b", sel_l)
            )
            has_under = bool(
                re.search(r":\s*under\b|\bunder\s+\d|\bunder\b", sel_l)
            )
            # Require explicit over XOR under; ambiguous → fall through
            if has_over and not has_under:
                want_over: bool | None = True
            elif has_under and not has_over:
                want_over = False
            elif has_over and has_under:
                # Prefer the side after the last colon (NT "…: Over 22.5")
                if re.search(r":\s*over\b", sel_l):
                    want_over = True
                elif re.search(r":\s*under\b", sel_l):
                    want_over = False
                else:
                    want_over = None
            else:
                want_over = None
            if want_over is True and est < ln:
                return "total_line_miss"
            if want_over is False and est > ln:
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
    settled_only: bool = False,
) -> list[dict[str, Any]]:
    """
    Last N live ledger rows for pattern peers.

    Default: settled-only (Win/Loss/Refunded) so open tickets do not push
    historical same-family losses out of the window.

    ``settled_only=False`` also includes Pending / ConfirmedPlaced (cluster view).
    Excludes Abandoned. Order: updated_at / date descending.
    """
    if settled_only:
        keep_results = {"win", "loss", "refunded"}
    else:
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


# Operator / process-miss phrasing for side flips after a heavy-fav HC win.
_FLIP_NOTE_RE = re.compile(
    r"opposite of|side[_\s-]*flip|flip(?:ped)?\s+(?:after|from)|anti[- ]?flip|"
    r"after\s+(?:heavy\s+)?fav|fav(?:ourite|orite)?\s+.*\bhit\b|"
    r"opposite[- ]side|flipped\s+side",
    re.I,
)


def _bet_text_blob(bet: dict[str, Any]) -> str:
    packet = (
        bet.get("post_settlement_packet")
        if isinstance(bet.get("post_settlement_packet"), dict)
        else {}
    )
    parts = [
        bet.get("notes"),
        bet.get("settlement_notes"),
        bet.get("main_reason"),
        bet.get("key_events"),
        bet.get("process_root_cause"),
        packet.get("notes") if packet else None,
        packet.get("process_root_cause") if packet else None,
        packet.get("classification_notes") if packet else None,
    ]
    return " ".join(str(x) for x in parts if x)


def _side_flip_series_bounds(cfg: dict[str, Any] | None) -> tuple[float, int]:
    """Reuse form_continuity max_hours / max_games (fail-closed series window)."""
    max_hours = 48.0
    max_games = 2
    try:
        from nt.form_continuity import default_form_continuity_cfg  # type: ignore

        fc = dict(default_form_continuity_cfg())
        div = ((cfg or {}).get("learning") or {}).get("diversification") or {}
        sec = div.get("form_continuity") if isinstance(div, dict) else None
        if isinstance(sec, dict):
            fc.update(sec)
        max_hours = float(fc.get("max_hours", max_hours) or max_hours)
        max_games = int(fc.get("max_games", max_games) or max_games)
    except Exception:  # noqa: BLE001
        pass
    return max_hours, max_games


def detect_side_flip_after_fav_win(
    bet: dict[str, Any],
    *,
    window: list[dict[str, Any]],
    cfg: dict[str, Any] | None = None,
) -> bool:
    """
    True when this **Loss** seat is an opposite-side HC after a recent heavy-fav HC Win.

    Primary signal: live settled peer (Win, heavy fav minus HC) on same matchup
    with opposite HC sign, inside form_continuity series window (hours AND games).
    Secondary: process-miss notes / variance class (Loss only).

    Soft-awareness emission is loss-linked only (Win/Refunded never flag this pattern).
    """
    bet_id = str(bet.get("bet_id") or "").strip()
    result = str(bet.get("result") or "").strip()
    # Loss-linked only — soft awareness / pattern for process-miss flips
    if result != "Loss":
        return False

    packet = (
        bet.get("post_settlement_packet")
        if isinstance(bet.get("post_settlement_packet"), dict)
        else {}
    )
    vc = str(
        bet.get("variance_class") or packet.get("variance_class") or ""
    ).strip().lower()
    blob = _bet_text_blob(bet)
    cand_match = str(bet.get("match") or "")

    # Anchor scan: prior heavy-fav HC Win on opposite side of same teams
    try:
        from nt.form_continuity import (  # type: ignore
            is_heavy_favourite_hc,
            is_opposite_side_hc,
            in_series_window,
        )
    except ImportError:  # pragma: no cover
        is_heavy_favourite_hc = None  # type: ignore
        is_opposite_side_hc = None  # type: ignore
        in_series_window = None  # type: ignore

    max_hours, max_games = _side_flip_series_bounds(cfg)
    peer_hit = False
    if is_heavy_favourite_hc is not None and is_opposite_side_hc is not None:
        for peer in window or []:
            if str(peer.get("bet_id") or "").strip() == bet_id:
                continue
            if str(peer.get("result") or "").strip() != "Win":
                continue
            try:
                if not is_heavy_favourite_hc(peer, require_result=False):
                    continue
                if not is_opposite_side_hc(peer, bet):
                    continue
                # Series window: same team-pair AND hours AND games (fail-closed)
                if in_series_window is not None and cand_match:
                    ok, _h, _g = in_series_window(
                        peer,
                        cand_match,
                        window or [],
                        max_hours=max_hours,
                        max_games=max_games,
                    )
                    if not ok:
                        continue
            except Exception:  # noqa: BLE001
                continue
            peer_hit = True
            break

    note_hit = bool(_FLIP_NOTE_RE.search(blob))
    process_miss = vc in ("research_process_miss", "process_error", "process_miss")

    if peer_hit:
        return True
    if note_hit and (process_miss or "opposite" in blob.lower()):
        return True
    return False


def detect_pattern_flag(
    bet: dict[str, Any],
    *,
    family: str,
    window: list[dict[str, Any]],
    open_window: list[dict[str, Any]] | None = None,
    cfg: dict[str, Any] | None = None,
) -> str:
    """
    Pattern vs peers.

    Loss/Win repeat detection uses ``window`` (prefer settled-only).
    ``cluster_same_family`` may also use open tickets in ``open_window``.
    Soft awareness is only emitted for loss-linked patterns (see build).

    ``side_flip_after_fav_win`` (PR6) is highest-specificity when a heavy-fav
    HC Win is followed by opposite-side process miss — TTL soft only.
    """
    # Highest-specificity process miss first (Brewers −1.5 Win → Rockies +2.5)
    if detect_side_flip_after_fav_win(bet, window=window, cfg=cfg):
        return "side_flip_after_fav_win"

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
    open_peers = [
        w
        for w in (open_window or [])
        if _row_family(w) == family and str(w.get("bet_id") or "") != bet_id
    ]
    if len(peers) >= 2 or len(open_peers) >= 2:
        return "cluster_same_family"
    return "none"


def _soft_note_for(family: str, pattern_flag: str, *, match: str = "") -> str:
    if pattern_flag == "side_flip_after_fav_win":
        m = (match or "").strip()
        scope = f" matchup={m[:60]}" if m else ""
        return (
            f"side flip after heavy fav HC win{scope} — "
            "form_continuity owns soft-reject; lessons TTL mild only; never hard-reject"
        )
    if pattern_flag == "repeat_type_loss":
        return (
            f"Prefer {family} only with stronger hold-rate / H2H support; "
            "raise evidence bar, do not auto-ban"
        )
    if pattern_flag == "cluster_same_family":
        return f"Cluster of recent {family} — diversify shapes; soft caution only"
    return f"Soft note on {family}"


def _sa_merge_key(sa: dict[str, Any]) -> str:
    """Family key for normal notes; matchup-scoped key for side_flip patterns."""
    fam = str(sa.get("family") or "").strip()
    pf = str(sa.get("pattern_flag") or "")
    if pf == "side_flip_after_fav_win":
        m = str(sa.get("match") or "").strip().lower()
        return f"{fam}|side_flip|{m}"
    return fam


def _sa_sort_priority(sa: dict[str, Any]) -> int:
    pf = str(sa.get("pattern_flag") or "")
    if pf == "repeat_type_loss":
        return 0
    if pf == "side_flip_after_fav_win":
        return 1
    return 2


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
    family_or_rec: Any,
    lessons: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
    *,
    historical_rows: list[dict[str, Any]] | None = None,
    match: str = "",
    form_continuity_soft_rejected: bool = False,
) -> tuple[float, str]:
    """
    Soft EV penalty for family matching active soft_awareness.

    Independent of similar-recent hits (works with similar_count=0).
    Never hard-rejects.

    Call styles
    -----------
    ESR family API::
        lessons_soft_adjustments(family, lessons, cfg)

    Portfolio rec API (form_continuity PR2 wire-up)::
        lessons_soft_adjustments(rec, cfg=cfg, historical_rows=...)

    Double-count guard (PR6 ``side_flip_after_fav_win``)
    ----------------------------------------------------
    * Pattern is **TTL soft only** — never hard-reject.
    * Family pen stays **mild** (``soft_ev_penalty_repeat_loss``, default 0.008).
    * Prefer **matchup-scoped** notes: when SA carries ``match`` or ``scope=matchup``,
      only same-matchup seats take the side_flip pen. Empty candidate match is
      **fail-closed** (skip pen) so family-wide hammers cannot land by accident.
    * If ``form_continuity_soft_rejected`` (or rec already has a ``form_continuity:``
      reject), skip the side_flip pen so lessons do not stack on top of continuity.
      Portfolio must call lessons **after** form_continuity so this flag is live.
    """
    # --- resolve call style ---
    fam = ""
    cand_match = (match or "").strip()
    rec_obj: Any = None
    if isinstance(family_or_rec, str):
        fam = family_or_rec.strip()
    elif family_or_rec is None:
        fam = ""
    else:
        # Recommendation-like or dict
        rec_obj = family_or_rec
        if isinstance(family_or_rec, dict):
            fam = str(
                family_or_rec.get("market_family")
                or family_or_rec.get("market_family_key")
                or family_or_rec.get("market_key")
                or ""
            ).strip()
            if not cand_match:
                cand_match = str(family_or_rec.get("match") or "").strip()
            if cfg is None and isinstance(lessons, dict) and (
                "learning" in lessons or "paths" in lessons
            ):
                # Positional cfg passed as second arg under rec-style misuse
                cfg = lessons
                lessons = None
        else:
            fam = str(
                getattr(family_or_rec, "market_family", None)
                or getattr(family_or_rec, "market_key", None)
                or ""
            ).strip()
            if not fam:
                try:
                    fam = _row_family(
                        {
                            "sport": getattr(family_or_rec, "sport", "") or "",
                            "selection": getattr(family_or_rec, "selection", "") or "",
                            "market_type": getattr(family_or_rec, "market_type", "") or "",
                            "market_key": getattr(family_or_rec, "market_key", "") or "",
                        }
                    )
                except Exception:  # noqa: BLE001
                    fam = "other"
            if not cand_match:
                cand_match = str(getattr(family_or_rec, "match", "") or "").strip()
            # Portfolio: lessons_soft_fn(rec, cfg=cfg, historical_rows=...)
            if lessons is not None and cfg is None and isinstance(lessons, dict):
                # unlikely; keep lessons
                pass
            if lessons is None and cfg is not None:
                try:
                    lessons = load_settlement_lessons(cfg)
                except Exception:  # noqa: BLE001
                    lessons = empty_lessons_payload()
            # Detect form_continuity soft_reject already recorded on rec
            if not form_continuity_soft_rejected:
                rr = str(getattr(family_or_rec, "reject_reason", "") or "")
                if rr.startswith("form_continuity:"):
                    form_continuity_soft_rejected = True
                fcr = str(getattr(family_or_rec, "form_continuity_reason", "") or "")
                if fcr.startswith("form_continuity:") and "weak" in fcr.lower():
                    # reason alone is not reject; leave flag unless reject_reason set
                    pass

    # When family API passed lessons without cfg as third positional, ok
    if cfg is None and isinstance(lessons, dict) and "learning" in lessons:
        cfg = lessons
        lessons = None

    sl = settlement_lessons_cfg(cfg)
    if not sl.get("enabled", True):
        return 0.0, ""
    pen_unit = float(sl.get("soft_ev_penalty_repeat_loss") or 0.008)
    if not fam and rec_obj is not None:
        fam = "other"
    if not fam:
        return 0.0, ""

    pen = 0.0
    reasons: list[str] = []
    side_flip_applied = False
    family_caution_applied = False

    for sa in active_soft_awareness(lessons):
        if str(sa.get("family") or "").strip() != fam:
            continue
        pf = str(sa.get("pattern_flag") or "")
        note = str(sa.get("note") or "")

        if pf == "side_flip_after_fav_win":
            # Double-count guard: form_continuity already owns soft-reject for the flip
            if form_continuity_soft_rejected:
                continue
            sa_match = str(sa.get("match") or "").strip()
            matchup_scoped = (
                str(sa.get("scope") or "").strip().lower() == "matchup" or bool(sa_match)
            )
            if matchup_scoped:
                # Fail-closed: empty candidate match must not apply family-wide
                if not cand_match:
                    continue
                if sa_match and sa_match.lower() != cand_match.lower():
                    continue
            # Mild only; never stack multiple side_flip notes
            if side_flip_applied:
                continue
            pen += pen_unit
            side_flip_applied = True
            reasons.append(f"lessons_soft: {fam} (side_flip_after_fav_win)")
            continue

        if pf in ("repeat_type_loss", "cluster_same_family") or "caution" in note.lower():
            # Cap normal family caution at one unit when side_flip already applied
            # (avoid stacking large pens onto the same family from flip + caution)
            if side_flip_applied and family_caution_applied:
                continue
            if family_caution_applied and pf != "repeat_type_loss":
                continue
            pen += pen_unit
            family_caution_applied = True
            reasons.append(f"lessons_soft: {fam} ({pf or 'caution'})")

    # Hard cap: side_flip path never exceeds one mild unit alone; with family
    # caution allow at most 2× mild (repeat loss + flip) — never a "large" stack.
    max_pen = pen_unit * 2.0
    if pen > max_pen + 1e-12:
        pen = max_pen

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

    # live_ledger_only is always enforced (informational in config; archive peers forbidden)
    live = filter_live_rows(live_rows)
    # Settled-only peers for loss/win repeat detection (open tickets do not crowd out history)
    settled_window = recent_live_window(live, n=window_n, settled_only=True)
    # Open tickets only for cluster_same_family visibility (no soft_awareness by itself)
    open_window = recent_live_window(live, n=window_n, settled_only=False)

    # Enrich thin settle summaries from full ledger rows by bet_id
    by_id: dict[str, dict[str, Any]] = {}
    for r in live_rows or []:
        if not isinstance(r, dict):
            continue
        bid = str(r.get("bet_id") or "").strip()
        if bid:
            by_id[bid] = r

    bet_entries: list[dict[str, Any]] = []
    family_loss_counts: dict[str, int] = {}

    for raw_bet in settled_batch:
        bet = dict(raw_bet)
        ledger = by_id.get(str(bet.get("bet_id") or "").strip()) or {}
        # Prefer settle-batch fields; fill gaps from post-write ledger row
        for k in (
            "market_type",
            "market_key",
            "p_model",
            "sport",
            "selection",
            "match",
            "notes",
        ):
            if bet.get(k) in (None, "") and ledger.get(k) not in (None, ""):
                bet[k] = ledger.get(k)
        # main_reason from item/agent if present on either side
        if not bet.get("main_reason") and ledger.get("main_reason"):
            bet["main_reason"] = ledger.get("main_reason")

        fam = _row_family(bet)
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
        pattern = detect_pattern_flag(
            bet,
            family=fam,
            window=settled_window,
            open_window=open_window,
            cfg=cfg,
        )
        match_s = str(bet.get("match") or "")
        soft_note = ""
        # Soft note prose on bet; soft_awareness emission is loss-linked / side_flip
        if pattern in (
            "repeat_type_loss",
            "cluster_same_family",
            "side_flip_after_fav_win",
        ):
            soft_note = _soft_note_for(fam, pattern, match=match_s)
        if str(bet.get("result") or "") == "Loss":
            family_loss_counts[fam] = family_loss_counts.get(fam, 0) + 1

        bet_entries.append(
            {
                "bet_id": str(bet.get("bet_id") or ""),
                "match": match_s,
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

    # Soft awareness: previous non-expired + new from loss patterns / batch multi-loss
    # (cluster_same_family alone on open tickets does NOT create soft_awareness)
    # side_flip_after_fav_win is matchup-scoped TTL soft only (never hard-reject)
    prev = load_settlement_lessons(cfg)
    merged: dict[str, dict[str, Any]] = {}
    for sa in active_soft_awareness(prev, now=now_dt):
        key = _sa_merge_key(sa)
        if key:
            merged[key] = dict(sa)

    expires_at = (now_dt + timedelta(hours=ttl_h)).strftime("%Y-%m-%dT%H:%M:%SZ")
    created_at = now_s if now_s.endswith("Z") else now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    for entry in bet_entries:
        pf = entry.get("pattern_flag") or "none"
        fam = entry.get("market_family") or ""
        match_s = str(entry.get("match") or "")
        # Soft awareness for side_flip is loss-linked only
        if (
            pf == "side_flip_after_fav_win"
            and fam
            and str(entry.get("result") or "") == "Loss"
        ):
            sa_entry = {
                "family": fam,
                "match": match_s,
                "note": (
                    f"temporary caution — side flip after heavy fav HC win"
                    f"{f' ({match_s[:60]})' if match_s else ''}; "
                    "form_continuity owns soft-reject; mild family caution only; "
                    "never hard-reject"
                ),
                "pattern_flag": "side_flip_after_fav_win",
                "scope": "matchup",
                "form_continuity_primary": True,
                "never_hard_reject": True,
                "created_at": created_at,
                "expires_at": expires_at,
                "expired": False,
            }
            merged[_sa_merge_key(sa_entry)] = sa_entry
        elif pf == "repeat_type_loss" and fam:
            sa_entry = {
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
            merged[_sa_merge_key(sa_entry)] = sa_entry

    for fam, n_loss in family_loss_counts.items():
        if n_loss >= 2:
            existing = merged.get(fam)
            if not existing or existing.get("pattern_flag") not in (
                "repeat_type_loss",
                "side_flip_after_fav_win",
            ):
                sa_entry = {
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
                merged[_sa_merge_key(sa_entry)] = sa_entry

    soft_list = list(merged.values())
    # Cap keeps freshest notes: sort freshest-first, then promote loss/side_flip
    soft_list.sort(
        key=lambda s: str(s.get("created_at") or ""),
        reverse=True,  # newest created_at first
    )
    soft_list.sort(key=_sa_sort_priority)  # stable: loss → side_flip → other
    soft_list = soft_list[:max_notes]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": created_at,
        "settled_at": created_at,
        "batch_id": _batch_id(created_at),
        # Always true in v1 — config key is informational / fail-closed documentation
        "live_ledger_only": True,
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
        match_bit = ""
        if sa.get("match") and sa.get("pattern_flag") == "side_flip_after_fav_win":
            match_bit = f" · matchup: {(sa.get('match') or '')[:60]}"
        lines.append(
            f"- **{sa.get('family')}** (`{sa.get('pattern_flag')}`) — "
            f"{sa.get('note')} · {exp}{match_bit}"
        )
    lines.append("")
    lines.append(
        "_Soft notes only — never permanent hard rejects. "
        "Portfolio applies `lessons_soft:` demotion independently of similar-recent. "
        "`side_flip_after_fav_win` is TTL soft / matchup-scoped (mild 0.008); "
        "form_continuity owns place-path soft-reject — lessons never hard-reject._"
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
