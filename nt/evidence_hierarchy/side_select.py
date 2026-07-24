"""Side selection algorithm — pure decide_side + vote truth table."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from nt.evidence_hierarchy.checklist import ChecklistAnswers, SideLean

EvidenceSide = Literal[
    "favourite",
    "underdog",
    "even",
    "unclear",
    "natural_over",
    "natural_under",
    "n_a",
]
SelectionSide = Literal["favourite", "underdog", "over", "under", "other"]
Vote = Literal["favourite", "underdog", "even", "abstain"]


@dataclass
class SideDecision:
    evidence_side: EvidenceSide
    selection_side: SelectionSide
    agrees_with_selection: bool
    conflict: bool
    method: str
    hard_reject: bool
    reject_code: str | None  # FEH_SIDE_CONFLICT | FEH_SIDE_UNCLEAR_UD | FEH_PRICE_LED_SIDE
    notes: list[str] = field(default_factory=list)
    ranking_vote: Vote = "abstain"
    form_vote: Vote = "abstain"
    h2h_vote: Vote = "abstain"

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_side": self.evidence_side,
            "selection_side": self.selection_side,
            "agrees_with_selection": self.agrees_with_selection,
            "conflict": self.conflict,
            "method": self.method,
            "hard_reject": self.hard_reject,
            "reject_code": self.reject_code,
            "notes": list(self.notes),
            "ranking_vote": self.ranking_vote,
            "form_vote": self.form_vote,
            "h2h_vote": self.h2h_vote,
        }


def _lean_to_vote(lean: SideLean, conf: float, *, min_conf: float = 0.5) -> Vote:
    if lean in ("unknown", "n_a", ""):
        return "abstain"
    if lean in ("even",):
        return "even"
    if lean in ("favourite", "home", "player_a"):
        return "favourite" if conf >= min_conf * 0.5 else "abstain"
    if lean in ("underdog", "away", "player_b"):
        return "underdog" if conf >= min_conf * 0.5 else "abstain"
    return "abstain"


def _h2h_vote(h2h: dict[str, Any]) -> Vote:
    if h2h.get("positive"):
        return "underdog"  # positive H2H on dog pack = supports underdog selection
    if h2h.get("negative"):
        return "favourite"
    if h2h.get("mixed"):
        return "even"
    return "abstain"


def _vote_weight(vote: Vote, conf: float, *, h2h: bool = False) -> float:
    if vote == "abstain":
        return 0.0
    if h2h:
        if vote in ("favourite", "underdog"):
            return 1.2
        return 0.0  # mixed/even h2h weight 0 for aggregation edge
    base = 1.0 if conf >= 0.5 else 0.5
    if vote == "even":
        return base * 0.5
    return base


def _selection_side(
    selection: str,
    *,
    is_underdog_hc: bool,
    is_favourite_hc: bool,
    family: str,
    odds: float,
) -> SelectionSide:
    s = (selection or "").lower()
    if family in ("totals_over",) or re.search(r"\bover\b", s):
        if re.search(r"total|mål|mal|kart|runder|games?|legs?", s):
            return "over"
    if family in ("totals_under",) or re.search(r"\bunder\b", s):
        if re.search(r"total|mål|mal|kart|runder|games?|legs?", s):
            return "under"
    if is_underdog_hc:
        return "underdog"
    if is_favourite_hc:
        return "favourite"
    # ML dog/fav by odds heuristic
    if family == "ml" or re.search(r"vinner|to win|winner|ml\b", s):
        if float(odds) >= 1.70:
            return "underdog"
        return "favourite"
    if re.search(r"\+\s*\d|\+\d", selection or ""):
        return "underdog"
    if re.search(r"-\s*\d|-\d", selection or ""):
        return "favourite"
    return "other"


def decide_side(
    checklist: ChecklistAnswers,
    h2h: dict[str, Any],
    *,
    selection: str,
    odds: float,
    is_underdog_hc: bool,
    is_favourite_hc: bool,
    family: str,
    soft_ud_odds_lo: float = 1.70,
    soft_ud_odds_hi_hard: float = 2.20,
    soft_ud_band: bool = False,
) -> SideDecision:
    """
    Votes from Q1 ranking, Q2 form, Q3/h2h polarity.
    Normative truth table for soft UD HC (design §4).
    """
    notes: list[str] = []
    sel_side = _selection_side(
        selection,
        is_underdog_hc=is_underdog_hc,
        is_favourite_hc=is_favourite_hc,
        family=family,
        odds=float(odds),
    )

    # Totals family: do not force fav/ud
    if family in ("totals_over", "totals_under") or sel_side in ("over", "under"):
        ev_side: EvidenceSide = (
            "natural_over" if sel_side == "over" else "natural_under"
        )
        return SideDecision(
            evidence_side=ev_side,
            selection_side=sel_side,
            agrees_with_selection=True,
            conflict=False,
            method="totals_passthrough",
            hard_reject=False,
            reject_code=None,
            notes=["totals family — side rule N/A for fav/ud"],
        )

    r_vote = _lean_to_vote(
        checklist.higher_ranked_side, checklist.ranking_confidence
    )
    f_vote = _lean_to_vote(checklist.better_form_side, checklist.form_confidence)
    h_vote = _h2h_vote(h2h if isinstance(h2h, dict) else {})

    # Weighted scores
    scores = {"favourite": 0.0, "underdog": 0.0, "even": 0.0}
    for vote, conf, is_h2h in (
        (r_vote, checklist.ranking_confidence, False),
        (f_vote, checklist.form_confidence, False),
        (h_vote, 1.0, True),
    ):
        w = _vote_weight(vote, conf, h2h=is_h2h)
        if vote in scores:
            scores[vote] += w
        elif vote == "abstain":
            continue

    # Truth table (design §4) — explicit soft-UD cases first
    evidence_side: EvidenceSide
    method = "vote_aggregate"

    if r_vote == "favourite" and f_vote == "favourite" and h_vote != "underdog":
        evidence_side = "favourite"
        method = "rank_form_fav"
    elif r_vote == "favourite" and f_vote in ("even", "abstain") and h_vote in (
        "even",
        "abstain",
    ):
        evidence_side = "favourite"
        method = "rank_fav_form_neutral"
    elif r_vote == "favourite" and f_vote == "underdog" and h_vote == "underdog":
        # positive h2h vote = underdog
        evidence_side = "unclear"
        method = "split_rank_form_pos_h2h"
    elif r_vote == "favourite" and f_vote == "underdog" and h_vote != "underdog":
        evidence_side = "favourite"
        method = "rank_fav_form_split_no_pos_h2h"
    elif r_vote == "underdog" and f_vote == "underdog" and h_vote == "underdog":
        evidence_side = "underdog"
        method = "all_dog"
    elif r_vote == "underdog" and f_vote == "underdog" and h_vote != "underdog":
        evidence_side = "unclear"
        method = "dog_rank_form_mixed_h2h"
    elif r_vote == "even" and f_vote == "even" and h_vote in ("even", "abstain"):
        evidence_side = "even"
        method = "all_even"
    elif r_vote == "abstain" and f_vote == "abstain" and h_vote == "abstain":
        evidence_side = "unclear"
        method = "all_abstain"
    else:
        # fallback: highest score
        best = max(scores.items(), key=lambda kv: kv[1])
        if best[1] <= 0:
            evidence_side = "unclear"
            method = "no_votes"
        elif scores["favourite"] > scores["underdog"] + 0.3:
            evidence_side = "favourite"
            method = "score_fav"
        elif scores["underdog"] > scores["favourite"] + 0.3:
            evidence_side = "underdog"
            method = "score_dog"
        elif scores["even"] >= scores["favourite"] and scores["even"] >= scores[
            "underdog"
        ]:
            evidence_side = "even"
            method = "score_even"
        else:
            evidence_side = "unclear"
            method = "score_unclear"

    soft_ud = bool(
        soft_ud_band
        or (
            is_underdog_hc
            and soft_ud_odds_lo <= float(odds) <= soft_ud_odds_hi_hard
        )
    )
    # Outer soft band also treated for side hard rejects on UD HC
    if is_underdog_hc and soft_ud_odds_lo <= float(odds) <= 2.60:
        soft_ud = True

    agrees = (
        (evidence_side == "underdog" and sel_side == "underdog")
        or (evidence_side == "favourite" and sel_side == "favourite")
        or evidence_side in ("natural_over", "natural_under", "n_a")
    )
    conflict = bool(
        sel_side == "underdog"
        and evidence_side == "favourite"
        and soft_ud
    )

    hard_reject = False
    reject_code: str | None = None

    if soft_ud and sel_side == "underdog":
        if evidence_side == "favourite":
            hard_reject = True
            reject_code = "FEH_SIDE_CONFLICT"
            notes.append("soft UD HC vs evidence favourite → FEH_SIDE_CONFLICT")
        elif evidence_side in ("unclear", "even"):
            hard_reject = True
            reject_code = "FEH_SIDE_UNCLEAR_UD"
            notes.append(
                f"soft UD HC with evidence_side={evidence_side} → FEH_SIDE_UNCLEAR_UD"
            )

    # Price-led detection (hard mid-band UD HC)
    price_led = (
        is_underdog_hc
        and soft_ud_odds_lo <= float(odds) <= soft_ud_odds_hi_hard
        and not h2h.get("positive")
        and (r_vote == "favourite" or f_vote == "favourite")
    )
    if price_led and not hard_reject:
        hard_reject = True
        reject_code = "FEH_PRICE_LED_SIDE"
        notes.append("price-led soft UD HC without positive H2H")
        conflict = True

    return SideDecision(
        evidence_side=evidence_side,
        selection_side=sel_side,
        agrees_with_selection=agrees and not conflict,
        conflict=conflict,
        method=method,
        hard_reject=hard_reject,
        reject_code=reject_code,
        notes=notes,
        ranking_vote=r_vote,
        form_vote=f_vote,
        h2h_vote=h_vote,
    )
