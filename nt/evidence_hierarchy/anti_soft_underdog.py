"""Anti-Soft-Underdog gate — Condition A sealed to matchup/H2H only."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from nt.evidence_hierarchy.cards import SportCard
from nt.evidence_hierarchy.checklist import ChecklistAnswers
from nt.evidence_hierarchy.h2h_normalize import normalize_h2h, normalize_strength

# Never satisfy matchup edge alone (design §5 Condition A exclusions)
_EXCLUDED_FROM_A = frozenset(
    {
        "recent_form",
        "form",
        "xg_form",
        "frame_form",
        "checkout_scoring",
        "avg_checkout",
        "format_stage",
        "ranking_seed",
        "ranking_strength",
        "ranking_form",
        "motivation",
        "motivation_context",
        "script_consistency",
        "availability",
        "fitness_fatigue",
        "rest_schedule",
    }
)

# Default allowlist without card flags: h2h_matchup only (design §5 rev 3).
# surface_h2h / underdog_matchup_edge require individual_h2h or counts_for_anti_soft_a.
_DEFAULT_MATCHUP_IDS = frozenset({"h2h_matchup"})


@dataclass
class AntiSoftResult:
    applies: bool
    mode: str  # hard | soft | ""
    band: str  # hard | outer | ""
    condition_a: bool
    condition_b: bool
    condition_c: bool
    condition_d: bool
    failures: list[str] = field(default_factory=list)
    hard_reject: bool = False
    reject_code: str | None = None
    notes: list[str] = field(default_factory=list)
    a_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "applies": self.applies,
            "mode": self.mode,
            "band": self.band,
            "triggered": self.applies and self.hard_reject,
            "condition_a": self.condition_a,
            "condition_b": self.condition_b,
            "condition_c": self.condition_c,
            "condition_d": self.condition_d,
            "failures": list(self.failures),
            "hard_reject": self.hard_reject,
            "reject_code": self.reject_code,
            "notes": list(self.notes),
            "a_sources": list(self.a_sources),
        }


def is_plus_handicap(selection: str) -> bool:
    """True when selection is a +HC line (underdog handicap)."""
    s = selection or ""
    if re.search(r"\+\s*\d", s):
        return True
    # Norwegian style sometimes embeds +2.5 after name
    if re.search(r"\+\d+(?:\.\d+)?", s):
        return True
    return False


def is_minus_handicap(selection: str) -> bool:
    s = selection or ""
    # Prefer explicit minus after handikap/handicap or player
    if re.search(r"handikap|handicap", s, re.I) and re.search(r"-\s*\d", s):
        return True
    if re.search(r"-\d+(?:\.\d+)?", s) and not is_plus_handicap(s):
        return True
    return False


def is_handicap_family(selection: str, family: str = "") -> bool:
    if family == "handicap":
        return True
    s = (selection or "").lower()
    return bool(re.search(r"handikap|handicap|\+\d|-\d", s))


def matchup_eligible_factor_ids(card: SportCard | None) -> set[str]:
    """Factor ids that may satisfy anti-soft condition A."""
    out: set[str] = set(_DEFAULT_MATCHUP_IDS)
    if card is None:
        return out
    for f in card.all_factors():
        fid = str(f.get("id") or "")
        if not fid or fid in _EXCLUDED_FROM_A:
            continue
        if f.get("individual_h2h") or f.get("counts_for_anti_soft_a"):
            out.add(fid)
        # aliases that map to matchup slots
    # Also honour aliases pointing to matchup slots
    for alias, stable in (card.signal_id_aliases or {}).items():
        if stable in out:
            out.add(str(alias))
    # Remove explicit exclusions even if mis-flagged
    out -= _EXCLUDED_FROM_A
    return out


def matchup_eligible_signals(
    ev: dict[str, Any],
    card: SportCard | None,
) -> list[tuple[str, dict[str, Any]]]:
    """Yield (slot_id, signal_dict) for matchup-eligible filled signals."""
    eligible = matchup_eligible_factor_ids(card)
    signals = ev.get("signals") if isinstance(ev.get("signals"), dict) else {}
    out: list[tuple[str, dict[str, Any]]] = []
    for sid, sig in signals.items():
        if not isinstance(sig, dict) or not sig.get("filled"):
            continue
        # resolve alias → stable
        stable = sid
        if card is not None:
            stable = card.resolve_signal_id(str(sid))
        if stable in _EXCLUDED_FROM_A or str(sid) in _EXCLUDED_FROM_A:
            continue
        if stable in eligible or str(sid) in eligible:
            out.append((str(stable), sig))
    return out


def anti_soft_condition_a(
    ev: dict[str, Any],
    card: SportCard | None,
    checklist: ChecklistAnswers,
    h2h: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Condition A — sealed: positive H2H OR matchup-eligible slot only.

    Ranking favours favourite + H2H not positive → A false even if a
    mis-flagged slot were positive.
    """
    sources: list[str] = []
    if h2h.get("positive"):
        sources.append("h2h.positive")
        return True, sources

    for slot_id, sig in matchup_eligible_signals(ev, card):
        _num, pol = normalize_strength(sig.get("strength"))
        if pol == "positive":
            # Rank fav + no positive H2H → seal forces A false
            if (
                checklist.higher_ranked_side
                in ("favourite", "home", "player_a")
                and float(checklist.ranking_confidence or 0) >= 0.5
            ):
                sources.append(f"{slot_id}:positive_but_rank_fav_seal")
                return False, sources
            sources.append(f"{slot_id}:positive")
            return True, sources

    return False, sources


def anti_soft_condition_b(checklist: ChecklistAnswers) -> bool:
    """Form does NOT clearly favour favourite (Q2 lean ≠ favourite at conf≥0.5)."""
    if (
        checklist.better_form_side in ("favourite", "home", "player_a")
        and float(checklist.form_confidence or 0) >= 0.5
    ):
        return False
    return True


def _opposite_side_markers(
    *,
    selection: str = "",
    match: str = "",
) -> tuple[str, ...]:
    """Generic opposite-side markers; optional opponent tokens from match string."""
    base = (
        "favourite",
        "favorite",
        "fav ",
        " opposite",
        "other side",
        "instead of",
        "rather than",
        "not the",
        "chalk",
        "shorter price",
        "shorter odds",
        "minus line",
        "minus hc",
        "against the",
        "over the fav",
        "than the fav",
        "-1.5",
        "-2.5",
        "-3.5",
        "-4.5",
        "-5.5",
    )
    extra: list[str] = []
    # If match is "A vs B" and selection names one side, the other name is opposite
    m = (match or "").strip()
    sel_l = (selection or "").lower()
    if " vs " in m.lower() or " v " in m.lower():
        parts = re.split(r"\s+vs\.?\s+|\s+v\.?\s+", m, maxsplit=1, flags=re.I)
        if len(parts) == 2:
            for side in parts:
                # strip ranking commas "Smith, Ross" → tokens
                tokens = [
                    t.strip().lower()
                    for t in re.split(r"[,/]", side)
                    if len(t.strip()) >= 4
                ]
                for tok in tokens:
                    if tok and tok not in sel_l:
                        extra.append(tok)
    return base + tuple(extra)


def anti_soft_condition_c(
    checklist: ChecklistAnswers,
    *,
    selection: str = "",
    match: str = "",
) -> bool:
    """Why-side text ≥40 chars and mentions opposite side (not odds 'price' alone)."""
    why = (checklist.why_this_side_not_opposite or "").strip()
    if len(why) < 40:
        return False
    lower = why.lower()
    markers = _opposite_side_markers(selection=selection, match=match)
    return any(m in lower for m in markers)


def anti_soft_condition_d(
    checklist: ChecklistAnswers,
    *,
    condition_a: bool,
) -> bool:
    """
    Ranking not heavy favourite unless A true and why-side documents the rank gap.
    Q1 lean ≠ favourite at conf≥0.7, OR (A ∧ documented).
    """
    heavy_fav = (
        checklist.higher_ranked_side in ("favourite", "home", "player_a")
        and float(checklist.ranking_confidence or 0) >= 0.7
    )
    if not heavy_fav:
        return True
    if not condition_a:
        return False
    why = (checklist.why_this_side_not_opposite or "").lower()
    documented = any(
        tok in why
        for tok in (
            "rank",
            "seed",
            "higher",
            "favourite",
            "favorite",
            "gap",
            "despite",
        )
    )
    return documented


def anti_soft_applies(
    *,
    selection: str,
    odds: float,
    family: str,
    individual_sport: bool,
    soft_ud_odds_lo: float = 1.70,
    soft_ud_odds_hi_hard: float = 2.20,
    soft_ud_odds_hi_soft: float = 2.60,
    anti_soft_ml_dogs_individual: bool = True,
    anti_soft_ml_dogs_team: bool = False,
) -> tuple[bool, str, str]:
    """
    Returns (applies, mode, band).

    HC +plus mid/outer band → applies hard.
    Fav HC → never.
    ML dog mid → applies iff individual sport config.
    """
    o = float(odds)
    is_hc = is_handicap_family(selection, family)
    if is_hc:
        if is_minus_handicap(selection) and not is_plus_handicap(selection):
            return False, "", ""
        if not is_plus_handicap(selection):
            # handicap without clear plus → treat as non-soft for anti-soft
            return False, "", ""
        if soft_ud_odds_lo <= o <= soft_ud_odds_hi_hard:
            return True, "hard", "hard"
        if soft_ud_odds_hi_hard < o <= soft_ud_odds_hi_soft:
            return True, "hard", "outer"
        return False, "", ""

    # ML dogs
    if family == "ml" or re.search(
        r"vinner|to win|winner|\bml\b|moneyline", (selection or "").lower()
    ):
        if o < soft_ud_odds_lo or o > soft_ud_odds_hi_soft:
            return False, "", ""
        if individual_sport and anti_soft_ml_dogs_individual:
            band = "hard" if o <= soft_ud_odds_hi_hard else "outer"
            return True, "hard", band
        if (not individual_sport) and anti_soft_ml_dogs_team:
            band = "hard" if o <= soft_ud_odds_hi_hard else "outer"
            return True, "hard", band
        return False, "", ""

    return False, "", ""


def evaluate_anti_soft_underdog(
    ev: dict[str, Any] | None,
    checklist: ChecklistAnswers,
    h2h: dict[str, Any] | None = None,
    *,
    card: SportCard | None = None,
    selection: str = "",
    odds: float = 2.0,
    family: str = "",
    soft_ud_odds_lo: float = 1.70,
    soft_ud_odds_hi_hard: float = 2.20,
    soft_ud_odds_hi_soft: float = 2.60,
    anti_soft_ml_dogs_individual: bool = True,
    anti_soft_ml_dogs_team: bool = False,
    allow_soft_ud_grade_c: bool = False,
    enabled: bool = True,
) -> AntiSoftResult:
    """Full anti-soft evaluation. Fail any of A–D → hard reject FEH_ANTI_SOFT_UNDERDOG."""
    ev = ev or {}
    sel = selection or str(ev.get("selection") or "")
    individual = bool(card.individual_sport) if card is not None else False

    if not enabled:
        return AntiSoftResult(
            applies=False,
            mode="",
            band="",
            condition_a=False,
            condition_b=False,
            condition_c=False,
            condition_d=False,
            notes=["anti_soft disabled"],
        )

    if h2h is None:
        h2h = normalize_h2h(ev).to_dict()

    applies, mode, band = anti_soft_applies(
        selection=sel,
        odds=float(odds),
        family=family,
        individual_sport=individual,
        soft_ud_odds_lo=soft_ud_odds_lo,
        soft_ud_odds_hi_hard=soft_ud_odds_hi_hard,
        soft_ud_odds_hi_soft=soft_ud_odds_hi_soft,
        anti_soft_ml_dogs_individual=anti_soft_ml_dogs_individual,
        anti_soft_ml_dogs_team=anti_soft_ml_dogs_team,
    )
    if not applies:
        return AntiSoftResult(
            applies=False,
            mode="",
            band="",
            condition_a=False,
            condition_b=False,
            condition_c=False,
            condition_d=False,
            notes=["anti_soft does not apply"],
        )

    a, a_sources = anti_soft_condition_a(ev, card, checklist, h2h)
    b = anti_soft_condition_b(checklist)
    c = anti_soft_condition_c(
        checklist,
        selection=sel,
        match=str(ev.get("match") or ""),
    )
    d = anti_soft_condition_d(checklist, condition_a=a)

    failures: list[str] = []
    if not a:
        failures.append("A")
    if not b:
        failures.append("B")
    if not c:
        failures.append("C")
    if not d:
        failures.append("D")

    # Design: fail any of A–D → hard F. allow_soft_ud_grade_c is intentionally
    # ignored (no Grade-C escape for soft UD mid-band); kept for config compat.
    _ = allow_soft_ud_grade_c
    hard = bool(failures)

    notes = [f"anti_soft band={band} mode={mode}"]
    if a_sources:
        notes.append("a_sources=" + ",".join(a_sources))
    if failures:
        notes.append("failures=" + ",".join(failures))

    return AntiSoftResult(
        applies=True,
        mode=mode or "hard",
        band=band,
        condition_a=a,
        condition_b=b,
        condition_c=c,
        condition_d=d,
        failures=failures,
        hard_reject=hard,
        reject_code="FEH_ANTI_SOFT_UNDERDOG" if hard else None,
        notes=notes,
        a_sources=a_sources,
    )
