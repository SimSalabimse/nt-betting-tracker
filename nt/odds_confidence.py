"""
Sliding odds-band confidence gates (1.40ÔÇô2.60).

Bands (half-open where noted; D includes 2.60):
  A  1.40ÔÇô1.60  Short high-confidence ÔÇö Grade A, elevated EV, stake haircut
  B  1.60ÔÇô1.85  Short-medium ÔÇö strong B/A, explore disabled/weakened
  C  1.85ÔÇô2.30  Core ÔÇö solid B + supporting evidence (stricter than old preferred)
  D  2.30ÔÇô2.60  Upper ÔÇö solid B, stronger matchup bar for underdog HC
  outside: below 1.40 reject (unless exceptional A); above 2.60 ÔåÆ high-odds rules

Does not change capital_v2 / phase / secure. Coverage floor must not bypass these gates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from nt.evidence import has_core_reason, normalize_sources

GRADE_RANK = {"A": 4, "B": 3, "C": 2, "F": 0, "": 0}

# Band labels for reasoning / audit
BAND_A = "A_short_high_conf"  # 1.40ÔÇô1.60
BAND_B = "B_short_medium"  # 1.60ÔÇô1.85
BAND_C = "C_core"  # 1.85ÔÇô2.30
BAND_D = "D_upper"  # 2.30ÔÇô2.60
BAND_BELOW = "below_floor"  # < 1.40
BAND_HIGH = "high_odds"  # > 2.60


def odds_confidence_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    sel = dict((cfg or {}).get("selection") or {})
    raw = dict(sel.get("odds_confidence") or {})
    defaults: dict[str, Any] = {
        "enabled": True,
        "usable_lo": 1.40,
        "usable_hi": 2.60,
        "bands": {
            "A": {
                "lo": 1.40,
                "hi": 1.60,  # exclusive hi
                "min_grade": "A",
                "min_ev": 0.035,
                "min_sources": 8,
                "stake_mult": 0.80,
                "require_h2h_or_rank_form": True,
                "explore_allowed": False,
            },
            "B": {
                "lo": 1.60,
                "hi": 1.85,
                "min_grade": "B",
                "min_ev": 0.025,
                "min_sources": 7,
                "stake_mult": 0.90,
                "require_core_plus_support": True,
                "explore_allowed": False,
            },
            "C": {
                "lo": 1.85,
                "hi": 2.30,
                "min_grade": "B",
                "min_ev": 0.022,
                "min_sources": 6,
                "stake_mult": 1.0,
                "require_core_plus_support": True,
                "require_h2h_checked": True,
                "explore_allowed": True,
                "explore_ev_cap": 0.015,  # explore floor cannot go softer than this
            },
            "D": {
                "lo": 2.30,
                "hi": 2.60,  # inclusive via classify
                "min_grade": "B",
                "min_ev": 0.025,
                "min_sources": 7,
                "stake_mult": 0.95,
                "require_core_plus_support": True,
                "require_h2h_checked": True,
                "underdog_hc_require_matchup": True,
                "explore_allowed": True,
                "explore_ev_cap": 0.015,
            },
        },
        "below_floor": {
            "allow_exceptional": True,
            "min_grade": "A",
            "min_ev": 0.05,
            "min_sources": 10,
            "stake_mult": 0.70,
        },
        "underdog_hc_negative_h2h_reject": True,
    }
    out = {**defaults, **raw}
    if isinstance(raw.get("bands"), dict):
        bands = dict(defaults["bands"])
        for k, v in raw["bands"].items():
            if isinstance(v, dict) and k in bands:
                bands[k] = {**bands[k], **v}
            elif isinstance(v, dict):
                bands[k] = v
        out["bands"] = bands
    if isinstance(raw.get("below_floor"), dict):
        out["below_floor"] = {**defaults["below_floor"], **raw["below_floor"]}
    return out


def classify_odds_confidence_band(
    odds: float, cfg: dict[str, Any] | None = None
) -> str:
    """Return band id for decimal odds."""
    o = float(odds)
    oc = odds_confidence_cfg(cfg)
    lo = float(oc.get("usable_lo") or 1.40)
    hi = float(oc.get("usable_hi") or 2.60)
    if o < lo:
        return BAND_BELOW
    if o > hi:
        return BAND_HIGH
    bands = oc.get("bands") or {}
    a = bands.get("A") or {}
    b = bands.get("B") or {}
    c = bands.get("C") or {}
    d = bands.get("D") or {}
    if o < float(a.get("hi") or 1.60):
        return BAND_A
    if o < float(b.get("hi") or 1.85):
        return BAND_B
    if o < float(c.get("hi") or 2.30):
        return BAND_C
    return BAND_D  # through usable_hi inclusive


def band_letter(band_id: str) -> str:
    if band_id.startswith("A"):
        return "A"
    if band_id.startswith("B"):
        return "B"
    if band_id.startswith("C"):
        return "C"
    if band_id.startswith("D"):
        return "D"
    if band_id == BAND_BELOW:
        return "below"
    if band_id == BAND_HIGH:
        return "high"
    return "?"


def grade_meets(grade: str, min_grade: str) -> bool:
    g = (grade or "F").upper()[:1]
    m = (min_grade or "B").upper()[:1]
    return GRADE_RANK.get(g, 0) >= GRADE_RANK.get(m, 0)


def _blob(ev: dict[str, Any] | None) -> str:
    if not ev:
        return ""
    parts = [
        str(ev.get("summary") or ""),
        str(ev.get("failure_modes") or ""),
        str(ev.get("notes") or ""),
        str(ev.get("matchup_notes") or ""),
        str(ev.get("h2h") or ""),
        str(ev.get("form") or ""),
    ]
    for s in normalize_sources(ev.get("sources")):
        parts.append(str(s.get("name") or ""))
        parts.append(str(s.get("note") or s.get("takeaway") or s.get("url") or ""))
    return " ".join(parts).lower()


def detect_h2h_signal(
    ev: dict[str, Any] | None,
    *,
    feh: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    H2H / matchup detection for band gates.

    Prefer FEH h2h polarity when feh_version / feh.h2h present (PR3 compose).
    Else use shared normalize_h2h for structured pack fields (mixed strings).
    Regex blob is last resort only when no structured/FEH polarity exists.
    """
    # 1) FEH audit polarity (authoritative when present)
    feh_h2h = None
    if isinstance(feh, dict):
        raw = feh.get("h2h")
        if isinstance(raw, dict):
            feh_h2h = raw
        # also accept nested natural path from full FEHResult.to_audit()
    if feh_h2h is not None:
        checked = bool(feh_h2h.get("checked"))
        positive = bool(feh_h2h.get("positive"))
        negative = bool(feh_h2h.get("negative"))
        return {
            "checked": checked,
            "positive": positive and not negative,
            "negative": negative,
            "source": "feh",
            "polarity": feh_h2h.get("polarity"),
        }

    # 2) Shared normalize_h2h (same as FEH) for structured pack fields
    if ev and (isinstance(ev.get("h2h"), dict) or ev.get("h2h") is not None):
        try:
            from nt.evidence_hierarchy.h2h_normalize import normalize_h2h

            norm = normalize_h2h(ev)
            return {
                "checked": norm.checked,
                "positive": norm.positive and not norm.negative,
                "negative": norm.negative,
                "source": "normalize_h2h",
                "polarity": norm.polarity,
            }
        except Exception:
            pass

    # 3) Regex / blob fallback (legacy packs without structured H2H)
    text = _blob(ev)
    checked = bool(
        re.search(
            r"\bh2h\b|head[\s-]?to[\s-]?head|matchup|head2head|previous meetings|"
            r"never beaten|historikk|innbyrdes",
            text,
        )
    )
    if ev and (ev.get("h2h") is not None or ev.get("matchup") is not None):
        checked = True
    positive = bool(
        re.search(
            r"h2h\s*(edge|pos|positive|\+|strong)|positive h2h|favou?rs? |"
            r"won\s+\d|leads?\s+h2h|dominat",
            text,
        )
    )
    negative = bool(
        re.search(
            r"never beaten|0[–\-]?\d in h2h|negative h2h|h2h\s*(weak|poor|neg)|"
            r"lost\s+all|no wins? against|winless vs",
            text,
        )
    )
    return {
        "checked": checked,
        "positive": positive and not negative,
        "negative": negative,
        "source": "regex",
        "polarity": None,
    }


def detect_rank_form_edge(ev: dict[str, Any] | None) -> bool:
    text = _blob(ev)
    return bool(
        re.search(
            r"\branking\b|\belo\b|form\b|seed\b|world\s*no|atp|wta|fifa|"
            r"table position|goal difference|vrs\b|rating gap|class difference",
            text,
        )
    )


def count_support_factors(ev: dict[str, Any] | None) -> tuple[int, list[str]]:
    """Count distinct supporting factors beyond bare summary."""
    if not ev:
        return 0, []
    found: list[str] = []
    text = _blob(ev)
    checks = [
        ("h2h", r"\bh2h\b|head[\s-]?to[\s-]?head|matchup"),
        ("form", r"\bform\b|recent results|last\s+\d"),
        ("ranking", r"\branking\b|\belo\b|seed\b|world\s*no"),
        ("venue", r"\bvenue\b|home\b|away\b|court\b|surface\b"),
        ("motivation", r"motivation|must[\s-]?win|rotation|rested|fatigue"),
        ("injury", r"injur|availability|confirmed lineup|doubt"),
        ("stats", r"xg\b|shot|serve|break point|possession"),
    ]
    for name, pat in checks:
        if re.search(pat, text):
            found.append(name)
    sources = normalize_sources(ev.get("sources"))
    if len(sources) >= 2 and "multi_source" not in found:
        found.append("multi_source")
    if has_core_reason(ev) and "core_reason" not in found:
        found.append("core_reason")
    return len(found), found


def is_underdog_handicap(selection: str, odds: float) -> bool:
    """Heuristic: HC / +handicap line that is not short chalk."""
    s = (selection or "").lower()
    hc = bool(
        re.search(
            r"handikap|handicap|\+\d|plus\s*\d|underdog|\+\s*\d",
            s,
        )
    )
    if not hc:
        return False
    # Plus lines or explicitly long prices
    if re.search(r"\+\s*\d|\+\d", selection or ""):
        return True
    return float(odds) >= 1.85


@dataclass
class OddsBandGateResult:
    ok: bool
    band_id: str
    band_label: str
    requirements_checked: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)
    min_ev: float | None = None
    stake_mult: float = 1.0
    explore_allowed: bool = True
    explore_ev_cap: float | None = None
    reason: str = ""

    def to_audit(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "band_id": self.band_id,
            "band_label": self.band_label,
            "requirements_checked": list(self.requirements_checked),
            "failures": list(self.failures),
            "passes": list(self.passes),
            "min_ev": self.min_ev,
            "stake_mult": self.stake_mult,
            "explore_allowed": self.explore_allowed,
            "explore_ev_cap": self.explore_ev_cap,
            "reason": self.reason,
        }


def evaluate_odds_band_gates(
    *,
    odds: float,
    grade: str,
    evidence: dict[str, Any] | None,
    selection: str = "",
    cfg: dict[str, Any] | None = None,
    feh: dict[str, Any] | None = None,
) -> OddsBandGateResult:
    """
    Enforce sliding confidence band requirements.
    Returns ok=False with reason when selection must be rejected for band rules.
    High-odds band (above usable_hi) returns ok=True with band HIGH — caller applies
    existing high_odds grade/EV rules.

    FEH compose (PR3):
      - bands cannot bypass FEH hard reject / grade F
      - H2H polarity prefers feh.h2h when feh_version present
    """
    oc = odds_confidence_cfg(cfg)
    if not oc.get("enabled", True):
        return OddsBandGateResult(
            ok=True,
            band_id="disabled",
            band_label="disabled",
            reason="odds_confidence disabled",
        )

    # FEH fail-closed: bands never place what FEH hard-rejected
    if isinstance(feh, dict) and (
        feh.get("hard_reject")
        or str(feh.get("final_grade_suggestion") or "").upper() == "F"
        or str(grade or "").upper() == "F"
    ):
        return OddsBandGateResult(
            ok=False,
            band_id="feh_blocked",
            band_label="FEH hard reject / grade F",
            requirements_checked=["feh_non_bypassable"],
            failures=["FEH hard reject or grade F — odds_confidence cannot place"],
            passes=[],
            stake_mult=1.0,
            explore_allowed=False,
            reason="FEH hard reject / grade F — bands cannot bypass",
        )

    band_id = classify_odds_confidence_band(odds, cfg)
    letter = band_letter(band_id)
    sources = normalize_sources((evidence or {}).get("sources"))
    n_src = len(sources)
    h2h = detect_h2h_signal(evidence, feh=feh)
    rank_form = detect_rank_form_edge(evidence)
    n_sup, support = count_support_factors(evidence)
    core = has_core_reason(evidence) if evidence else False

    checked: list[str] = [f"band={band_id}", f"odds={float(odds):.3f}", f"grade={grade}"]
    if isinstance(feh, dict) and feh.get("feh_version") is not None:
        checked.append(f"feh_h2h_source={h2h.get('source')}")
    failures: list[str] = []
    passes: list[str] = []

    # --- High odds: defer to existing portfolio high-odds path ---
    if band_id == BAND_HIGH:
        return OddsBandGateResult(
            ok=True,
            band_id=BAND_HIGH,
            band_label="High odds (>2.60)",
            requirements_checked=checked + ["defer_high_odds_rules"],
            passes=["deferred_to_high_odds_rules"],
            stake_mult=1.0,
            explore_allowed=True,
            reason="above usable band ÔÇö high-odds rules apply",
        )

    # --- Below floor ---
    if band_id == BAND_BELOW:
        bf = oc.get("below_floor") or {}
        checked.extend(["below_1.40", "exceptional_A_only"])
        if not bf.get("allow_exceptional", True):
            failures.append("odds below usable floor 1.40")
        else:
            if not grade_meets(grade, str(bf.get("min_grade") or "A")):
                failures.append(
                    f"odds {odds:.2f} < 1.40 requires grade A (got {grade})"
                )
            need_src = int(bf.get("min_sources") or 10)
            if n_src < need_src:
                failures.append(f"below-floor sources {n_src} < {need_src}")
            if not (h2h["positive"] or rank_form):
                failures.append(
                    "below-floor requires positive H2H or strong ranking/form edge"
                )
            if not failures:
                passes.append("exceptional_short_price_ok")
        ok = not failures
        return OddsBandGateResult(
            ok=ok,
            band_id=BAND_BELOW,
            band_label="Below 1.40 (exceptional only)",
            requirements_checked=checked,
            failures=failures,
            passes=passes,
            min_ev=float(bf.get("min_ev") or 0.05),
            stake_mult=float(bf.get("stake_mult") or 0.70),
            explore_allowed=False,
            reason="; ".join(failures) if failures else "exceptional short price",
        )

    bands = oc.get("bands") or {}
    bcfg = bands.get(letter) or bands.get(letter[0]) or {}
    min_grade = str(bcfg.get("min_grade") or "B")
    min_ev = float(bcfg.get("min_ev") or 0.02)
    min_sources = int(bcfg.get("min_sources") or 6)
    stake_mult = float(bcfg.get("stake_mult") or 1.0)
    explore_allowed = bool(bcfg.get("explore_allowed", True))
    explore_ev_cap = bcfg.get("explore_ev_cap")
    if explore_ev_cap is not None:
        explore_ev_cap = float(explore_ev_cap)

    checked.append(f"min_grade={min_grade}")
    checked.append(f"min_ev={min_ev}")
    checked.append(f"min_sources={min_sources}")

    if not grade_meets(grade, min_grade):
        failures.append(f"grade {grade} < band min {min_grade}")
    else:
        passes.append(f"grade_ok:{grade}")

    if n_src < min_sources:
        failures.append(f"sources {n_src} < band min {min_sources}")
    else:
        passes.append(f"sources_ok:{n_src}")

    # Band A specials
    if letter == "A":
        checked.append("require_h2h_or_rank_form")
        checked.append("short_price_edge_justification")
        if bcfg.get("require_h2h_or_rank_form", True):
            if h2h["positive"] or rank_form:
                passes.append(
                    "h2h_or_rank_form:"
                    + (
                        "h2h_pos"
                        if h2h["positive"]
                        else "rank_form"
                    )
                )
            else:
                failures.append(
                    "Band A requires positive H2H or strong ranking/form edge "
                    "with multi-source support"
                )
        if n_src < 2:
            failures.append("Band A requires multiple independent sources")
        # Explicit short-price justification in summary
        if evidence and not re.search(
            r"short|price|edge|value|mispriced|market wrong|line long",
            str(evidence.get("summary") or "").lower(),
        ):
            # soft fail only if no other positive edge language
            if not (h2h["positive"] or rank_form):
                failures.append(
                    "Band A reasoning must justify short-price edge in summary"
                )
            else:
                passes.append("edge_implied_by_h2h_or_rank")

    # Band B / C / D support + core
    if letter in ("B", "C", "D") and bcfg.get("require_core_plus_support", True):
        checked.append("core_reason+support")
        if not core:
            failures.append("missing clear core reason (summary)")
        else:
            passes.append("core_reason")
        # Pure explore/mid-odds is not enough ÔÇö need ÔëÑ1 real support beyond core
        real_support = [s for s in support if s not in ("core_reason",)]
        if letter == "C":
            # Raise bar: need at least one support factor beyond multi_source alone
            # OR multi_source + h2h checked
            if not real_support:
                failures.append(
                    "Band C requires supporting evidence beyond bare mid-odds/explore"
                )
            elif real_support == ["multi_source"] and not h2h["checked"]:
                failures.append(
                    "Band C: multi-source alone without matchup/H2H check is too thin"
                )
            else:
                passes.append("support:" + ",".join(real_support[:4]))
        elif letter == "B":
            if len(real_support) < 1:
                failures.append(
                    "Band B requires solid core + ÔëÑ1 strong supporting factor"
                )
            else:
                passes.append("support:" + ",".join(real_support[:4]))
        elif letter == "D":
            if len(real_support) < 1:
                failures.append(
                    "Band D requires solid core + supporting evidence (higher variance)"
                )
            else:
                passes.append("support:" + ",".join(real_support[:4]))

    # H2H checked requirement (C/D)
    if bcfg.get("require_h2h_checked"):
        checked.append("h2h_matchup_checked")
        if h2h["checked"]:
            passes.append("h2h_checked")
            if h2h["negative"] and oc.get("underdog_hc_negative_h2h_reject", True):
                if is_underdog_handicap(selection, odds):
                    failures.append(
                        "negative H2H / never-beaten signal on underdog handicap"
                    )
        else:
            failures.append("H2H / matchup history not checked in pack")

    # Underdog HC matchup bar (any band, stronger on D)
    if is_underdog_handicap(selection, odds):
        checked.append("underdog_handicap_matchup")
        if bcfg.get("underdog_hc_require_matchup") or letter in ("A", "B", "D"):
            if h2h["negative"]:
                failures.append(
                    "underdog handicap with heavily negative H2H ÔÇö reject/force-down"
                )
            elif not h2h["checked"] and letter == "D":
                failures.append(
                    "Band D underdog handicap requires explicit matchup/H2H assessment"
                )
            elif h2h["checked"]:
                passes.append("underdog_hc_matchup_ok")

    ok = not failures
    label_map = {
        "A": "A Short high-confidence (1.40ÔÇô1.60)",
        "B": "B Short-medium (1.60ÔÇô1.85)",
        "C": "C Core (1.85ÔÇô2.30)",
        "D": "D Upper (2.30ÔÇô2.60)",
    }
    return OddsBandGateResult(
        ok=ok,
        band_id=band_id,
        band_label=label_map.get(letter, band_id),
        requirements_checked=checked,
        failures=failures,
        passes=passes,
        min_ev=min_ev,
        stake_mult=stake_mult if ok else 1.0,
        explore_allowed=explore_allowed,
        explore_ev_cap=explore_ev_cap,
        reason="; ".join(failures) if failures else f"passed {band_id}",
    )
