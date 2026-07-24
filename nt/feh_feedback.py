"""
FEH settlement feedback — soft-underdog loss pattern tags + safe variance lean.

Design (PR5):
1. Always append pattern tag to feh_feedback.jsonl when a **Loss** matches
   soft-UD HC + favourite rank/form heuristic (from notes/selection/pack).
2. Set variance_class lean ``research_process_miss`` **only if** FEH audit on
   the linked pack proves anti-soft / checklist gate should have fired.
3. Legacy bets without FEH: pattern tag only — never invent process_error or
   learning stake mults from a guess.
4. Does not touch capital_v2 / phase / secure.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from nt.bets_io import utc_now
from nt.config import path_from_config
from nt.paths import resolve

SCHEMA_VERSION = 1
DEFAULT_FEEDBACK_REL = "data/state/feh_feedback.jsonl"
PATTERN_SOFT_UD_FAV_FORM = "soft_ud_loss_fav_rank_form"

_FAV_LEAN_RE = re.compile(
    r"\b("
    r"fav(?:ourite|orite)?\s+(?:form|rank|ranking|seed)|"
    r"(?:higher|better)\s+rank|"
    r"rank(?:ing)?\s*(?:fav|gap|advantage)|"
    r"form\s*(?:fav|edge|advantage)|"
    r"seed\s*(?:fav|edge)|"
    r"ranking_seed|higher_ranked|better_form|"
    r"FEH_ANTI_SOFT|anti[_\s-]?soft"
    r")\b",
    re.I,
)
_DOG_HC_RE = re.compile(r"\+\s*\d+(?:\.\d+)?")


def feedback_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    if isinstance(cfg, dict):
        sel = cfg.get("selection") or {}
        if isinstance(sel, dict):
            raw = dict(sel.get("feh_feedback") or {})
        # allow top-level too
        if not raw and cfg.get("feh_feedback"):
            raw = dict(cfg.get("feh_feedback") or {})
    return {
        "enabled": bool(raw.get("enabled", True)),
        "jsonl": str(raw.get("jsonl") or DEFAULT_FEEDBACK_REL),
        "soft_ud_odds_lo": float(raw.get("soft_ud_odds_lo") or 1.70),
        "soft_ud_odds_hi": float(raw.get("soft_ud_odds_hi") or 2.60),
        "lean_process_miss": bool(raw.get("lean_process_miss", True)),
    }


def feedback_path(cfg: dict[str, Any] | None) -> Path:
    fc = feedback_cfg(cfg)
    if isinstance(cfg, dict):
        paths = cfg.get("paths") or {}
        if paths.get("feh_feedback_jsonl"):
            return path_from_config(cfg, "feh_feedback_jsonl")
        if paths.get("state_dir") and fc["jsonl"] in (
            DEFAULT_FEEDBACK_REL,
            "feh_feedback.jsonl",
        ):
            return path_from_config(cfg, "state_dir") / "feh_feedback.jsonl"
    rel = fc["jsonl"]
    p = Path(rel)
    return p if p.is_absolute() else resolve(rel)


def is_plus_handicap_selection(selection: str) -> bool:
    try:
        from nt.evidence_hierarchy.anti_soft_underdog import is_plus_handicap

        return bool(is_plus_handicap(selection))
    except Exception:
        return bool(_DOG_HC_RE.search(selection or ""))


def is_soft_underdog_hc(
    selection: str,
    odds: float | None,
    *,
    odds_lo: float = 1.70,
    odds_hi: float = 2.60,
) -> bool:
    if not is_plus_handicap_selection(selection):
        return False
    if odds is None:
        return True  # shape match without odds still tags for audit
    try:
        o = float(odds)
    except (TypeError, ValueError):
        return True
    return odds_lo <= o <= odds_hi


def _as_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def fav_rank_form_heuristic(
    *,
    notes: str = "",
    selection: str = "",
    issues: Any = None,
    feh_audit: dict[str, Any] | None = None,
    checklist: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """
    True when favourite rank/form looks stronger than the soft underdog side.

    Safe lean sources (any one is enough for *pattern tag*):
    - FEH checklist Q1/Q2 lean favourite
    - free-text notes/issues mentioning fav rank/form / anti-soft
    - FEH reject codes / anti_soft applies
    """
    reasons: list[str] = []
    cl = checklist
    if cl is None and isinstance(feh_audit, dict):
        raw_cl = feh_audit.get("checklist")
        if isinstance(raw_cl, dict):
            cl = raw_cl

    if isinstance(cl, dict):
        rank = str(cl.get("higher_ranked_side") or "").lower()
        form = str(cl.get("better_form_side") or "").lower()
        if rank in ("favourite", "fav", "favorite", "favoured", "favored"):
            reasons.append("checklist:higher_ranked_side=favourite")
        if form in ("favourite", "fav", "favorite", "favoured", "favored"):
            reasons.append("checklist:better_form_side=favourite")

    if isinstance(feh_audit, dict):
        codes = [str(c) for c in (feh_audit.get("reject_codes") or [])]
        if any("ANTI_SOFT" in c or "SIDE_CONFLICT" in c or "SIDE_UNCLEAR" in c for c in codes):
            reasons.append("feh_reject:" + ",".join(codes[:4]))
        anti = feh_audit.get("anti_soft_underdog")
        if isinstance(anti, dict) and anti.get("applies"):
            reasons.append("anti_soft.applies")
        if feh_audit.get("checklist_complete") is False:
            reasons.append("checklist_incomplete")

    blob_parts = [notes or "", selection or ""]
    if isinstance(issues, (list, tuple)):
        blob_parts.extend(str(x) for x in issues)
    elif issues:
        blob_parts.append(str(issues))
    blob = " ".join(blob_parts)
    if _FAV_LEAN_RE.search(blob):
        reasons.append("notes_heuristic:fav_rank_form")

    return (len(reasons) > 0, reasons)


def should_tag_soft_ud_loss(
    bet: dict[str, Any],
    *,
    result: str | None = None,
    cfg: dict[str, Any] | None = None,
    feh_audit: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Return (match, meta) for soft-UD + fav rank/form loss pattern."""
    fc = feedback_cfg(cfg)
    res = str(result if result is not None else bet.get("result") or "").strip()
    if res.lower() not in ("loss", "l"):
        return False, {"skip": "not_loss"}

    selection = str(bet.get("selection") or "")
    odds = _as_float(bet.get("decimal_odds") if bet.get("decimal_odds") is not None else bet.get("odds"))
    soft = is_soft_underdog_hc(
        selection,
        odds,
        odds_lo=float(fc["soft_ud_odds_lo"]),
        odds_hi=float(fc["soft_ud_odds_hi"]),
    )
    if not soft:
        return False, {"skip": "not_soft_ud_hc"}

    notes = str(bet.get("notes") or "")
    hit, reasons = fav_rank_form_heuristic(
        notes=notes,
        selection=selection,
        issues=bet.get("issues"),
        feh_audit=feh_audit or bet.get("feh") or bet.get("feh_audit"),
    )
    if not hit:
        return False, {"skip": "no_fav_rank_form_signal", "soft_ud": True}

    return True, {
        "pattern": PATTERN_SOFT_UD_FAV_FORM,
        "reasons": reasons,
        "selection": selection,
        "odds": odds,
        "soft_ud": True,
    }


# FEH-owned reject classes that justify research_process_miss lean (not SAEF-only F)
_FEH_OWNED_CODES = frozenset(
    {
        "FEH_CHECKLIST_INCOMPLETE",
        "FEH_SIDE_CONFLICT",
        "FEH_SIDE_UNCLEAR_UD",
        "FEH_PRICE_LED_SIDE",
        "FEH_ANTI_SOFT_UNDERDOG",
        "FEH_NATURAL_MARKET_UNEVALUATED",
        "FEH_QUARANTINE_SPORT",
        "FEH_ERROR",
    }
)


def feh_proves_process_miss(
    feh_audit: dict[str, Any] | None,
    *,
    evidence: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
    selection: str = "",
    odds: float | None = None,
    sport: str = "",
) -> tuple[bool, list[str]]:
    """
    True only when FEH audit proves gate should have blocked place.

    Proof requires at least one of:
    - FEH-owned reject codes (FEH_ANTI_SOFT_UNDERDOG, checklist, side, natural, …)
    - anti_soft_underdog.triggered / hard_reject
    - checklist_complete is False

    Bare ``final_grade_suggestion == "F"`` or generic hard_reject **without**
    FEH-owned codes is **not** proof (avoids SAEF-only / EV noise lean).
    Live recompute that yields FEH-owned codes still counts.

    Never true from free-text guess alone.
    """
    proofs: list[str] = []
    audit = feh_audit if isinstance(feh_audit, dict) else None

    if audit is None and evidence is not None:
        try:
            from nt.evidence_hierarchy.feh import run_forced_evidence_hierarchy

            result = run_forced_evidence_hierarchy(
                evidence,
                sport=sport or str(evidence.get("sport") or ""),
                selection=selection or str(evidence.get("selection") or ""),
                odds=float(odds or evidence.get("decimal_odds") or 1.85),
                cfg=cfg,
                run_saef=True,
            )
            audit = result.to_audit()
        except Exception as exc:  # noqa: BLE001
            return False, [f"feh_recompute_error:{exc}"]

    if not isinstance(audit, dict) or not audit:
        return False, []

    codes = {str(c) for c in (audit.get("reject_codes") or []) if str(c).strip()}
    owned = codes & _FEH_OWNED_CODES
    if owned:
        proofs.append("feh_codes:" + ",".join(sorted(owned)[:6]))

    if audit.get("checklist_complete") is False:
        proofs.append("checklist_incomplete")

    anti = audit.get("anti_soft_underdog")
    if isinstance(anti, dict) and (
        anti.get("hard_reject") or anti.get("triggered")
    ):
        fails = ",".join(str(x) for x in (anti.get("failures") or [])[:4])
        proofs.append("anti_soft_triggered" + (f":{fails}" if fails else ""))

    # Explicit: bare grade F / hard_reject without FEH-owned signal is NOT proof
    # (SAEF-only reject_codes or empty codes + final_grade_suggestion F → no lean)

    return (len(proofs) > 0, proofs)


def append_feh_feedback(
    cfg: dict[str, Any] | None,
    record: dict[str, Any],
) -> Path | None:
    """Append one feedback JSONL line. Soft-fail → None."""
    try:
        fc = feedback_cfg(cfg)
        if not fc.get("enabled", True):
            return None
        path = feedback_path(cfg)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ts": utc_now(),
            **record,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        return path
    except Exception:
        return None


def process_settlement_feh_feedback(
    cfg: dict[str, Any] | None,
    bet: dict[str, Any],
    *,
    result: str | None = None,
    packet: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
    feh_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Main settle hook.

    Returns meta dict:
      tagged, pattern, variance_lean, lean_applied, path, reasons, proofs
    """
    fc = feedback_cfg(cfg)
    out: dict[str, Any] = {
        "tagged": False,
        "pattern": None,
        "variance_lean": None,
        "lean_applied": False,
        "path": None,
        "reasons": [],
        "proofs": [],
    }
    if not fc.get("enabled", True):
        out["skip"] = "disabled"
        return out

    res = str(result if result is not None else bet.get("result") or "")
    audit = feh_audit
    if audit is None:
        audit = bet.get("feh") if isinstance(bet.get("feh"), dict) else None
    if audit is None and isinstance(packet, dict):
        audit = packet.get("feh") if isinstance(packet.get("feh"), dict) else None

    # Optional: recompute from evidence path on bet
    if audit is None and evidence is None:
        epath = str(bet.get("evidence_path") or "").strip()
        if epath:
            try:
                from nt.paths import resolve as _resolve

                p = Path(epath)
                if not p.is_file():
                    p = _resolve(epath)
                if p.is_file():
                    evidence = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                evidence = None

    match, meta = should_tag_soft_ud_loss(
        bet, result=res, cfg=cfg, feh_audit=audit
    )
    if not match:
        out.update(meta)
        return out

    out["tagged"] = True
    out["pattern"] = meta.get("pattern") or PATTERN_SOFT_UD_FAV_FORM
    out["reasons"] = list(meta.get("reasons") or [])

    prove, proofs = feh_proves_process_miss(
        audit,
        evidence=evidence,
        cfg=cfg,
        selection=str(bet.get("selection") or ""),
        odds=_as_float(
            bet.get("decimal_odds") if bet.get("decimal_odds") is not None else bet.get("odds")
        ),
        sport=str(bet.get("sport") or ""),
    )
    out["proofs"] = proofs

    variance_lean = None
    lean_applied = False
    if prove and fc.get("lean_process_miss", True):
        variance_lean = "research_process_miss"
        # Safe lean into packet/bet taxonomy only when FEH proves it
        if isinstance(packet, dict):
            existing = str(packet.get("variance_class") or "").strip().lower()
            # Do not override one-offs / true randomness already set
            if existing in ("", "unknown", "research_process_miss", "model_error"):
                packet["variance_class"] = variance_lean
                if not packet.get("predictability"):
                    packet["predictability"] = "moderately_predictable"
                try:
                    from nt.settlement_taxonomy import compute_learning_weight

                    packet["learning_weight"] = compute_learning_weight(
                        str(packet.get("predictability") or "moderately_predictable"),
                        variance_lean,
                    )
                except Exception:
                    pass
                notes = str(packet.get("classification_notes") or "")
                tag = "feh_feedback:research_process_miss"
                if tag not in notes:
                    packet["classification_notes"] = (
                        f"{notes}; {tag}".strip("; ") if notes else tag
                    )[:240]
                lean_applied = True
        # Annotate bet notes for audit trail (does not invent process_error alone)
        prev = str(bet.get("notes") or "")
        mark = f"feh_pattern:{PATTERN_SOFT_UD_FAV_FORM}"
        if mark not in prev:
            bet["notes"] = (prev + " | " + mark).strip(" |")[:800]
        if lean_applied:
            mark2 = "feh_lean:research_process_miss"
            if mark2 not in str(bet.get("notes") or ""):
                bet["notes"] = (str(bet.get("notes") or "") + " | " + mark2).strip(" |")[
                    :800
                ]
    else:
        # Pattern tag only — legacy / no FEH proof
        prev = str(bet.get("notes") or "")
        mark = f"feh_pattern:{PATTERN_SOFT_UD_FAV_FORM}"
        if mark not in prev:
            bet["notes"] = (prev + " | " + mark).strip(" |")[:800]

    out["variance_lean"] = variance_lean
    out["lean_applied"] = lean_applied

    path = append_feh_feedback(
        cfg,
        {
            "bet_id": bet.get("bet_id"),
            "match": bet.get("match"),
            "selection": bet.get("selection"),
            "sport": bet.get("sport"),
            "odds": meta.get("odds"),
            "result": res,
            "pattern": out["pattern"],
            "reasons": out["reasons"],
            "proofs": proofs,
            "variance_lean": variance_lean,
            "lean_applied": lean_applied,
            "legacy_no_feh_proof": not prove,
        },
    )
    out["path"] = str(path) if path else None
    return out


__all__ = [
    "PATTERN_SOFT_UD_FAV_FORM",
    "append_feh_feedback",
    "fav_rank_form_heuristic",
    "feedback_cfg",
    "feedback_path",
    "feh_proves_process_miss",
    "is_soft_underdog_hc",
    "process_settlement_feh_feedback",
    "should_tag_soft_ud_loss",
]
