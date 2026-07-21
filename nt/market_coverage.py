from __future__ import annotations

"""
Market Coverage Agent — exhaustive scan of all lines on a match before deep research.

For high-volume boards (international, WC, big leagues with 100+ markets), the
system historically gravitated to ML / O2.5 / BTTS. This module forces a tiered
pass across the full board and emits a structured Market Scan Summary.

Does not place bets. Outputs JSON + markdown for agents and LuminaNT.
"""

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nt.bets_io import odds_band
from nt.config import path_from_config
from nt.odds_parse import Candidate, parse_odds_file


# ---------------------------------------------------------------------------
# Tier taxonomy
# ---------------------------------------------------------------------------

TIER_1 = "T1_main"  # ML, draw, O/U, BTTS, Asian/3-way HC, team totals
TIER_2 = "T2_props"  # Player props, goalscorer, anytime, 180s, etc.
TIER_3 = "T3_alt"  # Corners, cards, halves, booking points
TIER_4 = "T4_specials"  # SGPs, multi-leg specials, exotic

TIER_LABELS = {
    TIER_1: "Tier 1 — Main board (ML, draw, O/U, BTTS, HC, team totals)",
    TIER_2: "Tier 2 — Player props & goalscorer",
    TIER_3: "Tier 3 — Corners, cards, halves, periods",
    TIER_4: "Tier 4 — Specials & same-game parlays",
}

# Patterns for tier assignment (order matters: first match wins)
_TIER_RULES: list[tuple[str, re.Pattern[str]]] = [
    # Tier 4 first (exotics contain words that might match lower tiers)
    (
        TIER_4,
        re.compile(
            r"&| og |samt|scorer før|100 sekund|utsiden av|heading|straffespark.*og|"
            r"flest kortpoeng\?|scorer minst \d|og over \d|og under \d|"
            r"vinner og holder nullen|vinner begge omgang|"
            r"begge lag scorer og over/under|"
            r"spesial|special|parlay|sgp|combo",
            re.I,
        ),
    ),
    (
        TIER_2,
        re.compile(
            r"målscorer|kampens 1\.\s*målscorer|anytime|to score|scorer mål|"
            r"spiller .+ scorer|^\w[\w\.\- ]{1,40} scorer|"
            r"totalt antall 180|180s|checkout|player|"
            r"første målscorer|first goalscorer|last goalscorer",
            re.I,
        ),
    ),
    (
        TIER_3,
        re.compile(
            r"hjørne|corner|kort|card|booking|rødt|"
            r"1\.\s*omgang|2\.\s*omgang|1st half|2nd half|first half|second half|"
            r"pause/fulltid|ht/ft|halftime|"
            r"oddetall|partall|odd/even|"
            r"lag med flest",
            re.I,
        ),
    ),
    (
        TIER_1,
        re.compile(
            r"^vinner|to win|uavgjort|draw|"
            r"btts|begge lag scorer|"
            r"over/under|totalt antall mål|"
            r"handikap|handicap|asian|"
            r"tilbakebetales|draw no bet|dnb|"
            r"dobbel sjanse|double chance|"
            r"totalt antall \w+ mål|team total|"
            r"holder nullen|clean sheet|"
            r"1\.\s*mål\b|first goal team|lag til å score",
            re.I,
        ),
    ),
]

_FAMILY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ml", re.compile(r"^vinner|to win|vinner \(inkludert", re.I)),
    ("draw", re.compile(r"^uavgjort", re.I)),
    ("btts", re.compile(r"btts|begge lag scorer(?! og)", re.I)),
    ("ou_goals", re.compile(r"totalt antall mål|over/under \d|mål - over/under", re.I)),
    ("team_total", re.compile(r"totalt antall \w+ mål|team total", re.I)),
    ("handicap", re.compile(r"handikap|handicap", re.I)),
    ("dnb", re.compile(r"tilbakebetales|draw no bet|\bdnb\b", re.I)),
    ("dc", re.compile(r"dobbel sjanse|double chance", re.I)),
    ("first_goal_team", re.compile(r"lag til å score 1\.|first team to score", re.I)),
    ("clean_sheet", re.compile(r"holder nullen|clean sheet", re.I)),
    ("period_ml", re.compile(r"1\.\s*omgang\s*-\s*hub|1\.\s*omgang.*hub|1st half result", re.I)),
    ("period_ou", re.compile(r"1\.\s*omgang.*over/under|2\.\s*omgang.*over/under|1st half.*over", re.I)),
    ("corners", re.compile(r"hjørne|corner", re.I)),
    ("cards", re.compile(r"kort|card|booking|rødt", re.I)),
    ("goalscorer", re.compile(r"målscorer|anytime|to score|scorer\b", re.I)),
    ("player_stat", re.compile(r"180s|checkout|assists?|shots?", re.I)),
    ("special", re.compile(r".+", re.I)),  # fallback
]

# High-volume threshold: auto-run coverage scan when lines per match ≥ this
DEFAULT_HIGH_VOLUME_THRESHOLD = 40


@dataclass
class MarketLine:
    selection: str
    market_type: str
    decimal_odds: float
    tier: str
    family: str
    odds_band: str
    implied_prob: float
    flag: str  # interesting | review | skip | noise
    reason: str
    rough_ev_hint: float | None = None  # vs mid-market heuristic, not research p_model
    notes: list[str] = field(default_factory=list)


@dataclass
class MarketScanSummary:
    match: str
    sport: str
    kickoff: str | None
    competition: str | None
    scanned_at: str
    total_lines: int
    total_markets_approx: int
    high_volume: bool
    coverage_confidence: float  # 0–1
    coverage_confidence_pct: int
    coverage_note: str
    needs_manual_review: bool
    manual_review_tiers: list[str]
    tier_counts: dict[str, int]
    family_counts: dict[str, int]
    interesting: list[dict[str, Any]]
    review: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    noise: list[dict[str, Any]]
    tier_detail: dict[str, dict[str, Any]]
    recommended_deep_research: list[dict[str, Any]]
    full_board_covered: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assign_tier(selection: str, market_type: str = "") -> str:
    blob = f"{selection} {market_type}".strip()
    for tier, pat in _TIER_RULES:
        if pat.search(blob):
            return tier
    return TIER_4


def assign_family(selection: str, market_type: str = "") -> str:
    blob = f"{selection} {market_type}".strip()
    for name, pat in _FAMILY_PATTERNS:
        if pat.search(blob):
            return name
    return "other"


def _is_noise(selection: str, odds: float) -> bool:
    sel = selection.lower()
    if odds >= 50:
        return True
    if re.search(r"100 sekund|minst 3 mål|scorer før det er spilt 15", sel):
        return True
    if odds >= 25 and ("&" in selection or " og " in sel):
        return True
    if re.search(r"korrekt resultat|score \d+-\d+", sel):
        return True
    return False


def _flag_line(
    selection: str,
    odds: float,
    tier: str,
    family: str,
    *,
    sport: str = "",
) -> tuple[str, str, float | None, list[str]]:
    """
    Return (flag, reason, rough_ev_hint, notes).

    rough_ev_hint is a soft signal only: deviation of price from a "fair band"
    for that family — NOT a researched p_model.
    """
    notes: list[str] = []
    if _is_noise(selection, odds):
        return "noise", "Exotic / extreme longshot or correct-score style", None, notes

    # Too short for EV room after haircut (~need p very high)
    if odds < 1.28:
        return "skip", "Odds too short for EV after haircut (need near-certainty)", None, notes

    # High odds need grade A later
    if odds > 4.5 and tier in (TIER_2, TIER_4):
        notes.append("High odds — needs grade A evidence if researched")

    # Soft "interesting" heuristics by tier
    if tier == TIER_1:
        if 1.45 <= odds <= 2.40:
            # Mid-board sweet spot
            return "interesting", "Tier-1 mid-band — priority research slot", 0.02, notes
        if family in ("ou_goals", "btts", "handicap", "ml", "team_total") and 1.35 <= odds <= 3.0:
            return "interesting", f"Core family {family} with tradeable price", 0.01, notes
        if odds > 3.0:
            return "review", "Longer main-board price — check if soft vs market", None, notes
        return "review", "Main board — always review in deep research", None, notes

    if tier == TIER_2:
        # Goalscorer / props: flag mid-range anytime-ish prices
        if 2.5 <= odds <= 8.0 and family in ("goalscorer", "player_stat"):
            return (
                "interesting",
                "Player prop in researchable band — do not ignore vs main board",
                None,
                notes,
            )
        if 1.6 <= odds <= 2.5 and family == "player_stat":
            return "interesting", "Player stat prop mid-band", None, notes
        if odds > 12:
            return "skip", "Prop too long without elite research (grade A)", None, notes
        return "review", "Prop market — scan for standout names/prices", None, notes

    if tier == TIER_3:
        if family in ("corners", "cards", "period_ou") and 1.50 <= odds <= 2.50:
            return (
                "interesting",
                f"{family} mid-band — often under-researched vs O2.5",
                0.015,
                notes,
            )
        if family in ("corners", "cards", "period_ou", "period_ml"):
            return "review", f"{family} — include in coverage pass", None, notes
        return "review", "Alt market — quick scan", None, notes

    # Tier 4 specials
    if odds <= 3.5 and ("&" in selection or " og " in selection.lower()):
        return "review", "SGP/special with moderate odds — only if legs researched", None, notes
    return "skip", "Special/SGP — skip unless manual high-conviction", None, notes


def classify_line(c: Candidate) -> MarketLine:
    tier = assign_tier(c.selection, c.market_type or "")
    family = assign_family(c.selection, c.market_type or "")
    odds = float(c.decimal_odds)
    flag, reason, hint, notes = _flag_line(
        c.selection, odds, tier, family, sport=c.sport or ""
    )
    return MarketLine(
        selection=c.selection,
        market_type=c.market_type or "",
        decimal_odds=odds,
        tier=tier,
        family=family,
        odds_band=odds_band(odds),
        implied_prob=round(1.0 / odds, 4) if odds > 1 else 0.0,
        flag=flag,
        reason=reason,
        rough_ev_hint=hint,
        notes=notes,
    )


def _approx_market_count(lines: list[MarketLine]) -> int:
    """Group outcomes into markets by market_type + selection prefix heuristics."""
    keys: set[str] = set()
    for ln in lines:
        mt = (ln.market_type or "").strip()
        if mt:
            keys.add(mt.lower())
            continue
        # Derive from selection: strip side (over/under, ja/nei, team names hard)
        sel = ln.selection
        base = re.sub(
            r":\s*.+$|over\s*[\d.]+|under\s*[\d.]+|\bja\b|\bnei\b",
            "",
            sel,
            flags=re.I,
        ).strip()
        keys.add((base or sel)[:60].lower())
    return max(len(keys), 1)


def compute_coverage_confidence(
    lines: list[MarketLine],
    *,
    high_volume: bool,
) -> tuple[float, str, list[str]]:
    """
    Confidence that we have *categorized and flagged* the board adequately
    (not that every line was deep-researched).
    """
    if not lines:
        return 0.0, "No lines found for match", [TIER_1]

    n = len(lines)
    by_tier: dict[str, list[MarketLine]] = defaultdict(list)
    for ln in lines:
        by_tier[ln.tier].append(ln)

    # Base: all lines classified into a tier
    conf = 0.55
    notes: list[str] = []
    manual: list[str] = []

    # Tier 1 presence
    t1 = by_tier.get(TIER_1) or []
    if t1:
        conf += 0.15
        interesting_t1 = sum(1 for x in t1 if x.flag in ("interesting", "review"))
        if interesting_t1 >= 4:
            conf += 0.05
    else:
        conf -= 0.15
        notes.append("No Tier-1 main board lines detected")
        manual.append(TIER_1)

    # Tier 2: if high volume football and few props flagged → lower confidence
    t2 = by_tier.get(TIER_2) or []
    if high_volume:
        if len(t2) >= 8:
            conf += 0.08
            if sum(1 for x in t2 if x.flag == "interesting") == 0:
                conf -= 0.05
                notes.append("Many props present but none flagged interesting — manual prop scan recommended")
                manual.append(TIER_2)
        elif len(t2) == 0:
            conf -= 0.05
            notes.append("High-volume match with zero player props parsed")
            manual.append(TIER_2)
        else:
            conf += 0.03

    # Tier 3
    t3 = by_tier.get(TIER_3) or []
    if high_volume:
        if len(t3) >= 6:
            conf += 0.07
        else:
            conf -= 0.04
            notes.append("Sparse corners/cards/halves vs expected high-volume board")
            manual.append(TIER_3)
    elif t3:
        conf += 0.03

    # Tier 4 acknowledged (skipped is OK if we catalogued them)
    t4 = by_tier.get(TIER_4) or []
    if t4:
        conf += 0.04
        notes.append(f"Catalogued {len(t4)} specials (mostly skip unless manual)")
    if high_volume and len(t4) > 30:
        conf -= 0.03
        notes.append("Very large specials block — coverage is catalog-only, not deep research")
        if TIER_4 not in manual:
            manual.append(TIER_4)

    # Interesting flags across non-T1
    alt_interesting = sum(
        1
        for ln in lines
        if ln.tier != TIER_1 and ln.flag == "interesting"
    )
    if high_volume and alt_interesting == 0:
        conf -= 0.08
        notes.append("No Tier 2/3 lines flagged interesting — risk of main-board tunnel vision")
        for t in (TIER_2, TIER_3):
            if t not in manual:
                manual.append(t)
    elif alt_interesting >= 2:
        conf += 0.06

    conf = max(0.0, min(0.98, conf))
    if conf >= 0.85:
        coverage_note = "High — board categorized; deep research can focus on flagged lines"
    elif conf >= 0.70:
        coverage_note = "Moderate — review flagged tiers before locking recommendations"
    else:
        coverage_note = "Low — manual market scan recommended before betting"
        if not manual:
            manual = [TIER_1, TIER_2]

    if notes:
        coverage_note = coverage_note + " | " + "; ".join(notes[:3])

    return conf, coverage_note, manual


def scan_match_candidates(
    candidates: list[Candidate],
    *,
    match: str | None = None,
    high_volume_threshold: int = DEFAULT_HIGH_VOLUME_THRESHOLD,
) -> MarketScanSummary:
    """Scan all candidates for one match (or first match if match is None)."""
    if not candidates:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return MarketScanSummary(
            match=match or "",
            sport="",
            kickoff=None,
            competition=None,
            scanned_at=now,
            total_lines=0,
            total_markets_approx=0,
            high_volume=False,
            coverage_confidence=0.0,
            coverage_confidence_pct=0,
            coverage_note="No candidates",
            needs_manual_review=True,
            manual_review_tiers=[TIER_1],
            tier_counts={},
            family_counts={},
            interesting=[],
            review=[],
            skipped=[],
            noise=[],
            tier_detail={},
            recommended_deep_research=[],
            full_board_covered=False,
        )

    # Resolve match key
    if match:
        match_l = match.lower()
        pool = [
            c
            for c in candidates
            if match_l in (c.match or "").lower()
            or (c.match or "").lower() in match_l
        ]
        if not pool:
            # fuzzy: tokens
            tokens = [t for t in re.split(r"\s+", match_l) if len(t) > 2]
            pool = [
                c
                for c in candidates
                if all(t in (c.match or "").lower() for t in tokens[:2])
            ]
        # Prefer the most common full match name in the pool
        if pool:
            counts: dict[str, int] = defaultdict(int)
            for c in pool:
                counts[c.match or "unknown"] += 1
            match = max(counts.keys(), key=lambda k: counts[k])
            pool = [c for c in pool if (c.match or "unknown") == match]
    else:
        # largest match by line count
        by_m: dict[str, list[Candidate]] = defaultdict(list)
        for c in candidates:
            by_m[c.match or "unknown"].append(c)
        match_key = max(by_m.keys(), key=lambda k: len(by_m[k]))
        pool = by_m[match_key]
        match = match_key

    lines = [classify_line(c) for c in pool]
    sport = (pool[0].sport if pool else "") or ""
    high_volume = len(lines) >= high_volume_threshold
    conf, coverage_note, manual = compute_coverage_confidence(
        lines, high_volume=high_volume
    )

    tier_counts: dict[str, int] = defaultdict(int)
    family_counts: dict[str, int] = defaultdict(int)
    buckets: dict[str, list[MarketLine]] = defaultdict(list)
    for ln in lines:
        tier_counts[ln.tier] += 1
        family_counts[ln.family] += 1
        buckets[ln.flag].append(ln)

    def _ser(lst: list[MarketLine], limit: int = 40) -> list[dict[str, Any]]:
        out = []
        for ln in sorted(lst, key=lambda x: (-(x.rough_ev_hint or 0), x.decimal_odds))[
            :limit
        ]:
            out.append(
                {
                    "selection": ln.selection,
                    "odds": ln.decimal_odds,
                    "tier": ln.tier,
                    "family": ln.family,
                    "band": ln.odds_band,
                    "implied": ln.implied_prob,
                    "reason": ln.reason,
                    "rough_ev_hint": ln.rough_ev_hint,
                    "notes": ln.notes,
                }
            )
        return out

    tier_detail: dict[str, dict[str, Any]] = {}
    for tier in (TIER_1, TIER_2, TIER_3, TIER_4):
        tlines = [ln for ln in lines if ln.tier == tier]
        tier_detail[tier] = {
            "label": TIER_LABELS.get(tier, tier),
            "n": len(tlines),
            "interesting": sum(1 for x in tlines if x.flag == "interesting"),
            "review": sum(1 for x in tlines if x.flag == "review"),
            "skip": sum(1 for x in tlines if x.flag == "skip"),
            "noise": sum(1 for x in tlines if x.flag == "noise"),
            "top_interesting": _ser(
                [x for x in tlines if x.flag == "interesting"], limit=8
            ),
            "sample_review": _ser([x for x in tlines if x.flag == "review"], limit=5),
        }

    # Recommended deep research: all interesting T1 + interesting T2/T3 + top review T1
    deep: list[MarketLine] = []
    deep.extend([ln for ln in lines if ln.flag == "interesting"])
    # Ensure core T1 families present
    have_families = {ln.family for ln in deep}
    for fam in ("ml", "ou_goals", "btts", "handicap"):
        if fam not in have_families:
            cand = [
                ln
                for ln in lines
                if ln.family == fam and ln.flag in ("review", "interesting")
            ]
            if cand:
                deep.append(sorted(cand, key=lambda x: x.decimal_odds)[0])
    # Dedup by selection
    seen: set[str] = set()
    deep_ser: list[dict[str, Any]] = []
    for ln in deep:
        if ln.selection in seen:
            continue
        seen.add(ln.selection)
        deep_ser.append(
            {
                "selection": ln.selection,
                "odds": ln.decimal_odds,
                "tier": ln.tier,
                "family": ln.family,
                "flag": ln.flag,
                "reason": ln.reason,
            }
        )
        if len(deep_ser) >= 20:
            break

    full_covered = (
        conf >= 0.75
        and (not high_volume or (tier_counts.get(TIER_2, 0) + tier_counts.get(TIER_3, 0)) > 0)
        and len([x for x in lines if x.flag == "interesting"]) >= 1
    )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return MarketScanSummary(
        match=match or "",
        sport=sport,
        kickoff=None,
        competition=None,
        scanned_at=now,
        total_lines=len(lines),
        total_markets_approx=_approx_market_count(lines),
        high_volume=high_volume,
        coverage_confidence=round(conf, 3),
        coverage_confidence_pct=int(round(conf * 100)),
        coverage_note=coverage_note,
        needs_manual_review=conf < 0.75 or bool(manual),
        manual_review_tiers=manual,
        tier_counts=dict(tier_counts),
        family_counts=dict(sorted(family_counts.items(), key=lambda kv: -kv[1])),
        interesting=_ser(buckets.get("interesting") or [], limit=25),
        review=_ser(buckets.get("review") or [], limit=30),
        skipped=_ser(buckets.get("skip") or [], limit=20),
        noise=_ser(buckets.get("noise") or [], limit=15),
        tier_detail=tier_detail,
        recommended_deep_research=deep_ser,
        full_board_covered=full_covered,
    )


def scan_odds_file(
    odds_path: Path,
    *,
    match: str | None = None,
    high_volume_threshold: int = DEFAULT_HIGH_VOLUME_THRESHOLD,
    top_n_matches: int = 5,
) -> dict[str, Any]:
    """
    Scan one match or the top high-volume matches in an odds file.
    """
    candidates = parse_odds_file(odds_path)
    by_m: dict[str, list[Candidate]] = defaultdict(list)
    for c in candidates:
        by_m[c.match or "unknown"].append(c)

    ranked = sorted(by_m.items(), key=lambda kv: len(kv[1]), reverse=True)

    if match:
        summary = scan_match_candidates(
            candidates, match=match, high_volume_threshold=high_volume_threshold
        )
        return {
            "odds_file": str(odds_path),
            "mode": "single_match",
            "n_matches_in_file": len(by_m),
            "scan": summary.to_dict(),
        }

    # Auto: scan high-volume matches (or top by line count)
    scans: list[dict[str, Any]] = []
    high_vol = [(m, cs) for m, cs in ranked if len(cs) >= high_volume_threshold]
    targets = high_vol[:top_n_matches] if high_vol else ranked[: min(3, top_n_matches)]
    for m, cs in targets:
        s = scan_match_candidates(
            cs, match=m, high_volume_threshold=high_volume_threshold
        )
        scans.append(s.to_dict())

    return {
        "odds_file": str(odds_path),
        "mode": "auto_high_volume" if high_vol else "auto_top_matches",
        "n_matches_in_file": len(by_m),
        "high_volume_threshold": high_volume_threshold,
        "n_high_volume_matches": len(high_vol),
        "top_matches_by_lines": [
            {"match": m, "n_lines": len(cs)} for m, cs in ranked[:15]
        ],
        "scans": scans,
    }


def render_scan_markdown(scan: dict[str, Any]) -> str:
    """Render one MarketScanSummary dict as markdown."""
    lines = [
        f"# Market Scan Summary — {scan.get('match') or '—'}",
        "",
        f"**Scanned:** {scan.get('scanned_at')} · **Sport:** {scan.get('sport') or '—'}",
        f"**Lines:** **{scan.get('total_lines')}** · approx markets **{scan.get('total_markets_approx')}**",
        f"**High-volume board:** {'Yes' if scan.get('high_volume') else 'No'}",
        "",
        f"## Coverage confidence: **{scan.get('coverage_confidence_pct')}%**",
        "",
        f"{scan.get('coverage_note')}",
        "",
        f"**Full board covered (catalog):** {'Yes' if scan.get('full_board_covered') else 'No — see flags'}",
    ]
    if scan.get("needs_manual_review"):
        lines.append(
            f"**⚠ Manual review suggested for:** "
            + ", ".join(scan.get("manual_review_tiers") or [])
        )
    lines.extend(["", "## Tier breakdown", ""])
    lines.append("| Tier | n | Interesting | Review | Skip | Noise |")
    lines.append("|------|---|-------------|--------|------|-------|")
    td = scan.get("tier_detail") or {}
    for tier in (TIER_1, TIER_2, TIER_3, TIER_4):
        d = td.get(tier) or {}
        label = (d.get("label") or tier).split("—")[0].strip()
        lines.append(
            f"| {label} | {d.get('n', 0)} | {d.get('interesting', 0)} | "
            f"{d.get('review', 0)} | {d.get('skip', 0)} | {d.get('noise', 0)} |"
        )

    lines.extend(["", "## Flagged interesting (priority research)", ""])
    interesting = scan.get("interesting") or []
    if not interesting:
        lines.append("_None auto-flagged — check Tier 2/3 review samples._")
    for it in interesting[:15]:
        lines.append(
            f"- **{it.get('selection')}** @ {it.get('odds')} "
            f"[{it.get('tier')}/{it.get('family')}] — {it.get('reason')}"
        )

    lines.extend(["", "## Recommended deep-research queue", ""])
    for it in (scan.get("recommended_deep_research") or [])[:12]:
        lines.append(
            f"- `{it.get('selection')}` @ {it.get('odds')} "
            f"({it.get('tier')}, {it.get('flag')})"
        )

    lines.extend(["", "## Sample skipped / noise", ""])
    for it in (scan.get("skipped") or [])[:8]:
        lines.append(f"- skip: {it.get('selection')} @ {it.get('odds')} — {it.get('reason')}")
    for it in (scan.get("noise") or [])[:5]:
        lines.append(f"- noise: {it.get('selection')} @ {it.get('odds')} — {it.get('reason')}")

    lines.extend(
        [
            "",
            "---",
            "_Market Coverage Agent: catalog + flag only. Deep research still required "
            "for honest p_model before recommend._",
            "",
        ]
    )
    return "\n".join(lines)


def write_scan_reports(
    cfg: dict[str, Any],
    payload: dict[str, Any],
    *,
    out_dir: Path | None = None,
) -> list[str]:
    """Write JSON + MD for each scan into outbox/market_scans/."""
    if out_dir is None:
        try:
            outbox = path_from_config(cfg, "outbox")
        except Exception:
            outbox = Path("outbox")
        out_dir = outbox / "market_scans"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    scans = payload.get("scans")
    if payload.get("scan"):
        scans = [payload["scan"]]
    if not scans:
        # write index only
        idx = out_dir / "INDEX.json"
        idx.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(str(idx))
        return written

    for scan in scans:
        safe = re.sub(r"[^a-z0-9]+", "_", (scan.get("match") or "match").lower()).strip("_")[
            :50
        ]
        stamp = (scan.get("scanned_at") or "")[:10].replace("-", "")
        base = f"{safe}_{stamp}" if stamp else safe
        jpath = out_dir / f"{base}.json"
        mpath = out_dir / f"{base}.md"
        jpath.write_text(json.dumps(scan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        mpath.write_text(render_scan_markdown(scan), encoding="utf-8")
        written.extend([str(jpath), str(mpath)])

    idx = out_dir / "INDEX.json"
    idx.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    written.append(str(idx))
    return written


def run_market_coverage(
    cfg: dict[str, Any],
    odds_path: Path,
    *,
    match: str | None = None,
    write: bool = True,
    high_volume_threshold: int = DEFAULT_HIGH_VOLUME_THRESHOLD,
    top_n_matches: int = 5,
) -> dict[str, Any]:
    payload = scan_odds_file(
        odds_path,
        match=match,
        high_volume_threshold=high_volume_threshold,
        top_n_matches=top_n_matches,
    )
    if write:
        paths = write_scan_reports(cfg, payload)
        payload["written"] = paths
    return payload
