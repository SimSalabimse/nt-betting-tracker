"""Natural Market Elevation — card-driven triggers + N/A when absent from board."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from nt.evidence_hierarchy.anti_soft_underdog import is_plus_handicap
from nt.evidence_hierarchy.cards import SportCard
from nt.evidence_hierarchy.checklist import ChecklistAnswers

REJECT_UNEVALUATED = "FEH_NATURAL_MARKET_UNEVALUATED"

# Generic dual-high / long-format trigger tokens (pack flags + free text)
_TRIGGER_ALIASES: dict[str, tuple[str, ...]] = {
    "dual_high_scoring": (
        "dual_high_scoring",
        "dual_high_180",
        "dual_high",
        "both high",
        "high averages both",
        "both players high",
        "both high avg",
        "high scoring both",
    ),
    "high_checkout_both": (
        "high_checkout_both",
        "both checkout",
        "checkout both",
        "high checkout both",
    ),
    "dual_high_180": (
        "dual_high_180",
        "both 180",
        "180s both",
        "high 180",
    ),
    "long_format": (
        "long_format",
        "long format",
        "long legs",
        "best of 3",
        "best of 5",
        "bo11",
        "bo13",
        "bo15",
        "bo31",
        "matchplay",
    ),
}


@dataclass
class NaturalMarketEval:
    required: bool = False
    candidates: list[str] = field(default_factory=list)
    evaluated: list[str] = field(default_factory=list)
    missing_on_board: list[str] = field(default_factory=list)
    comparison_vs_hc: str = ""
    preferred_market: str | None = None
    hard_reject: bool = False
    reject_code: str | None = None
    status: str = "n_a"  # n_a | disabled | required_ok | unevaluated | no_trigger
    triggers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "candidates": list(self.candidates),
            "evaluated": list(self.evaluated),
            "missing_on_board": list(self.missing_on_board),
            "comparison_vs_hc": self.comparison_vs_hc,
            "preferred_market": self.preferred_market,
            "hard_reject": self.hard_reject,
            "reject_code": self.reject_code,
            "status": self.status,
            "triggers": list(self.triggers),
            "notes": list(self.notes)[:8],
        }


def _card_natural_entries(card: SportCard | None) -> list[dict[str, Any]]:
    if card is None:
        return []
    raw = getattr(card, "natural_markets", None) or []
    return [dict(x) for x in raw if isinstance(x, dict)]


def _pack_text_blob(ev: dict[str, Any] | None) -> str:
    if not ev:
        return ""
    parts: list[str] = [
        str(ev.get("summary") or ""),
        str(ev.get("notes") or ""),
        str(ev.get("failure_modes") or ""),
        str(ev.get("script_lean") or ""),
    ]
    flags = ev.get("profile_flags") or []
    if isinstance(flags, (list, tuple)):
        parts.extend(str(x) for x in flags)
    signals = ev.get("signals") if isinstance(ev.get("signals"), dict) else {}
    for sid, sig in signals.items():
        if not isinstance(sig, dict):
            continue
        parts.append(str(sid))
        parts.append(str(sig.get("note") or ""))
        parts.append(str(sig.get("strength") or ""))
    cl = ev.get("checklist") if isinstance(ev.get("checklist"), dict) else {}
    parts.append(str(cl.get("natural_market_hint") or ""))
    for m in cl.get("natural_markets") or []:
        parts.append(str(m))
    return " ".join(parts).lower()


def detect_triggers(
    ev: dict[str, Any] | None,
    card: SportCard | None,
    checklist: ChecklistAnswers | None = None,
) -> list[str]:
    """
    Card-driven + pack fields:
      - signals.checkout_scoring / averages text mentioning both players high 180/avg
      - checklist.natural_markets non-empty (not only 'none')
      - explicit pack.profile_flags: ["dual_high_180", ...]
      - card natural_markets.trigger_when tokens matched in pack text/flags
    """
    found: list[str] = []
    seen: set[str] = set()

    def _add(tid: str) -> None:
        t = str(tid or "").strip()
        if t and t not in seen:
            seen.add(t)
            found.append(t)

    # Explicit pack profile flags
    flags = (ev or {}).get("profile_flags") or []
    if isinstance(flags, (list, tuple)):
        for f in flags:
            fl = str(f).strip().lower()
            if not fl or fl in ("none", "n/a", "na"):
                continue
            _add(fl)
            for canon, aliases in _TRIGGER_ALIASES.items():
                if fl == canon or fl in aliases or any(a in fl for a in aliases):
                    _add(canon)

    # Checklist natural markets (Q4) — non-empty and not none-only
    nm_list: list[str] = []
    if checklist is not None:
        nm_list = [str(x).strip() for x in (checklist.natural_markets or []) if str(x).strip()]
        hint = (checklist.natural_market_hint or "").strip()
        if hint and hint.lower() not in ("none", "n/a", "na", ""):
            _add("checklist_natural_hint")
    else:
        raw_cl = (ev or {}).get("checklist") if isinstance((ev or {}).get("checklist"), dict) else {}
        nm_list = [str(x).strip() for x in (raw_cl.get("natural_markets") or []) if str(x).strip()]
    meaningful = [m for m in nm_list if m.lower() not in ("none", "n/a", "na", "")]
    if meaningful:
        _add("checklist_natural_markets")
        for m in meaningful:
            _add(f"checklist:{m.lower()}")

    blob = _pack_text_blob(ev)

    # Card-declared trigger tokens
    for entry in _card_natural_entries(card):
        for tw in entry.get("trigger_when") or []:
            key = str(tw).strip().lower()
            if not key:
                continue
            aliases = _TRIGGER_ALIASES.get(key, (key,))
            if any(a in blob for a in aliases) or key in blob:
                _add(key)

    # Heuristic dual-high / checkout both from checkout_scoring signal
    signals = (ev or {}).get("signals") if isinstance((ev or {}).get("signals"), dict) else {}
    checkout = signals.get("checkout_scoring") or signals.get("avg_checkout") or {}
    if isinstance(checkout, dict) and checkout.get("filled"):
        note = str(checkout.get("note") or "").lower()
        strength = str(checkout.get("strength") or "").lower()
        if any(
            tok in note
            for tok in (
                "both",
                "dual",
                "high avg",
                "high average",
                "180",
                "long format",
                "long legs",
                "matchplay",
            )
        ) or strength == "positive":
            # positive checkout alone is weak; require dual language or dual flag already
            if any(tok in note for tok in ("both", "dual", "each", "two players", "high")):
                _add("dual_high_scoring")
                _add("high_checkout_both")

    # Long format from format_stage
    fmt = signals.get("format_stage") or {}
    if isinstance(fmt, dict) and fmt.get("filled"):
        note = str(fmt.get("note") or "").lower()
        if any(tok in note for tok in ("long", "matchplay", "bo1", "bo3", "legs", "deep")):
            _add("long_format")

    return found


def _selection_family_tags(selection: str, family: str = "") -> set[str]:
    tags: set[str] = set()
    fam = (family or "").strip().lower()
    if fam:
        tags.add(fam)
    if is_plus_handicap(selection):
        tags.add("underdog_hc")
        tags.add("handicap")
    sel = (selection or "").lower()
    if re.search(r"handikap|handicap|\+\d|-\d", sel):
        tags.add("handicap")
    if re.search(r"over\s*\d|under\s*\d|totalt|total", sel):
        tags.add("totals")
    return tags


def _patterns_match(text: str, patterns: list[str]) -> bool:
    t = (text or "").lower()
    for p in patterns:
        pl = str(p).strip().lower()
        if not pl:
            continue
        if pl in t:
            return True
        # loose digit-aware: "over 27.5" vs "over_27_5"
        compact = re.sub(r"[\s_\-]+", "", pl)
        t_compact = re.sub(r"[\s_\-]+", "", t)
        if compact and compact in t_compact:
            return True
    return False


def _row_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(k) or "")
        for k in ("selection", "market", "market_type", "line", "name", "match")
    ).lower()


def _sibling_text(sib: dict[str, Any]) -> str:
    return " ".join(
        [
            str(sib.get("selection") or ""),
            str(sib.get("summary") or ""),
            str(sib.get("match") or ""),
        ]
    ).lower()


def _pack_eval_payload(pack: dict[str, Any] | None) -> tuple[list[str], str]:
    """Return (evaluated_ids, comparison_text) from pack natural_market fields."""
    if not pack:
        return [], ""
    nme = pack.get("natural_market_eval")
    evaluated: list[str] = []
    comparison = ""
    if isinstance(nme, dict):
        evaluated = [str(x).strip() for x in (nme.get("evaluated") or []) if str(x).strip()]
        comparison = str(nme.get("comparison_vs_hc") or nme.get("comparison") or "")
    if not comparison:
        comparison = str(
            pack.get("natural_market_comparison")
            or pack.get("natural_comparison")
            or ""
        )
    # checklist natural markets already named as evaluated labels when comparison long
    return evaluated, comparison.strip()


def evaluate_natural_markets(
    *,
    triggers: list[str] | None = None,
    pack: dict[str, Any] | None = None,
    selection: str = "",
    family: str = "",
    card: SportCard | None = None,
    checklist: ChecklistAnswers | None = None,
    odds_rows: list[dict[str, Any]] | None = None,
    sibling_packs: list[dict[str, Any]] | None = None,
    enabled: bool = True,
    soft_ud_hc: bool = False,
    min_comparison_chars: int = 40,
) -> NaturalMarketEval:
    """
    Natural market elevation gate.

    N/A rules:
      - candidate not on board and no sibling pack → missing_on_board; does not fail
      - trigger + (on board OR sibling) but no evaluation/comparison → hard reject
        on soft underdog HC (FEH_NATURAL_MARKET_UNEVALUATED)
      - in-pack evaluation / comparison ≥ min_comparison_chars is enough
    """
    if not enabled:
        return NaturalMarketEval(
            required=False,
            status="disabled",
            notes=["natural_market_elevation disabled"],
        )

    trig = list(triggers) if triggers is not None else detect_triggers(pack, card, checklist)
    entries = _card_natural_entries(card)

    # Default darts-style candidate when card has no natural_markets but dual-high fired
    if not entries and any(
        t in ("dual_high_scoring", "high_checkout_both", "dual_high_180", "long_format")
        or str(t).startswith("checklist:")
        for t in trig
    ):
        entries = [
            {
                "id": "over_legs_high",
                "trigger_when": [
                    "dual_high_scoring",
                    "high_checkout_both",
                    "dual_high_180",
                    "long_format",
                    "checklist_natural_markets",
                ],
                "selection_patterns": [
                    "totalt antall runder",
                    "over 27.5",
                    "over 27",
                    "runder 27",
                ],
                "require_eval_on": ["underdog_hc", "handicap"],
            }
        ]

    if not trig:
        return NaturalMarketEval(
            required=False,
            status="no_trigger",
            triggers=[],
            notes=["no natural market triggers"],
        )

    fam_tags = _selection_family_tags(selection, family)
    evaluated_labels, comparison = _pack_eval_payload(pack)
    # Also treat long comparison as covering any candidate that patterns match it
    if comparison and len(comparison) >= min_comparison_chars:
        # keep comparison; candidates matched below may use it
        pass

    candidates: list[str] = []
    require_eval = False
    matched_entries: list[dict[str, Any]] = []

    for entry in entries:
        tw = [str(x).strip().lower() for x in (entry.get("trigger_when") or []) if str(x).strip()]
        # Fire if any declared trigger is present, or any trigger if none declared
        if tw:
            # checklist_natural_markets / hint count as soft match for any entry
            soft_trig = {
                "checklist_natural_markets",
                "checklist_natural_hint",
            }
            if not (
                any(t in trig for t in tw)
                or any(t in soft_trig for t in trig)
                or any(str(t).startswith("checklist:") for t in trig)
            ):
                continue
        else:
            # no trigger_when → any trigger activates entry
            pass
        cid = str(entry.get("id") or "natural")
        candidates.append(cid)
        matched_entries.append(entry)
        req_on = {
            str(x).strip().lower()
            for x in (entry.get("require_eval_on") or ["underdog_hc", "handicap"])
            if str(x).strip()
        }
        if fam_tags & req_on:
            require_eval = True

    if not candidates:
        return NaturalMarketEval(
            required=False,
            status="no_trigger",
            triggers=list(trig),
            notes=["triggers present but no card candidates matched"],
        )

    # Presence: odds board rows and sibling packs
    on_board: set[str] = set()
    via_sibling: set[str] = set()
    evaluated: list[str] = list(evaluated_labels)

    for entry, cid in zip(matched_entries, candidates):
        patterns = [str(p) for p in (entry.get("selection_patterns") or []) if str(p).strip()]
        # Explicit evaluated labels matching id or patterns
        for lab in evaluated_labels:
            if lab == cid or _patterns_match(lab, patterns + [cid]):
                if cid not in evaluated:
                    evaluated.append(cid)
        # Comparison text covers candidate
        if comparison and len(comparison) >= min_comparison_chars:
            if not patterns or _patterns_match(comparison, patterns + [cid]):
                if cid not in evaluated:
                    evaluated.append(cid)

        # Board presence
        for row in odds_rows or []:
            if not isinstance(row, dict):
                continue
            if _patterns_match(_row_text(row), patterns):
                on_board.add(cid)
                break

        # Sibling pack presence (+ may supply evaluation via summary ≥40 chars)
        for sib in sibling_packs or []:
            if not isinstance(sib, dict):
                continue
            st = _sibling_text(sib)
            if not patterns or _patterns_match(st, patterns):
                via_sibling.add(cid)
                summary = str(sib.get("summary") or "")
                # Sibling pack with substantial summary can count as evaluated evidence
                if len(summary) >= min_comparison_chars:
                    # Only if pack references sibling or comparison mentions it —
                    # design: "Sibling pack can supply evaluated evidence via reference"
                    # For fail path: sibling present without HC pack evaluation → unevaluated.
                    # So sibling alone does NOT mark evaluated unless pack references it.
                    pack_blob = _pack_text_blob(pack) + " " + comparison.lower()
                    ref_tokens = patterns + [cid, "natural", "total", "over", "sibling"]
                    if comparison and len(comparison) >= min_comparison_chars:
                        if cid not in evaluated:
                            evaluated.append(cid)
                    elif any(tok.lower() in pack_blob for tok in ref_tokens if len(tok) >= 4):
                        # soft reference without full comparison — still need comparison
                        pass
                break

    missing_on_board: list[str] = []
    present_unevaluated: list[str] = []
    for cid in candidates:
        present = cid in on_board or cid in via_sibling
        # If neither board nor sibling known (no discovery context), treat as N/A
        if odds_rows is None and sibling_packs is None:
            # No board context → cannot prove presence; N/A not fail
            missing_on_board.append(cid)
            continue
        if not present:
            missing_on_board.append(cid)
            continue
        if cid not in evaluated:
            present_unevaluated.append(cid)

    # required only on soft UD HC (or when require_eval_on matched and soft_ud_hc)
    required = bool(require_eval and soft_ud_hc and present_unevaluated)

    # If candidates present but unevaluated and soft UD → hard reject
    hard = False
    code: str | None = None
    status = "required_ok"
    notes: list[str] = []

    if present_unevaluated and soft_ud_hc and require_eval:
        hard = True
        code = REJECT_UNEVALUATED
        status = "unevaluated"
        notes.append(
            "natural markets present on board/sibling but unevaluated: "
            + ",".join(present_unevaluated)
        )
        required = True
    elif not candidates:
        status = "no_trigger"
    elif missing_on_board and not present_unevaluated and not evaluated:
        status = "n_a"
        notes.append("natural candidates missing on board → N/A")
        required = False
    elif evaluated and not present_unevaluated:
        status = "required_ok"
        notes.append("natural markets evaluated: " + ",".join(evaluated[:4]))
        required = bool(require_eval and soft_ud_hc)
    else:
        status = "n_a"
        notes.append("natural market N/A or not required")

    preferred = evaluated[0] if evaluated else (candidates[0] if candidates else None)

    return NaturalMarketEval(
        required=required or hard,
        candidates=candidates,
        evaluated=evaluated,
        missing_on_board=missing_on_board,
        comparison_vs_hc=comparison,
        preferred_market=preferred,
        hard_reject=hard,
        reject_code=code,
        status=status,
        triggers=list(trig),
        notes=notes,
    )


__all__ = [
    "NaturalMarketEval",
    "REJECT_UNEVALUATED",
    "detect_triggers",
    "evaluate_natural_markets",
]
