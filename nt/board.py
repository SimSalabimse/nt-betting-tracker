from __future__ import annotations

"""
Board research workflow — shortlist + scaffold before recommend.

Makes the wrong path (bare recommend with zero evidence) hard:
  1. research board --odds …   → shortlist, report, optional scaffolds
  2. fill p_model / takeaways
  3. recommend --odds …        → engine sizes (or refuses if still no research)

Code is law at step 3. Research is mandatory at steps 1–2.

Diversity law (v7):
  - Market type is NOT a quality filter. ML / O-U / BTTS / DNB / HC /
    player props / period (1H) lines all compete on researchability.
  - Football must not monopolize the shortlist when other sports are present.
  - Thin sports need board slots so the book can *generate* sample for them.
"""

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from nt.bets_io import odds_band
from nt.config import path_from_config
from nt.odds_parse import Candidate, attach_evidence, parse_odds_file
from nt.research import checklist_for, list_sources, scaffold_evidence
from nt.sport_taxonomy import normalize_sport


# Priority = weak tie-break only (lower slightly preferred). EV research treats all equal.
_MAIN_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    ("ml_home_away", re.compile(r"to win\s*$", re.I), 12),
    ("ml_vinner", re.compile(r"^vinner\s*:", re.I), 12),
    ("ml_vinner_loose", re.compile(r"^vinner\b", re.I), 13),
    ("ml_incl_ot", re.compile(r"vinner\s*\(inkludert overtid", re.I), 12),
    ("draw", re.compile(r"^uavgjort\s*$", re.I), 14),
    ("btts", re.compile(r"btts|begge lag scorer", re.I), 12),
    ("ou_25", re.compile(r"over/under\s*2\.5|over 2\.5|under 2\.5", re.I), 12),
    ("ou_15", re.compile(r"over/under\s*1\.5|over 1\.5|under 1\.5", re.I), 13),
    ("ou_35", re.compile(r"over/under\s*3\.5|over 3\.5|under 3\.5", re.I), 13),
    ("ou_other", re.compile(r"over/under\s*\d|totalt antall (mål|games|kart|points?)", re.I), 14),
    ("dnb", re.compile(r"tilbakebetales|draw no bet|\bdnb\b", re.I), 12),
    ("dc", re.compile(r"dobbel sjanse|double chance", re.I), 15),
    ("hcap_main", re.compile(r"handikap|handicap|asian", re.I), 12),
    ("hcap_spread", re.compile(r"[+-]\s?\d+(?:[.,]\d+)?(?:\s*(?:sets?|maps?|games?))?\s*$", re.I), 13),
    ("map_hc", re.compile(r"[+-]\s?\d+(?:[.,]\d+)?\s*\(?\s*maps?|kart handikap|maps?\s*hand", re.I), 13),
    ("set_hc", re.compile(r"[+-]\s?\d+(?:[.,]\d+)?\s*sets?\b", re.I), 13),
    # Period / half markets (1. omgang, first half, 1H)
    (
        "period_ou",
        re.compile(
            r"1\.\s*omgang.*over/under|2\.\s*omgang.*over/under|"
            r"1st half|first half|2nd half|second half|"
            r"omgang - totalt|1H |2H ",
            re.I,
        ),
        13,
    ),
    ("period_ml", re.compile(r"1\.\s*omgang\s*-\s*hub|1\.\s*omgang.*hub|1st half result|ht result", re.I), 14),
    # Player / anytime props — first-class for research (need strong evidence when high odds)
    (
        "player_score",
        re.compile(
            r"to score|anytime|målscorer|scorer mål|scorer\b|player to score|"
            r"scorer:|spiller .+ scorer",
            re.I,
        ),
        14,
    ),
    ("team_total", re.compile(r"totalt antall \w+ mål|team total|lag total", re.I), 14),
    ("clean_sheet", re.compile(r"holder nullen|clean sheet", re.I), 15),
    ("first_goal", re.compile(r"1\.\s*mål|first goal|første mål", re.I), 15),
    # Corners — optional alt (not pure spam if main corner total)
    ("corners", re.compile(r"hjørne|corner", re.I), 16),
]

# Hard noise only — longshot junk that floods boards without research value
_HARD_NOISE = re.compile(
    r"korrekt resultat|correct score|"
    r"omgang med flest|"
    r"begge omganger over|"
    r"scorer i begge omganger|"
    r"hub og begge|"
    r"10 min - hub|"
    r"booking|antall kort|"
    r"rødt kort|"
    r"score \d+-\d+",
    re.I,
)

_FAMILY_MACRO: dict[str, str] = {
    "ml_home_away": "ml",
    "ml_vinner": "ml",
    "ml_vinner_loose": "ml",
    "ml_incl_ot": "ml",
    "draw": "ml",
    "btts": "btts",
    "ou_25": "totals",
    "ou_15": "totals",
    "ou_35": "totals",
    "ou_other": "totals",
    "dnb": "dnb",
    "dc": "dc",
    "hcap_main": "handicap",
    "hcap_spread": "handicap",
    "map_hc": "handicap",
    "set_hc": "handicap",
    "period_ou": "period",
    "period_ml": "period",
    "player_score": "props",
    "team_total": "props",
    "clean_sheet": "props",
    "first_goal": "props",
    "corners": "props",
}


@dataclass
class ShortlistItem:
    match: str
    selection: str
    decimal_odds: float
    sport: str
    market_type: str
    market_family: str
    priority: int
    odds_band: str
    implied_prob: float
    has_evidence: bool
    has_p_model: bool
    p_model: float | None
    evidence_grade_hint: str
    research_ready: bool
    score: float
    notes: list[str] = field(default_factory=list)


def _family(selection: str, market_type: str = "") -> tuple[str, int] | None:
    blob = f"{selection} {market_type}"
    if _HARD_NOISE.search(blob):
        # Allow if also a clean main pattern (rare)
        if not re.search(r"to win|vinner:|btts|begge lag scorer|over/under 2\.5", blob, re.I):
            return None
    best: tuple[str, int] | None = None
    for name, pat, pri in _MAIN_PATTERNS:
        if pat.search(selection) or pat.search(market_type or ""):
            if best is None or pri < best[1]:
                best = (name, pri)
    return best


def _fam_key(it: ShortlistItem) -> str:
    fam_key = it.market_family
    sel = it.selection.lower()
    if it.market_family.startswith("ou_") or it.market_family in ("ou_other", "period_ou"):
        fam_key = f"{it.market_family}:{'O' if 'over' in sel else 'U'}"
    if it.market_family == "btts":
        fam_key = f"btts:{'Y' if 'ja' in sel or 'yes' in sel else 'N'}"
    if it.market_family == "player_score":
        # one player prop slot per match by selection prefix
        fam_key = f"prop:{sel[:40]}"
    return fam_key


def _macro(family: str) -> str:
    return _FAMILY_MACRO.get(family, family)


def _sport_key(sport: str) -> str:
    """Canonical diversify key (nba/wnba→basketball, LoL→esports, …)."""
    return normalize_sport(sport, default="unknown")


def _is_processable_odds(odds: float, thr_high: float = 2.5) -> bool:
    # Props often sit 1.8–4.5; allow slightly longer for research shortlist
    return 1.25 <= odds <= 5.5


def _score_item(
    c: Candidate,
    family: str,
    priority: int,
    *,
    has_ev: bool,
    has_p: bool,
    high_thr: float,
    learn: dict[str, Any] | None = None,
) -> float:
    """Higher = more worth researching. Priority is a weak nudge only."""
    odds = float(c.decimal_odds)
    score = 80.0 - float(priority) * 0.35
    if 1.45 <= odds <= 2.20:
        score += 25
    elif 1.30 <= odds < 1.45 or 2.20 < odds <= 2.50:
        score += 12
    elif odds > high_thr:
        score -= 8  # still shortlistable; needs grade A later
    if has_ev and has_p:
        score += 40
    elif has_ev:
        score += 15

    # Multi-sport: boost thin sports so football volume does not own the board
    sp = _sport_key(c.sport)
    sports = (learn or {}).get("sports") or {}
    g = sports.get(sp) or {}
    n = int(g.get("n") or 0)
    if sp and sp != "football":
        if n < 12:
            score += 18  # strong research priority for thin sports
        elif n < 25:
            score += 8
    if sp == "football" and n >= 80:
        score -= 6  # slight deprioritize when already data-rich

    # Thin market families (props / period) need board airtime
    mac = _macro(family)
    markets = (learn or {}).get("markets") or {}
    # Infer rough sample from known keys
    if mac in ("props", "period"):
        score += 10
    return score


def shortlist_board(
    candidates: list[Candidate],
    cfg: dict[str, Any],
    *,
    max_per_match: int = 5,
    max_total: int = 24,
    include_ready: bool = True,
) -> list[ShortlistItem]:
    """
    Collapse a full NT dump into a researchable shortlist.

    Enforces:
      - multi-macro per match (not ML-only)
      - multi-sport board when odds file has multiple sports
      - room for props / period markets
    """
    sel_cfg = cfg.get("selection") or {}
    high_thr = float(sel_cfg.get("high_odds_threshold", 2.5))
    rcfg = cfg.get("research") or {}
    # Config supplies defaults; explicit function args win when caller sets them
    if rcfg.get("board_max_total") is not None and max_total in (16, 24):
        max_total = int(rcfg["board_max_total"])
    if rcfg.get("board_max_per_match") is not None and max_per_match in (5, 6):
        max_per_match = int(rcfg["board_max_per_match"])
    max_football_share = float(rcfg.get("board_max_football_share", 0.45))
    min_non_football = int(rcfg.get("board_min_non_football", 4))
    max_props_board = int(rcfg.get("board_max_props", 4))

    learn: dict[str, Any] = {}
    try:
        from nt.learning import load_learning

        learn = load_learning(cfg) or {}
    except Exception:
        learn = {}

    by_match: dict[str, list[Candidate]] = defaultdict(list)
    for c in candidates:
        by_match[c.match or "?"].append(c)

    items: list[ShortlistItem] = []
    for match, rows in by_match.items():
        match_items: list[ShortlistItem] = []
        for c in rows:
            fam = _family(c.selection or "", c.market_type or "")
            if fam is None:
                continue
            family, pri = fam
            odds = float(c.decimal_odds)
            if not _is_processable_odds(odds, high_thr):
                continue
            has_ev = bool(c.evidence)
            p = c.p_model
            if p is None and c.evidence and c.evidence.get("p_model") is not None:
                try:
                    p = float(c.evidence["p_model"])
                except (TypeError, ValueError):
                    p = None
            has_p = p is not None
            ready = has_ev and has_p and bool((c.evidence or {}).get("summary")) and bool(
                (c.evidence or {}).get("failure_modes")
            )
            notes: list[str] = []
            if odds >= high_thr:
                notes.append("high_odds→needs grade A")
            if _macro(family) == "props":
                notes.append("prop/period-alt — require solid evidence")
            if not has_ev:
                notes.append("needs evidence pack")
            elif not has_p:
                notes.append("evidence missing p_model")
            if ready:
                notes.append("research_ready")

            sc = _score_item(
                c, family, pri, has_ev=has_ev, has_p=has_p, high_thr=high_thr, learn=learn
            )
            match_items.append(
                ShortlistItem(
                    match=c.match,
                    selection=c.selection,
                    decimal_odds=odds,
                    sport=normalize_sport(c.sport or "", default="unknown")
                    if (c.sport or "").strip()
                    else "",
                    market_type=c.market_type or "",
                    market_family=family,
                    priority=pri,
                    odds_band=odds_band(odds),
                    implied_prob=round(1.0 / odds, 4) if odds > 0 else 0.0,
                    has_evidence=has_ev,
                    has_p_model=has_p,
                    p_model=p,
                    evidence_grade_hint="A_required" if odds >= high_thr else "B_ok",
                    research_ready=ready,
                    score=sc,
                    notes=notes,
                )
            )

        match_items.sort(key=lambda x: (-x.score, x.priority, x.decimal_odds))
        seen_fam: set[str] = set()
        seen_macro: set[str] = set()
        picked_m: list[ShortlistItem] = []

        def _try_pick(it: ShortlistItem, *, force_macro: bool = False) -> bool:
            fk = _fam_key(it)
            mac = _macro(it.market_family)
            if fk in seen_fam:
                return False
            if mac in seen_macro and not force_macro and len(seen_macro) < 3:
                return False
            seen_fam.add(fk)
            seen_macro.add(mac)
            picked_m.append(it)
            return True

        macros_wanted = ("ml", "totals", "btts", "dnb", "handicap", "period", "props")
        for mac in macros_wanted:
            if len(picked_m) >= max_per_match:
                break
            for it in match_items:
                if _macro(it.market_family) != mac:
                    continue
                if _try_pick(it):
                    break
        for it in match_items:
            if len(picked_m) >= max_per_match:
                break
            _try_pick(it, force_macro=True)
        items.extend(picked_m)

    items.sort(key=lambda x: (-x.score, x.match, x.priority))
    if not include_ready:
        items = [i for i in items if not i.research_ready]

    max_total = max(10, int(max_total))
    sports_present = {_sport_key(c.sport) for c in candidates if _sport_key(c.sport) != "unknown"}
    non_fb_present = {s for s in sports_present if s != "football"}

    # --- Pass A: ensure non-football representation ---
    final: list[ShortlistItem] = []
    picked_ids: set[tuple[str, str, float]] = set()
    n_fb = n_props = 0
    n_by_sport: dict[str, int] = defaultdict(int)

    def _add(it: ShortlistItem) -> bool:
        nonlocal n_fb, n_props
        tid = (it.match, it.selection, it.decimal_odds)
        if tid in picked_ids:
            return False
        if len(final) >= max_total:
            return False
        sp = _sport_key(it.sport)
        mac = _macro(it.market_family)
        if mac == "props" and n_props >= max_props_board:
            return False
        # Football share cap when other sports exist (hard ceiling on football slots)
        if sp == "football" and non_fb_present:
            fb_cap = max(1, int(max_total * max_football_share))
            # Also leave room for remaining min_non_football obligations
            non_fb_now = len(final) - n_fb
            still_need_non = max(0, min_non_football - non_fb_now)
            room = max_total - len(final)
            if n_fb >= fb_cap or (room <= still_need_non and still_need_non > 0):
                return False
        final.append(it)
        picked_ids.add(tid)
        n_by_sport[sp] += 1
        if sp == "football":
            n_fb += 1
        if mac == "props":
            n_props += 1
        return True

    # A1: pull best line per non-football sport first
    if non_fb_present:
        by_sp: dict[str, list[ShortlistItem]] = defaultdict(list)
        for it in items:
            sp = _sport_key(it.sport)
            if sp != "football" and sp in non_fb_present:
                by_sp[sp].append(it)
        for sp in sorted(by_sp.keys(), key=lambda s: -((learn.get("sports") or {}).get(s) or {}).get("roi_blended", 0) if (learn.get("sports") or {}).get(s) else 0):
            for it in sorted(by_sp[sp], key=lambda x: -x.score):
                if _add(it):
                    break
        # A2: fill min_non_football slots
        need = max(0, min_non_football - sum(1 for i in final if _sport_key(i.sport) != "football"))
        for it in items:
            if need <= 0 or len(final) >= max_total:
                break
            if _sport_key(it.sport) == "football":
                continue
            if _add(it):
                need -= 1

    # A3: fill rest by score with macro diversity soft preference
    max_ml = max(3, int(max_total * 0.35))
    max_totals = max(3, int(max_total * 0.30))
    n_ml = n_tot = 0
    deferred: list[ShortlistItem] = []
    for it in items:
        if len(final) >= max_total:
            break
        mac = _macro(it.market_family)
        if mac == "ml" and n_ml >= max_ml:
            deferred.append(it)
            continue
        if mac == "totals" and n_tot >= max_totals:
            deferred.append(it)
            continue
        if _add(it):
            if mac == "ml":
                n_ml += 1
            elif mac == "totals":
                n_tot += 1
    for it in deferred:
        if len(final) >= max_total:
            break
        _add(it)

    # A4: ensure at least one prop/period if available on board
    have_macros = {_macro(i.market_family) for i in final}
    for want in ("period", "props"):
        if want in have_macros or len(final) >= max_total:
            continue
        for it in items:
            if _macro(it.market_family) != want:
                continue
            if _add(it):
                break

    final.sort(key=lambda x: (-x.score, x.match, x.priority))
    return final[:max_total]


def board_coverage(candidates: list[Candidate]) -> dict[str, Any]:
    n = len(candidates)
    with_ev = sum(1 for c in candidates if c.evidence)
    with_p = 0
    for c in candidates:
        p = c.p_model
        if p is None and c.evidence and c.evidence.get("p_model") is not None:
            p = c.evidence.get("p_model")
        if p is not None:
            with_p += 1
    matches = sorted({c.match for c in candidates if c.match})
    sports: dict[str, int] = defaultdict(int)
    macros: dict[str, int] = defaultdict(int)
    for c in candidates:
        sports[(c.sport or "unknown").lower()] += 1
        fam = _family(c.selection or "", c.market_type or "")
        if fam:
            macros[_macro(fam[0])] += 1
    return {
        "n_candidates": n,
        "n_matches": len(matches),
        "matches": matches,
        "sports": dict(sports),
        "market_macros_available": dict(macros),
        "n_with_evidence": with_ev,
        "n_with_p_model": with_p,
        "research_coverage_pct": round(100.0 * with_p / n, 2) if n else 0.0,
        "ready_for_recommend": with_p > 0,
    }


def run_board_research(
    cfg: dict[str, Any],
    odds_path: Path,
    *,
    write_scaffolds: bool = False,
    write_report: bool = True,
    max_per_match: int = 5,
    max_total: int = 24,
    overwrite_scaffolds: bool = False,
    market_coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Full board research gate:

    parse → (optional market coverage) → attach evidence → shortlist → scaffolds → report
    """
    rcfg = cfg.get("research") or {}
    max_per_match = int(rcfg.get("board_max_per_match") or max_per_match)
    max_total = int(rcfg.get("board_max_total") or max_total)

    candidates = parse_odds_file(odds_path)
    attach_evidence(candidates, path_from_config(cfg, "evidence"))
    coverage = board_coverage(candidates)
    shortlist = shortlist_board(
        candidates,
        cfg,
        max_per_match=max_per_match,
        max_total=max_total,
    )

    # Boost shortlist with market-scan "interesting" flags from high-volume boards
    if market_coverage and not market_coverage.get("error"):
        shortlist = _merge_coverage_into_shortlist(
            shortlist, candidates, market_coverage, cfg, max_total=max_total
        )

    scaffolds: list[dict[str, Any]] = []
    if write_scaffolds:
        for it in shortlist:
            if it.has_evidence and it.has_p_model and not overwrite_scaffolds:
                scaffolds.append(
                    {
                        "match": it.match,
                        "selection": it.selection,
                        "skipped": True,
                        "reason": "already has evidence+p_model",
                    }
                )
                continue
            res = scaffold_evidence(
                cfg,
                match=it.match,
                selection=it.selection,
                sport=it.sport or "football",
                odds=it.decimal_odds,
                p_model=None,
                write=True,
            )
            scaffolds.append(
                {
                    "match": it.match,
                    "selection": it.selection,
                    "path": res.get("path"),
                    "ok": res.get("ok"),
                    "skipped": False,
                }
            )

    # Stage 1 Light Research (broad coverage) — auto unless disabled
    light_payload: dict[str, Any] | None = None
    rcfg_tiers = (cfg.get("research") or {}).get("tiers") or {}
    auto_light = bool(rcfg_tiers.get("auto_light_on_board", True))
    if auto_light and shortlist:
        try:
            from nt.light_research import run_light_research

            light_payload = run_light_research(
                cfg,
                odds_path,
                shortlist,
                write=write_report,
            )
        except Exception as ex:  # noqa: BLE001
            light_payload = {"error": str(ex)}

    md = render_board_markdown(
        odds_path,
        coverage,
        shortlist,
        cfg=cfg,
        market_coverage=market_coverage,
        light_research=light_payload,
    )
    report_path: Path | None = None
    if write_report:
        outbox = path_from_config(cfg, "outbox")
        outbox.mkdir(parents=True, exist_ok=True)
        day = date.today().isoformat()
        report_path = outbox / f"RESEARCH_BOARD_{day}.md"
        report_path.write_text(md, encoding="utf-8")
        latest = outbox / "RESEARCH_BOARD.md"
        latest.write_text(md, encoding="utf-8")

    return {
        "odds_path": str(odds_path),
        "coverage": coverage,
        "n_shortlist": len(shortlist),
        "shortlist": [asdict(s) for s in shortlist],
        "scaffolds": scaffolds,
        "report_path": str(report_path) if report_path else None,
        "markdown": md,
        "sport_mix": _shortlist_sport_mix(shortlist),
        "macro_mix": _shortlist_macro_mix(shortlist),
        "market_coverage": market_coverage,
        "light_research": light_payload,
    }


def _merge_coverage_into_shortlist(
    shortlist: list[ShortlistItem],
    candidates: list[Candidate],
    market_coverage: dict[str, Any],
    cfg: dict[str, Any],
    *,
    max_total: int,
) -> list[ShortlistItem]:
    """Inject flagged interesting lines from market scans into shortlist."""
    scans = market_coverage.get("scans") or (
        [market_coverage["scan"]] if market_coverage.get("scan") else []
    )
    if not scans:
        return shortlist

    by_key = {(s.match, s.selection): s for s in shortlist}
    cand_index: dict[tuple[str, str], Candidate] = {
        (c.match, c.selection): c for c in candidates
    }

    high_thr = float((cfg.get("risk") or {}).get("high_odds_threshold") or 2.5)
    added = 0
    for sc in scans:
        if not sc.get("high_volume") and int(sc.get("total_lines") or 0) < 40:
            continue
        for it in (sc.get("interesting") or [])[:12]:
            sel = it.get("selection") or ""
            match = sc.get("match") or ""
            key = (match, sel)
            if key in by_key:
                # Annotate existing
                by_key[key].notes.append("market_scan:interesting")
                continue
            # Find candidate (match string may differ slightly)
            c = cand_index.get(key)
            if not c:
                for (m, s), cc in cand_index.items():
                    if s == sel and (
                        match.lower() in (m or "").lower()
                        or (m or "").lower() in match.lower()
                    ):
                        c = cc
                        key = (m, s)
                        break
            if not c or key in by_key:
                continue
            fam_pri = _family(c.selection, c.market_type or "")
            if not fam_pri:
                # Force as prop/special family for shortlist visibility
                fam_pri = ("player_score", 14)
            family, pri = fam_pri
            has_p = c.p_model is not None
            has_ev = bool(c.evidence)
            item = ShortlistItem(
                match=c.match,
                selection=c.selection,
                decimal_odds=float(c.decimal_odds),
                sport=normalize_sport(c.sport or "", default="unknown")
                if (c.sport or "").strip()
                else "",
                market_type=c.market_type or "",
                market_family=family,
                priority=pri,
                odds_band=odds_band(float(c.decimal_odds)),
                implied_prob=round(1.0 / float(c.decimal_odds), 4),
                has_evidence=has_ev,
                has_p_model=has_p,
                p_model=c.p_model,
                evidence_grade_hint="",
                research_ready=has_p,
                score=70.0,
                notes=[
                    "market_scan:interesting",
                    it.get("reason") or "",
                    f"tier={it.get('tier')}",
                ],
            )
            by_key[key] = item
            added += 1
            if len(by_key) >= max_total + 8:
                break

    out = list(by_key.values())
    out.sort(key=lambda x: -x.score)
    # Prefer keeping original length bound but allow a few coverage injects
    return out[: max(max_total, min(len(out), max_total + min(6, added)))]


def _shortlist_sport_mix(shortlist: list[ShortlistItem]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for s in shortlist:
        out[_sport_key(s.sport)] += 1
    return dict(out)


def _shortlist_macro_mix(shortlist: list[ShortlistItem]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for s in shortlist:
        out[_macro(s.market_family)] += 1
    return dict(out)


def render_board_markdown(
    odds_path: Path,
    coverage: dict[str, Any],
    shortlist: list[ShortlistItem],
    *,
    cfg: dict[str, Any] | None = None,
    market_coverage: dict[str, Any] | None = None,
    light_research: dict[str, Any] | None = None,
) -> str:
    day = date.today().isoformat()
    lines = [
        f"# Research Board — {day}",
        "",
        f"**Odds file:** `{odds_path}`",
        "",
        "## Workflow (tiered research — mandatory)",
        "",
        "1. **Market coverage** on high-volume matches",
        "2. **Shortlist** (this board)",
        "3. **Stage 1 — Light Research** on ≥70–85% of shortlist (auto + agent review)",
        "4. **Stage 2 — Deep Research** only light-pass promotions → full `evidence/*.json` + honest `p_model`",
        "5. **Recommend** — **only Deep** lines can place (engine requires p_model)",
        "6. **Place** only `outbox/PLACE_THESE.md`",
        "",
        "> Wrong path: skip Light coverage then deep-dive 2–3 favorites.  ",
        "> Right path: Light broad filter → Deep on survivors → empty slip OK if none clear.",
        "",
        "## Board coverage",
        "",
        f"- Candidates parsed: **{coverage.get('n_candidates')}**",
        f"- Matches: **{coverage.get('n_matches')}** — {', '.join((coverage.get('matches') or [])[:20])}",
        f"- Sports: {coverage.get('sports')}",
        f"- Market macros in dump: {coverage.get('market_macros_available')}",
        f"- With evidence file: **{coverage.get('n_with_evidence')}**",
        f"- With p_model (Deep): **{coverage.get('n_with_p_model')}**",
        f"- Ready for recommend: **{coverage.get('ready_for_recommend')}**",
        "",
        f"### Shortlist mix — sports: {_shortlist_sport_mix(shortlist)} · macros: {_shortlist_macro_mix(shortlist)}",
        "",
    ]

    # Light research coverage block
    if light_research and not light_research.get("error"):
        st = light_research.get("stats") or {}
        lines.extend(
            [
                "### Light Research (Stage 1)",
                "",
                f"- Assessed: **{st.get('assessed_n', 0)}** / shortlist **{st.get('shortlist_n', 0)}** "
                f"(**{st.get('light_coverage_pct', 0)}%**)",
                f"- Promote to Deep: **{st.get('promote_to_deep_n', 0)}**",
                f"- Coverage OK: **{light_research.get('coverage_ok')}**",
                f"- By verdict: `{st.get('by_verdict')}`",
                f"- Report: `{light_research.get('md_path') or light_research.get('path') or 'outbox/light_research/'}`",
                "",
            ]
        )
        dq = light_research.get("deep_queue") or []
        if dq:
            lines.append("**Deep queue (research these next):**")
            lines.append("")
            for i, r in enumerate(dq[:12], 1):
                lines.append(
                    f"{i}. `{r.get('sport')}` · {(r.get('match') or '')[:40]} · "
                    f"{(r.get('selection') or '')[:45]} @ {r.get('decimal_odds')}"
                )
            lines.append("")
        for w in light_research.get("warnings") or []:
            lines.append(f"- ⚠ {w}")
        if light_research.get("warnings"):
            lines.append("")
    elif light_research and light_research.get("error"):
        lines.append(f"### Light Research error: {light_research.get('error')}")
        lines.append("")

    # Market Coverage Agent summary (high-volume boards)
    if market_coverage and not market_coverage.get("error"):
        lines.extend(_render_market_coverage_section(market_coverage))
    elif market_coverage and market_coverage.get("error"):
        lines.extend(
            [
                "## Market Coverage Agent",
                "",
                f"_Scan error: {market_coverage.get('error')}_",
                "",
            ]
        )

    lines.extend(
        [
        "## Shortlist (research these)",
        "",
        "| # | Match | Sport | Selection | Odds | Band | Family | Ready | Notes |",
        "|---|-------|-------|-----------|------|------|--------|-------|-------|",
        ]
    )
    for i, s in enumerate(shortlist, 1):
        ready = "YES" if s.research_ready else "NO"
        notes = ", ".join(s.notes) if s.notes else "—"
        sel = (s.selection or "")[:42]
        m = (s.match or "")[:28]
        lines.append(
            f"| {i} | {m} | {s.sport or '?'} | {sel} | {s.decimal_odds:.2f} | "
            f"{s.odds_band} | {s.market_family} | {ready} | {notes} |"
        )

    lines.extend(
        [
            "",
            "## Research rules (v7 diversity)",
            "",
            "- Treat **player props**, **1. omgang O/U**, and **handicaps** with the same rigor as HUB/BTTS when data supports them.",
            "- If a non-football line is shortlisted, research it — do not default to the next football ML.",
            "- High-odds props need **grade A** evidence; thin sports may use explore min-EV in the engine.",
            "",
            "## Suggested sources",
            "",
        ]
    )
    for src in list_sources("football"):
        name = src.get("name") or src.get("id") or "source"
        url = src.get("url") or ""
        use = src.get("use") or src.get("kind") or ""
        lines.append(f"- **{name}** — {use} — {url}")

    lines.extend(
        [
            "",
            "## Next commands",
            "",
            "```bash",
            f"python run_nt.py research market-scan --odds {odds_path}",
            f"python run_nt.py research board --odds {odds_path} --write-scaffolds",
            f"python run_nt.py research ready --odds {odds_path}",
            f"python run_nt.py recommend --odds {odds_path} --dry-run",
            f"python run_nt.py recommend --odds {odds_path}",
            "```",
            "",
            "_Generated by `nt research board` + Market Coverage Agent. Multi-sport + multi-market shortlist is code-is-law._",
            "",
        ]
    )
    return "\n".join(lines)


def _render_market_coverage_section(market_coverage: dict[str, Any]) -> list[str]:
    """Compact Market Scan Summary block for the research board."""
    scans = market_coverage.get("scans") or (
        [market_coverage["scan"]] if market_coverage.get("scan") else []
    )
    lines = [
        "## Market Coverage Agent",
        "",
        "Tiered scan of **all lines** on high-volume matches (props, corners, cards, specials) "
        "so research does not tunnel-vision on ML / O2.5 / BTTS.",
        "",
        f"- Mode: `{market_coverage.get('mode')}` · high-volume matches: "
        f"**{market_coverage.get('n_high_volume_matches', 0)}**",
        f"- Threshold: {market_coverage.get('high_volume_threshold', 40)} lines/match",
        "",
    ]
    if not scans:
        lines.append("_No scans produced._")
        lines.append("")
        return lines

    lines.append("| Match | Lines | Coverage conf. | Full board? | Manual review | Top interesting |")
    lines.append("|-------|------:|---------------:|:-----------:|---------------|-----------------|")
    for sc in scans:
        m = (sc.get("match") or "")[:32]
        conf = sc.get("coverage_confidence_pct", 0)
        full = "Yes" if sc.get("full_board_covered") else "No"
        manual = ", ".join(
            t.replace("T1_main", "T1")
            .replace("T2_props", "T2")
            .replace("T3_alt", "T3")
            .replace("T4_specials", "T4")
            for t in (sc.get("manual_review_tiers") or [])[:3]
        ) or "—"
        tops = sc.get("interesting") or []
        top_s = "; ".join(
            f"{(t.get('selection') or '')[:28]}@{t.get('odds')}" for t in tops[:3]
        ) or "—"
        flag = "⚠" if sc.get("needs_manual_review") else "✓"
        lines.append(
            f"| {m} | {sc.get('total_lines')} | **{conf}%** {flag} | {full} | {manual} | {top_s} |"
        )

    lines.extend(
        [
            "",
            "### Per-match notes",
            "",
        ]
    )
    for sc in scans:
        lines.append(
            f"- **{sc.get('match')}**: {sc.get('coverage_note')} "
            f"(T1={ (sc.get('tier_counts') or {}).get('T1_main', 0) }, "
            f"T2={ (sc.get('tier_counts') or {}).get('T2_props', 0) }, "
            f"T3={ (sc.get('tier_counts') or {}).get('T3_alt', 0) }, "
            f"T4={ (sc.get('tier_counts') or {}).get('T4_specials', 0) })"
        )
        if sc.get("needs_manual_review"):
            lines.append(
                f"  - → Manual review: {', '.join(sc.get('manual_review_tiers') or [])}"
            )
    lines.extend(
        [
            "",
            "Full reports: `outbox/market_scans/*.md`",
            "",
            "```bash",
            "python run_nt.py research market-scan --odds <file> --match \"Frankrike\"",
            "```",
            "",
        ]
    )
    return lines


def research_readiness(cfg: dict[str, Any], odds_path: Path) -> dict[str, Any]:
    """Whether recommend is allowed for this odds file."""
    candidates = parse_odds_file(odds_path)
    attach_evidence(candidates, path_from_config(cfg, "evidence"))
    cov = board_coverage(candidates)
    rcfg = cfg.get("research") or {}
    require = rcfg.get("require_research_for_recommend", True)
    allow = bool(cov.get("ready_for_recommend")) or not require
    return {
        "allow_recommend": allow,
        "require_research": require,
        "coverage": cov,
        "message": (
            "Research present — recommend allowed"
            if allow
            else "No p_model/evidence on board — run research board first"
        ),
    }
