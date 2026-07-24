"""Pure score_evidence against Sport Research Cards."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from nt.evidence import has_core_reason, normalize_sources
from nt.evidence_hierarchy.cards import (
    SportCard,
    default_quarantine_card,
    load_sport_card,
)
from nt.evidence_hierarchy.h2h_normalize import normalize_h2h, normalize_strength
from nt.evidence_hierarchy.normalize import normalize_sport_for_research
from nt.evidence_hierarchy.types import EvidenceScorecard, SignalSlot


def evidence_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    sel = dict((cfg or {}).get("selection") or {})
    raw = dict(sel.get("evidence") or {})
    fh = dict(raw.get("forced_hierarchy") or {})
    return {
        "enabled": bool(raw.get("enabled", False)),
        # PR1 default: shadow — legacy place path still active
        "shadow_mode": bool(raw.get("shadow_mode", True)),
        "auto_onboard_cards": bool(raw.get("auto_onboard_cards", True)),
        "strict_band_cd": bool(raw.get("strict_band_cd", True)),
        "min_takeaway_chars": int(raw.get("min_takeaway_chars") or 24),
        "infer_min_confidence": float(raw.get("infer_min_confidence") or 0.65),
        "min_quality_sources_floor": int(raw.get("min_quality_sources_floor") or 3),
        "min_quality_sources_b": int(raw.get("min_quality_sources_b") or 4),
        "min_quality_sources_a": int(raw.get("min_quality_sources_a") or 6),
        "min_E_grade_b": float(raw.get("min_E_grade_b") or 0.55),
        "min_E_grade_a": float(raw.get("min_E_grade_a") or 0.72),
        "min_E_grade_c": float(raw.get("min_E_grade_c") or 0.30),
        "onboarded_override": list(raw.get("onboarded") or []),
        "quarantine_unknown": bool(raw.get("quarantine_unknown", True)),
        "allow_quarantine_place": bool(raw.get("allow_quarantine_place", False)),
        "card_schema_version": int(raw.get("card_schema_version") or 1),
        # FEH place ownership — PR1 keeps disabled (shadow audit only)
        "forced_hierarchy_enabled": bool(fh.get("enabled", False)),
    }


def compute_saef(cfg: dict[str, Any] | None) -> bool:
    ec = evidence_cfg(cfg)
    return bool(ec["enabled"] or ec["shadow_mode"])


def place_uses_saef(cfg: dict[str, Any] | None) -> bool:
    """
    True only when SAEF / FEH owns place grade.

    Fail-safe triple gate (PR1):
      selection.evidence.enabled
      AND not shadow_mode
      AND forced_hierarchy.enabled

    Flipping shadow_mode alone must NOT hand place ownership to SAEF without
    the FEH place stack (anti-soft, checklist, …) that ships in PR2.
    """
    ec = evidence_cfg(cfg)
    return bool(
        ec["enabled"]
        and not ec["shadow_mode"]
        and ec["forced_hierarchy_enabled"]
    )


def is_quality_source(s: dict[str, Any], *, min_chars: int = 24) -> bool:
    if not (s.get("url") or s.get("name")):
        return False
    take = str(s.get("takeaway") or s.get("note") or s.get("summary") or "").strip()
    return len(take) >= min_chars


def source_domain(s: dict[str, Any]) -> str:
    url = str(s.get("url") or "")
    if not url:
        return str(s.get("name") or "").lower()[:40]
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def quality_source_count(sources: list[dict[str, Any]], *, min_chars: int = 24) -> int:
    return sum(1 for s in sources if is_quality_source(s, min_chars=min_chars))


def distinct_quality_domains(sources: list[dict[str, Any]], *, min_chars: int = 24) -> int:
    doms = {source_domain(s) for s in sources if is_quality_source(s, min_chars=min_chars) and source_domain(s)}
    return len(doms)


def _family(selection: str) -> str:
    s = (selection or "").lower()
    if re.search(r"btts|begge lag|both teams", s):
        if re.search(r"nei|no\b", s):
            return "btts_no"
        return "btts_yes"
    if re.search(r"over\s*\d|over\b", s) and re.search(r"total|mål|mal|kart|runder|games?", s):
        return "totals_over"
    if re.search(r"under\s*\d|under\b", s) and re.search(r"total|mål|mal|kart|runder|games?", s):
        return "totals_under"
    if re.search(r"handikap|handicap|\+\d|\-\d", s):
        return "handicap"
    if re.search(r"prop|scorer|points|assist", s):
        return "prop"
    if re.search(r"vinner|to win|winner|ml\b|moneyline", s):
        return "ml"
    return "other"


def _is_underdog_hc(selection: str, odds: float) -> bool:
    s = selection or ""
    if re.search(r"\+\s*\d|\+\d", s):
        return True
    if re.search(r"handikap|handicap", s, re.I) and float(odds) >= 1.85:
        return True
    return False


def _mid_band(odds: float) -> bool:
    return 1.85 <= float(odds) <= 2.60


def _token_matches(tok: str, *, family: str, underdog: bool, avail_sens: bool, high_ctx: bool, standin: bool, schedule_load: bool) -> bool:
    if tok == "*":
        return True
    if tok == family:
        return True
    # aliases
    if tok == "totals" and family in ("totals_over", "totals_under"):
        return True
    if tok == "btts" and family in ("btts_yes", "btts_no"):
        return True
    if tok == "prop*" and family.startswith("prop"):
        return True
    if tok == "underdog_hc":
        return underdog
    if tok == "avail_sensitive":
        return avail_sens
    if tok == "high_context":
        return high_ctx
    if tok == "standin":
        return standin
    if tok == "schedule_load":
        return schedule_load
    return False


def _avail_sensitive(family: str) -> bool:
    return family in (
        "totals_over",
        "totals_under",
        "btts_yes",
        "btts_no",
        "prop",
        "prop_over",
        "prop_under",
    )


def _blob(ev: dict[str, Any]) -> str:
    parts = [
        str(ev.get("summary") or ""),
        str(ev.get("failure_modes") or ""),
        str(ev.get("h2h") or ""),
        str(ev.get("form") or ""),
        str(ev.get("matchup_notes") or ""),
    ]
    for s in normalize_sources(ev.get("sources")):
        parts.append(str(s.get("takeaway") or ""))
        parts.append(str(s.get("name") or ""))
    return " ".join(parts).lower()


def _h2h_info(ev: dict[str, Any]) -> dict[str, Any]:
    """H2H flags via shared normalize_h2h (mixed string ≠ positive/negative)."""
    norm = normalize_h2h(ev)
    info = norm.to_dict()
    # Blob-only checked fallback (when pack has no h2h block but prose mentions it)
    if not info["checked"]:
        text = _blob(ev)
        if re.search(r"\bh2h\b|head[\s-]?to[\s-]?head|matchup|innbyrdes", text):
            info["checked"] = True
            if info["polarity"] == "unchecked":
                info["polarity"] = "unknown"
        if re.search(
            r"never beaten|negative h2h|0[–\-]?\d in h2h|winless vs|lost all", text
        ):
            info["negative"] = True
            info["positive"] = False
            info["mixed"] = False
            info["polarity"] = "negative"
            info["checked"] = True
        if re.search(r"positive h2h|h2h\s*(edge|pos|\+)|leads?\s+h2h|won\s+\d", text):
            if not info["negative"]:
                info["positive"] = True
                info["mixed"] = False
                info["polarity"] = "positive"
                info["checked"] = True
    return info


def _slot_fill(
    slot: SignalSlot,
    ev: dict[str, Any],
    *,
    underdog: bool,
    h2h: dict[str, Any],
    min_chars: int,
    infer_min: float,
    card: SportCard | None = None,
) -> float:
    signals = ev.get("signals") if isinstance(ev.get("signals"), dict) else {}
    if card is not None:
        sig = card.lookup_signal(signals, slot.id)
    else:
        sig = signals.get(slot.id) if isinstance(signals, dict) else None
    if isinstance(sig, dict) and sig.get("filled"):
        note = str(sig.get("note") or sig.get("takeaway") or "")
        note_len = len(note.strip())
        raw = sig.get("strength")
        num, pol = normalize_strength(raw)
        if num is not None:
            s_val = float(num)
        elif raw is None:
            s_val = 0.7
        else:
            # unknown string strength — weak fill, not positive boost
            s_val = 0.5
        # mixed → abs 0 still allows floor fill via max(0.35, ...)
        if pol == "mixed":
            s_abs = 0.45
        else:
            s_abs = max(0.0, min(1.0, abs(s_val)))
        if s_val < 0 and not slot.allows_negative_strength:
            s_abs = min(s_abs, 0.35)
        if slot.individual_h2h or "h2h" in slot.id:
            edge = h2h.get("edge")
            edge_neg = False
            try:
                if edge is not None:
                    edge_neg = float(edge) < 0
            except (TypeError, ValueError):
                edge_neg = False
            if underdog and (h2h.get("negative") or s_val < 0 or edge_neg):
                return 0.0
        if note_len < min_chars and note_len < slot.min_takeaway_chars:
            # allow structured strength with short note if summary long enough
            if len(str(ev.get("summary") or "")) < 20:
                return 0.0
            note_len = max(note_len, 24)
        len_factor = min(1.0, note_len / 40.0)
        return max(0.35, min(1.0, len_factor * max(s_abs, 0.35)))

    # Structured H2H dict for h2h slots
    if "h2h" in slot.id or slot.individual_h2h:
        if h2h.get("checked"):
            if underdog and h2h.get("negative"):
                return 0.0
            if h2h.get("positive"):
                return 0.7
            if h2h.get("mixed"):
                return 0.45  # filled but not positive
            if h2h.get("edge") is not None:
                return 0.55
            if len(str(h2h.get("summary") or "")) >= min_chars:
                return 0.5
            return 0.4

    # Infer from pack blob (migration) — capped low
    text = _blob(ev)
    patterns = {
        "h2h_matchup": r"\bh2h\b|head[\s-]?to[\s-]?head|matchup",
        "surface_h2h": r"surface|clay|hard|grass|h2h",
        "xg_form": r"\bxg\b|expected goals|form\b",
        "recent_form": r"\bform\b|last\s+\d|recent results",
        "availability": r"injur|lineup|availability|fitness|suspension",
        "fitness_fatigue": r"fatigue|retirement|fitness|injury",
        "ranking_form": r"ranking|seed|elo|world\s*no",
        "ranking_strength": r"ranking|seed|elo|rating",
        "ranking_seed": r"ranking|seed|elo|rating",
        "serve_return": r"serve|return|break point",
        "pitcher_matchup": r"pitcher|era\b|whip|starter",
        "pace_efficiency": r"pace|net rating|offensive rating",
        "map_pool": r"\bmap\b|veto|pool",
        "roster_standin": r"stand-?in|roster|lineup",
        "venue_split": r"home|away|venue",
        "motivation": r"motivation|must[\s-]?win|relegation|title",
        "motivation_context": r"motivation|tournament|stage",
        "script_consistency": r"script|high_scoring|low_scoring",
        "avg_checkout": r"average|checkout|3-dart",
        "checkout_scoring": r"average|checkout|3-dart|scoring",
        "frame_form": r"frame|century|break",
        "rest_schedule": r"b2b|back-to-back|rest|travel",
        "bullpen": r"bullpen|reliever",
        "park_factors": r"park|ballpark",
        "format_stage": r"format|stage|bo\d|legs",
    }
    pat = patterns.get(slot.id)
    if pat and re.search(pat, text):
        # crude confidence
        conf = 0.7 if len(text) > 80 else 0.5
        if conf < infer_min:
            return 0.0
        return 0.35 * conf
    return 0.0


def score_evidence(
    ev: dict[str, Any] | None,
    *,
    sport: str = "",
    selection: str = "",
    odds: float = 2.0,
    cfg: dict[str, Any] | None = None,
    card: SportCard | None = None,
) -> EvidenceScorecard:
    """
    Pure scorecard relative to the pack: never mutates pack fields.

    Does **not** write sport-card YAML to disk. Missing cards use an in-memory
    quarantine template (or the committed default card). Explicit disk onboard
    stays on scaffold / ensure_sport_card / migrate tools.
    """
    ec = evidence_cfg(cfg)
    min_chars = int(ec["min_takeaway_chars"])
    sport_key = normalize_sport_for_research(sport or (ev or {}).get("sport") or "")
    if card is None:
        card = load_sport_card(sport_key, cfg)
        if card is None and ec.get("auto_onboard_cards", True):
            # In-memory quarantine only — grade/recommend must not write cards
            card = default_quarantine_card(sport_key)
        if card is None:
            card = load_sport_card("default", cfg)

    if card is None:
        return EvidenceScorecard(
            sport=sport_key,
            card_id="missing",
            onboarded=False,
            E=0.0,
            r=0.0,
            quality_source_count=0,
            distinct_quality_domains=0,
            grade_suggestion="F",
            hard_rejects=["HR_SPORT_UNKNOWN"],
            soft_notes=["no sport card"],
            confidence="Low",
        )

    # Onboarded override list
    onboarded = bool(card.onboarded)
    if sport_key in (ec.get("onboarded_override") or []):
        onboarded = True

    sources = normalize_sources((ev or {}).get("sources"))
    q_count = quality_source_count(sources, min_chars=min_chars)
    q_dom = distinct_quality_domains(sources, min_chars=min_chars)

    family = _family(selection or str((ev or {}).get("selection") or ""))
    underdog = _is_underdog_hc(selection or str((ev or {}).get("selection") or ""), float(odds or 2.0))
    high_ctx = str((ev or {}).get("context_risk") or "").lower() == "high"
    avail_sens = _avail_sensitive(family)
    blob = _blob(ev or {})
    standin = bool(re.search(r"stand-?in|roster change", blob))
    schedule_load = bool(re.search(r"\bb2b\b|back-to-back|3-in-4|load management", blob))
    h2h = _h2h_info(ev or {})
    mid = _mid_band(float(odds or 2.0))

    hard: list[str] = []
    soft: list[str] = []

    if not onboarded and ec.get("quarantine_unknown", True):
        hard.append("HR_SPORT_UNKNOWN")
        if not ec.get("allow_quarantine_place"):
            soft.append("sport card not onboarded — quarantine (no place mid-band)")

    if q_count < int(ec["min_quality_sources_floor"]):
        hard.append("HR_EMPTY_TAKEAWAYS")

    # Wrong-sport football pollution (non-football)
    if sport_key not in ("football", "default") and sources:
        football_doms = ("fbref.com", "transfermarkt.", "understat.com", "whoscored.com", "soccerstats")
        n_foot = sum(
            1
            for s in sources
            if any(d in (source_domain(s) + str(s.get("url") or "")).lower() for d in football_doms)
        )
        # quality sport-correct: quality source whose domain is not pure football for non-football sports
        n_sport_q = sum(
            1
            for s in sources
            if is_quality_source(s, min_chars=min_chars)
            and not any(d in source_domain(s) for d in ("fbref.com", "transfermarkt", "understat"))
        )
        if n_sport_q == 0 and n_foot >= max(1, len(sources) // 2):
            hard.append("HR_WRONG_SPORT_SOURCES")

    if underdog and h2h.get("negative"):
        hard.append("HR_NEG_H2H_UD")
    # Individual and team both require matchup check for underdog HC mid-band today;
    # keep single condition (team vs individual may diverge in PR2 FEH).
    if underdog and mid and not h2h.get("checked"):
        hard.append("HR_NO_MATCHUP_UD")

    if str((ev or {}).get("selection_vs_script") or "").lower() == "conflict":
        hard.append("HR_SCRIPT")
    if (ev or {}).get("base_rate_conflict") is True:
        hard.append("HR_BASE_RATE")

    slots = card.slots()
    fills: list[tuple[SignalSlot, float, bool, bool]] = []
    # applicable, required, f_i
    for slot in slots:
        m_i = 1 if ("*" in slot.markets or family in slot.markets or _market_alias_match(slot.markets, family)) else 0
        if not m_i:
            fills.append((slot, 0.0, False, False))
            continue
        req = False
        for tok in slot.require_when:
            if _token_matches(
                tok,
                family=family,
                underdog=underdog,
                avail_sens=avail_sens,
                high_ctx=high_ctx,
                standin=standin,
                schedule_load=schedule_load,
            ):
                req = True
                break
        f_i = _slot_fill(
            slot,
            ev or {},
            underdog=underdog,
            h2h=h2h,
            min_chars=min_chars,
            infer_min=float(ec["infer_min_confidence"]),
            card=card,
        )
        fills.append((slot, f_i, True, req))

    denom = sum(s.weight for s, f, app, r in fills if app)
    if denom <= 0:
        hard.append("HR_NO_APPLICABLE_SLOTS")
        E = 0.0
    else:
        E = sum(s.weight * f for s, f, app, r in fills if app) / denom
        E = max(0.0, min(1.0, E))

    required = [(s, f) for s, f, app, r in fills if app and r]
    missing = [s.id for s, f in required if f < 0.35]
    if required:
        r_cov = sum(1 for s, f in required if f >= 0.35) / len(required)
    else:
        r_cov = 1.0  # no required slots → coverage vacuous

    # Required groups
    for g in card.groups():
        apply = any(
            _token_matches(
                tok,
                family=family,
                underdog=underdog,
                avail_sens=avail_sens,
                high_ctx=high_ctx,
                standin=standin,
                schedule_load=schedule_load,
            )
            for tok in g.apply_when
        )
        if not apply:
            continue
        n_ok = 0
        for sid in g.slot_ids:
            for s, f, app, _r in fills:
                if s.id == sid and app and f >= 0.35:
                    n_ok += 1
        if n_ok < g.min_filled:
            missing.append(f"group:{g.id}")
            r_cov = min(r_cov, 0.0)

    if mid and ec.get("strict_band_cd") and missing and onboarded:
        hard.append("HR_MISSING_T1")

    filled_slots = [s.id for s, f, app, _r in fills if app and f >= 0.35]
    factors = []
    best_pos = ("", -1.0)
    best_neg = ("", 99.0)
    for s, f, app, req in fills:
        if not app:
            continue
        factors.append(
            {
                "id": s.id,
                "tier": s.tier,
                "weight": s.weight,
                "f": round(f, 3),
                "required": req,
                "filled": f >= 0.35,
            }
        )
        if f >= 0.35 and f * s.weight > best_pos[1]:
            best_pos = (s.id, f * s.weight)
        if req and f < 0.35:
            best_neg = (s.id + ":missing", f)

    if h2h.get("negative"):
        best_neg = ("h2h_negative", -1.0)
    if not best_pos[0] and filled_slots:
        best_pos = (filled_slots[0], 0.5)

    # Grade suggestion
    floors = card.grade_floors or {}
    b_floor = floors.get("B") or {}
    a_floor = floors.get("A") or {}
    c_floor = floors.get("C") or {}
    min_Eb = float(b_floor.get("min_E") or ec["min_E_grade_b"])
    min_Ea = float(a_floor.get("min_E") or ec["min_E_grade_a"])
    min_Ec = float(c_floor.get("min_E") or ec["min_E_grade_c"])
    min_qb = int(b_floor.get("min_quality_sources") or ec["min_quality_sources_b"])
    min_qa = int(a_floor.get("min_quality_sources") or ec["min_quality_sources_a"])
    min_qc = int(c_floor.get("min_quality_sources") or 3)

    grade = "B"
    if hard:
        grade = "F"
    elif not onboarded:
        grade = "C" if q_count >= min_qc and E >= min_Ec else "F"
    elif E < min_Ec or q_count < min_qc or not has_core_reason(ev):
        grade = "F" if q_count < ec["min_quality_sources_floor"] else "C"
    elif r_cov < 1.0 or E < min_Eb or q_count < min_qb or missing:
        grade = "C"
    else:
        # Grade B base
        grade = "B"
        # Grade A?
        unc = False
        try:
            from nt.evidence import _has_grade_a_uncertainty

            unc = _has_grade_a_uncertainty(ev or {}, sources)
        except Exception:
            unc = bool((ev or {}).get("p_model_sd"))
        dual = _dual_tier1(fills, sources, min_chars)
        if E >= min_Ea and q_count >= min_qa and unc and dual:
            grade = "A"

    if grade == "A":
        conf = "High"
    elif grade == "B":
        conf = "High" if E >= 0.72 else "Medium"
    elif grade == "C":
        conf = "Low"
    else:
        conf = "Low"

    p_rel = max(0.0, min(1.0, 0.5 * E + 0.3 * r_cov + 0.2 * min(1.0, q_count / 6.0)))

    primary_w = {
        s.id: s.weight for s, f, app, r in fills if app and s.tier == 1
    }

    return EvidenceScorecard(
        sport=sport_key,
        card_id=card.card_id,
        onboarded=onboarded,
        E=E,
        r=r_cov,
        quality_source_count=q_count,
        distinct_quality_domains=q_dom,
        grade_suggestion=grade,
        hard_rejects=hard,
        soft_notes=soft,
        missing_required=missing,
        filled_slots=filled_slots,
        strongest_positive=best_pos[0],
        strongest_negative=best_neg[0] if best_neg[0] else (missing[0] if missing else ""),
        factors=factors,
        primary_weights=primary_w,
        confidence=conf,
        p_reliability=p_rel,
    )


def _market_alias_match(markets: frozenset[str], family: str) -> bool:
    if "totals" in markets and family in ("totals_over", "totals_under"):
        return True
    if "btts" in markets and family in ("btts_yes", "btts_no"):
        return True
    if "prop*" in markets and family.startswith("prop"):
        return True
    return False


def _dual_tier1(fills: list, sources: list, min_chars: int) -> bool:
    tier1_filled = [s for s, f, app, _r in fills if app and s.tier == 1 and f >= 0.35]
    if not tier1_filled:
        return False
    return distinct_quality_domains(sources, min_chars=min_chars) >= 2
