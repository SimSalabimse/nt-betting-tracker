"""Forced Evidence Hierarchy orchestrator — pure recompute every grade."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from nt.evidence_hierarchy.anti_soft_underdog import (
    evaluate_anti_soft_underdog,
    is_minus_handicap,
    is_plus_handicap,
)
from nt.evidence_hierarchy.cards import SportCard, default_quarantine_card, load_sport_card
from nt.evidence_hierarchy.checklist import ChecklistAnswers, load_checklist_from_pack
from nt.evidence_hierarchy.h2h_normalize import normalize_h2h
from nt.evidence_hierarchy.normalize import normalize_sport_for_research
from nt.evidence_hierarchy.score import (
    evidence_cfg,
    place_uses_saef,
    score_evidence,
)
from nt.evidence_hierarchy.side_select import SideDecision, decide_side
from nt.evidence_hierarchy.types import FEHRejectCode


def _family(selection: str) -> str:
    s = (selection or "").lower()
    if re.search(r"btts|begge lag|both teams", s):
        if re.search(r"nei|no\b", s):
            return "btts_no"
        return "btts_yes"
    if re.search(r"over\s*\d|over\b", s) and re.search(
        r"total|mål|mal|kart|runder|games?|legs?", s
    ):
        return "totals_over"
    if re.search(r"under\s*\d|under\b", s) and re.search(
        r"total|mål|mal|kart|runder|games?|legs?", s
    ):
        return "totals_under"
    if re.search(r"handikap|handicap|\+\d|\-\d", s):
        return "handicap"
    if re.search(r"prop|scorer|points|assist", s):
        return "prop"
    if re.search(r"vinner|to win|winner|ml\b|moneyline", s):
        return "ml"
    return "other"


def _is_underdog_hc(selection: str, odds: float = 0.0) -> bool:
    """Underdog HC = plus handicap only. Odds never substitute for sign."""
    _ = odds  # odds used only for soft-band gates, not UD classification
    return is_plus_handicap(selection)


def _is_favourite_hc(selection: str) -> bool:
    return is_minus_handicap(selection) and not is_plus_handicap(selection)


def forced_hierarchy_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Normalized forced_hierarchy + evidence flags for FEH."""
    ec = evidence_cfg(cfg)
    sel = dict((cfg or {}).get("selection") or {})
    raw = dict(sel.get("evidence") or {})
    fh = dict(raw.get("forced_hierarchy") or {})
    ml = dict(fh.get("anti_soft_ml_dogs") or {})
    return {
        **ec,
        "fail_closed": bool(raw.get("fail_closed", True)),
        "require_checklist": bool(fh.get("require_checklist", True)),
        "anti_soft_underdog": bool(fh.get("anti_soft_underdog", True)),
        "allow_soft_ud_grade_c": bool(fh.get("allow_soft_ud_grade_c", False)),
        "natural_market_elevation": bool(fh.get("natural_market_elevation", False)),
        "side_first": bool(fh.get("side_first", True)),
        "soft_ud_odds_lo": float(fh.get("soft_ud_odds_lo") or 1.70),
        "soft_ud_odds_hi_hard": float(fh.get("soft_ud_odds_hi_hard") or 2.20),
        "soft_ud_odds_hi_soft": float(fh.get("soft_ud_odds_hi_soft") or 2.60),
        "anti_soft_ml_dogs_individual": bool(ml.get("individual_sports", True)),
        "anti_soft_ml_dogs_team": bool(ml.get("team_sports", False)),
    }


@dataclass
class FEHResult:
    """Result of run_forced_evidence_hierarchy (always recomputed)."""

    feh_version: int = 1
    place_owning: bool = False
    hard_reject: bool = False
    reject_codes: list[str] = field(default_factory=list)
    grade_cap: str = "B"  # A|B|C|F — min'd with SAEF
    checklist: ChecklistAnswers | None = None
    checklist_complete: bool = False
    side: SideDecision | None = None
    anti_soft: dict[str, Any] = field(default_factory=dict)
    natural_markets: dict[str, Any] = field(default_factory=dict)
    h2h: dict[str, Any] = field(default_factory=dict)
    saef_audit: dict[str, Any] | None = None
    saef_grade: str | None = None
    notes: list[str] = field(default_factory=list)
    final_grade_suggestion: str = "F"

    def to_audit(self) -> dict[str, Any]:
        return {
            "feh_version": self.feh_version,
            "place_owning": self.place_owning,
            "hard_reject": self.hard_reject,
            "reject_codes": list(self.reject_codes),
            "grade_cap": self.grade_cap,
            "checklist_complete": self.checklist_complete,
            "checklist": self.checklist.to_dict() if self.checklist else None,
            "side": self.side.to_dict() if self.side else None,
            "anti_soft_underdog": dict(self.anti_soft),
            "natural_market_eval": dict(self.natural_markets),
            "h2h": dict(self.h2h),
            "saef": self.saef_audit,
            "saef_grade": self.saef_grade,
            "final_grade_suggestion": self.final_grade_suggestion,
            "notes": list(self.notes)[:12],
        }


def _natural_markets_stub(
    *,
    enabled: bool,
) -> dict[str, Any]:
    """PR2: natural markets optional stub — always N/A (full gate in PR3)."""
    return {
        "required": False,
        "candidates": [],
        "evaluated": [],
        "missing_on_board": [],
        "comparison_vs_hc": "",
        "preferred_market": None,
        "hard_reject": False,
        "reject_code": None,
        "status": "n_a" if not enabled else "stub_n_a",
        "note": "PR2 natural market elevation stub — always N/A",
    }


def _min_grade(a: str, b: str) -> str:
    order = {"F": 0, "C": 1, "B": 2, "A": 3}
    return a if order.get(a, 0) <= order.get(b, 0) else b


def run_forced_evidence_hierarchy(
    ev: dict[str, Any] | None,
    *,
    sport: str = "",
    selection: str = "",
    odds: float = 2.0,
    cfg: dict[str, Any] | None = None,
    card: SportCard | None = None,
    run_saef: bool = True,
) -> FEHResult:
    """
    Pure FEH recompute (design pipeline):

      normalize_h2h → checklist → decide_side → anti-soft → natural (stub)
      → score_evidence (optional) → grade_cap

    Never mutates pack. Ignore stored grade_cap on pack.
    Explore / temp_ev_relax / promo cannot bypass — they never enter this function.
    """
    fh = forced_hierarchy_cfg(cfg)
    place_owning = place_uses_saef(cfg)
    notes: list[str] = []
    codes: list[str] = []
    hard = False
    grade_cap = "B"

    try:
        sport_key = normalize_sport_for_research(
            sport or (ev or {}).get("sport") or ""
        )
        sel = selection or str((ev or {}).get("selection") or "")
        family = _family(sel)
        underdog_hc = _is_underdog_hc(sel, float(odds))
        fav_hc = _is_favourite_hc(sel)

        if card is None:
            card = load_sport_card(sport_key, cfg)
            if card is None and fh.get("auto_onboard_cards", True):
                card = default_quarantine_card(sport_key)
            if card is None:
                card = load_sport_card("default", cfg)

        h2h_norm = normalize_h2h(ev)
        h2h = h2h_norm.to_dict()

        primary_ids: list[str] = []
        if card is not None:
            primary_ids = [
                str(f.get("id"))
                for f in (card.primary or [])
                if f.get("id")
            ]

        checklist = load_checklist_from_pack(
            ev, h2h=h2h, primary_factor_ids=primary_ids
        )
        checklist_ok = bool(checklist.complete)

        # 1) Checklist fail-closed when place-owning + require_checklist
        if place_owning and fh.get("require_checklist", True) and not checklist_ok:
            hard = True
            codes.append("FEH_CHECKLIST_INCOMPLETE")
            notes.append(
                "checklist incomplete: "
                + ",".join(checklist.incomplete_reasons[:6])
            )
            grade_cap = "F"

        # 2) Side selection (always compute for audit)
        side = decide_side(
            checklist,
            h2h,
            selection=sel,
            odds=float(odds),
            is_underdog_hc=underdog_hc,
            is_favourite_hc=fav_hc,
            family=family,
            soft_ud_odds_lo=float(fh["soft_ud_odds_lo"]),
            soft_ud_odds_hi_hard=float(fh["soft_ud_odds_hi_hard"]),
            soft_ud_odds_hi_soft=float(fh["soft_ud_odds_hi_soft"]),
            # None → derive from plus-HC + odds band (no force)
            soft_ud_band=None,
        )
        if place_owning and side.hard_reject and side.reject_code:
            hard = True
            if side.reject_code not in codes:
                codes.append(side.reject_code)
            notes.extend(side.notes)
            grade_cap = "F"

        # 3) Anti-soft (runs even if checklist incomplete — Smith still gets ANTI_SOFT)
        anti = evaluate_anti_soft_underdog(
            ev,
            checklist,
            h2h,
            card=card,
            selection=sel,
            odds=float(odds),
            family=family,
            soft_ud_odds_lo=float(fh["soft_ud_odds_lo"]),
            soft_ud_odds_hi_hard=float(fh["soft_ud_odds_hi_hard"]),
            soft_ud_odds_hi_soft=float(fh["soft_ud_odds_hi_soft"]),
            anti_soft_ml_dogs_individual=bool(fh["anti_soft_ml_dogs_individual"]),
            anti_soft_ml_dogs_team=bool(fh["anti_soft_ml_dogs_team"]),
            allow_soft_ud_grade_c=bool(fh["allow_soft_ud_grade_c"]),
            enabled=bool(fh.get("anti_soft_underdog", True)),
        )
        if place_owning and anti.hard_reject and anti.reject_code:
            hard = True
            if anti.reject_code not in codes:
                codes.append(anti.reject_code)
            notes.extend(anti.notes)
            grade_cap = "F"

        # 4) Natural markets stub (PR2 always N/A — no hard reject here)
        natural = _natural_markets_stub(
            enabled=bool(fh.get("natural_market_elevation"))
        )
        notes.append(str(natural.get("note") or "natural N/A"))

        # 5) SAEF scorecard
        saef_audit: dict[str, Any] | None = None
        saef_grade: str | None = None
        if run_saef:
            sc = score_evidence(
                ev,
                sport=sport_key,
                selection=sel,
                odds=float(odds),
                cfg=cfg,
                card=card,
            )
            saef_audit = sc.to_audit()
            saef_grade = sc.grade_suggestion
            if place_owning and sc.hard_rejects:
                hard = True
                codes.append("FEH_SAEF_HARD")
                for hr in sc.hard_rejects:
                    notes.append(f"saef:{hr}")
                grade_cap = "F"
            if not sc.onboarded and place_owning and not fh.get(
                "allow_quarantine_place"
            ):
                hard = True
                if "FEH_QUARANTINE_SPORT" not in codes:
                    codes.append("FEH_QUARANTINE_SPORT")
                grade_cap = "F"

        # Compose final grade suggestion
        if hard:
            final = "F"
            grade_cap = "F"
        elif saef_grade:
            final = _min_grade(saef_grade, grade_cap)
        else:
            final = grade_cap

        # Deduplicate codes preserving order
        seen: set[str] = set()
        uniq_codes: list[str] = []
        for c in codes:
            if c not in seen:
                seen.add(c)
                uniq_codes.append(c)

        return FEHResult(
            feh_version=1,
            place_owning=place_owning,
            hard_reject=hard,
            reject_codes=uniq_codes,
            grade_cap=grade_cap,
            checklist=checklist,
            checklist_complete=checklist_ok,
            side=side,
            anti_soft=anti.to_dict(),
            natural_markets=natural,
            h2h=h2h,
            saef_audit=saef_audit,
            saef_grade=saef_grade,
            notes=notes,
            final_grade_suggestion=final,
        )
    except Exception as exc:
        # Fail-closed when place-owning or fail_closed
        if place_owning or fh.get("fail_closed", True):
            return FEHResult(
                feh_version=1,
                place_owning=place_owning,
                hard_reject=True,
                reject_codes=["FEH_ERROR"],
                grade_cap="F",
                notes=[f"FEH_ERROR:{exc}"],
                final_grade_suggestion="F",
            )
        return FEHResult(
            feh_version=1,
            place_owning=False,
            hard_reject=False,
            reject_codes=[],
            grade_cap="B",
            notes=[f"feh_shadow_error:{exc}"],
            final_grade_suggestion="B",
        )


# Re-export for type checkers / tests
__all__ = [
    "FEHResult",
    "FEHRejectCode",
    "forced_hierarchy_cfg",
    "run_forced_evidence_hierarchy",
    "place_uses_saef",
]
