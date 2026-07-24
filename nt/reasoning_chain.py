from __future__ import annotations

"""
Minimal reasoning-chain dump for recommend (dry-run OK).

Append-only JSONL: data/state/reasoning_chains.jsonl
PLACE_THESE.md sections:
  ## Reasoning          (picks)
  ## Near-miss / Rejected  (even when slip empty / recommend blocked)

Does not invent p_model, stakes, or bankroll math — only records what
recommend / light already computed. Light LATEST is SSOT for promo join.
"""

import json
import re
from pathlib import Path
from typing import Any

from nt.bets_io import utc_now
from nt.config import path_from_config
from nt.paths import resolve

SCHEMA_VERSION = 1

# Missed-audit mid band (prefer for near-miss volume cap)
_MID_BAND_LO = 1.80
_MID_BAND_HI = 2.20
# Survivable research band (secondary preference)
_SURV_BAND_LO = 1.85
_SURV_BAND_HI = 2.60


def reasoning_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = dict(cfg.get("reasoning") or {})
    defaults = {
        "enabled": True,
        "jsonl": "data/state/reasoning_chains.jsonl",
        "max_near_miss": 8,
        "near_miss_ev_slack": 0.04,  # include rejects within this of clearing EV
        "place_md_section": True,
        "join_light": True,
    }
    return {**defaults, **raw}


def reasoning_chains_path(cfg: dict[str, Any]) -> Path:
    rc = reasoning_cfg(cfg)
    paths = cfg.get("paths") or {}
    if paths.get("reasoning_chains_jsonl"):
        return path_from_config(cfg, "reasoning_chains_jsonl")
    rel = str(rc.get("jsonl") or "data/state/reasoning_chains.jsonl")
    return resolve(rel)


def _as_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pick_attr(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _line_key(match: Any, selection: Any) -> str:
    return f"{str(match or '').strip().lower()}||{str(selection or '').strip().lower()}"


def _odds_of(row: dict[str, Any]) -> float | None:
    return _as_float(
        row.get("decimal_odds") if row.get("decimal_odds") is not None else row.get("odds")
    )


def _is_mid_band(odds: float | None) -> bool:
    return odds is not None and _MID_BAND_LO <= float(odds) <= _MID_BAND_HI


def _is_surv_band(odds: float | None) -> bool:
    return odds is not None and _SURV_BAND_LO <= float(odds) <= _SURV_BAND_HI


def _controls_from_notes_and_stake(
    notes: str,
    stake_decision: dict[str, Any] | None,
    *,
    explore: bool = False,
    learning_stake_mult: float | None = None,
    learning_ev_boost: float | None = None,
) -> dict[str, Any]:
    """Extract auditable control flags without inventing values."""
    controls: dict[str, Any] = {}
    n = notes or ""
    if "temp_ev_relax" in n:
        controls["temp_ev_relax"] = True
        m = re.search(r"temp_ev_relax:delta=([0-9.]+)", n)
        if m:
            controls["temp_ev_relax_delta"] = float(m.group(1))
        m2 = re.search(r"stake[×x]([0-9.]+)", n)
        if m2:
            controls["temp_ev_relax_stake_mult"] = float(m2.group(1))
    if stake_decision and isinstance(stake_decision, dict):
        ter = stake_decision.get("temp_ev_relax")
        if isinstance(ter, dict):
            controls["temp_ev_relax"] = True
            if ter.get("delta_ev") is not None:
                controls["temp_ev_relax_delta"] = ter.get("delta_ev")
            if ter.get("stake_mult") is not None:
                controls["temp_ev_relax_stake_mult"] = ter.get("stake_mult")
        if stake_decision.get("size_mode"):
            controls["size_mode"] = stake_decision.get("size_mode")
        if stake_decision.get("active_unit_nok") is not None:
            controls["unit_nok"] = stake_decision.get("active_unit_nok")
        if stake_decision.get("regime_explore"):
            controls["regime_explore"] = True
    if explore or "EXPLORE" in n or "EXPLORE_REGIME" in n:
        controls["explore"] = True
    if learning_stake_mult is not None and abs(float(learning_stake_mult) - 1.0) > 0.01:
        controls["learning_stake_mult"] = float(learning_stake_mult)
    if learning_ev_boost is not None and abs(float(learning_ev_boost)) > 1e-9:
        controls["learning_ev_boost"] = float(learning_ev_boost)
    if "process_gate" in n.lower():
        controls["process_gate"] = True
    return controls


def _parse_promo_from_notes(notes: str) -> float | None:
    n = notes or ""
    if "promo_score=" not in n:
        return None
    try:
        return float(n.split("promo_score=")[-1].split()[0].split("|")[0].rstrip(";,"))
    except (TypeError, ValueError, IndexError):
        return None


def load_light_payload(cfg: dict[str, Any]) -> dict[str, Any] | None:
    """Load light LATEST.json, else same-day batch. Soft-fail → None."""
    try:
        outbox = path_from_config(cfg, "outbox")
        latest = outbox / "light_research" / "LATEST.json"
        if latest.is_file():
            data = json.loads(latest.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            if isinstance(data, list):
                return {"records": data}
        from nt.light_research import load_light_batch

        payload = load_light_batch(cfg)
        if payload and (payload.get("records") or payload.get("deep_queue")):
            return payload
    except Exception:
        return None
    return None


def _record_from_light_dict(d: dict[str, Any]) -> Any:
    """Build a LightRecord-ish object for promotion_score_components."""
    from nt.light_research import LightRecord

    return LightRecord(
        match=str(d.get("match") or ""),
        selection=str(d.get("selection") or ""),
        sport=str(d.get("sport") or "unknown"),
        decimal_odds=float(d.get("decimal_odds") or d.get("odds") or 1.5),
        odds_band=str(d.get("odds_band") or ""),
        market_family=str(d.get("market_family") or ""),
        verdict=str(d.get("verdict") or "pass"),
        promote_to_deep=bool(d.get("promote_to_deep")),
        rough_p_needed=_as_float(d.get("rough_p_needed")),
        rough_ev_note=str(d.get("rough_ev_note") or ""),
        reason=str(d.get("reason") or ""),
        has_deep_pack=bool(d.get("has_deep_pack")),
        has_p_model=bool(d.get("has_p_model")),
        prior_p=_as_float(d.get("prior_p")),
        prior_ev=_as_float(d.get("prior_ev")),
        prior_available=bool(d.get("prior_available")),
        prefilter_stage1=str(d.get("prefilter_stage1") or ""),
        prefilter_stage2=str(d.get("prefilter_stage2") or ""),
        prefilter_rank=_as_float(d.get("prefilter_rank")),
    )


def enrich_light_for_chain(
    rec: dict[str, Any],
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Normalize a light record for chain join: promo total + components when possible.
    Never notes-only when structured fields exist.
    """
    out: dict[str, Any] = {}
    for k in (
        "verdict",
        "promotion_score",
        "promo_score",
        "promote_to_deep",
        "rough_ev_note",
        "notes",
        "preferred",
        "short_main",
        "reason",
        "tier",
        "has_p_model",
        "has_deep_pack",
        "prefilter_stage1",
        "prefilter_stage2",
        "prior_ev",
        "prior_available",
        "market_family",
        "odds_band",
        "sport",
        "decimal_odds",
    ):
        if rec.get(k) is not None and rec.get(k) != "":
            key = "promotion_score" if k == "promo_score" else k
            out[key] = rec.get(k)

    # Prefer explicit breakdown on the record
    breakdown = rec.get("promotion_score_breakdown") or rec.get("promo_components")
    if isinstance(breakdown, dict) and breakdown:
        out["promotion_score_breakdown"] = breakdown
        if breakdown.get("total") is not None and out.get("promotion_score") is None:
            out["promotion_score"] = breakdown.get("total")
        if isinstance(breakdown.get("components"), dict):
            out["promotion_score_components"] = breakdown["components"]

    notes = str(rec.get("rough_ev_note") or rec.get("notes") or rec.get("reason") or "")
    parsed = _parse_promo_from_notes(notes)
    if parsed is not None and out.get("promotion_score") is None:
        out["promotion_score"] = parsed

    # Compute components via light_research API when cfg available and still thin
    if cfg is not None and (
        out.get("promotion_score_components") is None
        or out.get("promotion_score") is None
    ):
        try:
            from nt.light_research import promotion_score_components

            br = promotion_score_components(_record_from_light_dict(rec), cfg)
            out["promotion_score"] = br["total"]
            out["promotion_score_components"] = br.get("components") or {}
            out["promotion_score_breakdown"] = br
            out["promo_scorer"] = br.get("scorer") or "promotion_score"
            if br.get("preferred") is not None and "preferred" not in out:
                out["preferred"] = br["preferred"]
            if br.get("short_main") is not None and "short_main" not in out:
                out["short_main"] = br["short_main"]
        except Exception:
            if out.get("promotion_score") is not None:
                out.setdefault("promo_scorer", "promotion_score")
    elif out.get("promotion_score") is not None:
        out.setdefault("promo_scorer", "promotion_score")

    return out


def build_light_by_key(
    cfg: dict[str, Any],
    light_payload: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Index light records by (match, selection) with promo enrichment."""
    payload = light_payload if light_payload is not None else load_light_payload(cfg)
    if not payload:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for rec in payload.get("records") or []:
        if not isinstance(rec, dict):
            continue
        key = _line_key(rec.get("match"), rec.get("selection"))
        if not key or key == "||":
            continue
        out[key] = enrich_light_for_chain(rec, cfg)
    # deep_queue rows may lack full record fields — fill missing keys only
    for dq in payload.get("deep_queue") or []:
        if not isinstance(dq, dict):
            continue
        key = _line_key(dq.get("match"), dq.get("selection"))
        if not key or key == "||" or key in out:
            continue
        out[key] = enrich_light_for_chain(dq, cfg)
    return out


def _light_from_notes_or_dict(notes: str = "", light: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(light, dict):
        # Prefer structured light SSOT — copy known fields (never notes-only)
        for k in (
            "verdict",
            "promotion_score",
            "promo_score",
            "promote_to_deep",
            "rough_ev_note",
            "notes",
            "preferred",
            "short_main",
            "reason",
            "tier",
            "has_p_model",
            "promotion_score_components",
            "promotion_score_breakdown",
            "promo_scorer",
            "prefilter_stage1",
            "prefilter_stage2",
        ):
            if light.get(k) is not None:
                out[k if k != "promo_score" else "promotion_score"] = light.get(k)
    n = notes or ""
    if "promo_score=" in n and "promotion_score" not in out:
        parsed = _parse_promo_from_notes(n)
        if parsed is not None:
            out["promotion_score"] = parsed
    return out


def build_chain_from_pick(
    pick: Any,
    *,
    haircut: float | None = None,
    phase_id: str | None = None,
    bet_id: str | None = None,
    light: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a minimal reasoning chain dict from a recommend pick
    (Recommendation dataclass or dict).
    """
    notes = str(_pick_attr(pick, "notes") or "")
    stake_decision = _pick_attr(pick, "stake_decision")
    if stake_decision is not None and not isinstance(stake_decision, dict):
        stake_decision = None
    p_model = _as_float(_pick_attr(pick, "p_model"))
    odds = _as_float(_pick_attr(pick, "decimal_odds"))
    ev = _as_float(_pick_attr(pick, "ev"))
    stake = _as_float(_pick_attr(pick, "stake_nok"))
    hair = _as_float(haircut)
    # Prefer recorded EV; optionally restate haircut EV if both p and odds known
    ev_h = None
    if p_model is not None and odds is not None and hair is not None:
        from nt.evidence import ev_after_haircut

        ev_h = round(ev_after_haircut(p_model, odds, hair), 4)

    oc = _pick_attr(pick, "odds_confidence")
    if not isinstance(oc, dict):
        oc = None
    oc_band = str(_pick_attr(pick, "odds_confidence_band") or "")
    if not oc_band and isinstance(oc, dict):
        oc_band = str(oc.get("band_id") or "")

    chain: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "ts": utc_now(),
        "kind": "pick",
        "match": str(_pick_attr(pick, "match") or ""),
        "selection": str(_pick_attr(pick, "selection") or ""),
        "decimal_odds": odds,
        "sport": str(_pick_attr(pick, "sport") or ""),
        "market_type": str(_pick_attr(pick, "market_type") or ""),
        "market_key": str(_pick_attr(pick, "market_key") or ""),
        "grade": str(_pick_attr(pick, "grade") or ""),
        "odds_band": str(_pick_attr(pick, "odds_band") or ""),
        "odds_confidence_band": oc_band,
        "odds_confidence": oc,
        "p_model": p_model,
        "haircut": hair,
        "ev": ev,
        "ev_after_haircut": ev_h if ev_h is not None else ev,
        "stake_nok": stake,
        "phase": phase_id,
        "bet_id": bet_id,
        "evidence_path": str(_pick_attr(pick, "evidence_path") or ""),
        "high_odds": bool(_pick_attr(pick, "high_odds") or False),
        "controls": _controls_from_notes_and_stake(
            notes,
            stake_decision,
            explore=bool(_pick_attr(pick, "explore") or False),
            learning_stake_mult=_as_float(_pick_attr(pick, "learning_stake_mult")),
            learning_ev_boost=_as_float(_pick_attr(pick, "learning_ev_boost")),
        ),
        "light": _light_from_notes_or_dict(notes, light),
        "reasons": list(_pick_attr(pick, "reasons") or [])[:8],
        "notes": notes[:400],
    }
    if extra:
        chain["extra"] = dict(extra)
    return chain


def build_chain_from_near_miss(
    row: dict[str, Any],
    *,
    haircut: float | None = None,
    phase_id: str | None = None,
    light: dict[str, Any] | None = None,
    source: str = "reject",
) -> dict[str, Any]:
    """
    Build a chain for a light near-miss, portfolio reject, or prefilter discard.
    """
    notes = str(row.get("notes") or row.get("rough_ev_note") or "")
    reason = str(row.get("reason") or row.get("reject_reason") or "")
    p_model = _as_float(row.get("p_model"))
    odds = _odds_of(row)
    ev = _as_float(row.get("ev"))
    hair = _as_float(haircut if haircut is not None else row.get("haircut"))
    ev_h = None
    if p_model is not None and odds is not None and hair is not None:
        from nt.evidence import ev_after_haircut

        ev_h = round(ev_after_haircut(p_model, odds, hair), 4)

    kind = str(row.get("kind") or "near_miss")
    if kind not in ("near_miss", "rejected_prefilter", "pick"):
        kind = "near_miss"
    rejected_at = str(
        row.get("rejected_at_stage")
        or row.get("stage")
        or ("prefilter" if kind == "rejected_prefilter" else source)
    )

    light_blob = _light_from_notes_or_dict(notes, light or row.get("light"))
    # Ensure promo on chain when light join present
    if light_blob.get("promotion_score") is None and row.get("promotion_score") is not None:
        light_blob["promotion_score"] = row.get("promotion_score")
    if row.get("promotion_score_components") and "promotion_score_components" not in light_blob:
        light_blob["promotion_score_components"] = row.get("promotion_score_components")

    oc = row.get("odds_confidence")
    if not isinstance(oc, dict):
        oc = None
    oc_band = str(row.get("odds_confidence_band") or "")
    if not oc_band and isinstance(oc, dict):
        oc_band = str(oc.get("band_id") or "")
    if not oc_band and odds is not None:
        try:
            from nt.odds_confidence import classify_odds_confidence_band

            oc_band = classify_odds_confidence_band(float(odds), None)
        except Exception:
            oc_band = ""

    chain: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "ts": utc_now(),
        "kind": kind,
        "source": source,
        "rejected_at_stage": rejected_at,
        "match": str(row.get("match") or ""),
        "selection": str(row.get("selection") or ""),
        "decimal_odds": odds,
        "sport": str(row.get("sport") or ""),
        "market_type": str(row.get("market_type") or ""),
        "grade": str(row.get("grade") or ""),
        "odds_confidence_band": oc_band,
        "odds_confidence": oc,
        "p_model": p_model,
        "haircut": hair,
        "ev": ev if ev is not None else ev_h,
        "ev_after_haircut": ev_h if ev_h is not None else ev,
        "stake_nok": _as_float(row.get("stake_nok")),
        "phase": phase_id,
        "reject_reason": reason,
        "controls": {
            k: v
            for k, v in {
                "process_gate_raise": row.get("process_gate_raise"),
                "temp_ev_relax_delta": row.get("temp_ev_relax_delta"),
            }.items()
            if v is not None
        },
        "light": light_blob,
        "notes": (notes or reason)[:400],
    }
    if row.get("promotion_score") is not None:
        chain["promotion_score"] = row.get("promotion_score")
    elif light_blob.get("promotion_score") is not None:
        chain["promotion_score"] = light_blob.get("promotion_score")
    return chain


def is_near_miss_reject(row: dict[str, Any], *, slack: float = 0.04) -> bool:
    """Heuristic: reject with EV present and reason suggesting EV/floor miss."""
    if not isinstance(row, dict):
        return False
    reason = str(row.get("reason") or "").lower()
    ev = _as_float(row.get("ev"))
    # Explicit near-miss tags from light research
    if row.get("near_miss") or row.get("kind") in ("near_miss", "rejected_prefilter"):
        return True
    if "promo_score" in reason or "light" in reason:
        return True
    # Grade F mid-band always interesting for near-miss audit
    grade = str(row.get("grade") or "").upper()
    if grade == "F" and _is_mid_band(_odds_of(row)):
        return True
    if "grade f" in reason and _is_mid_band(_odds_of(row)):
        return True
    # Pure "no p_model" without mid-band / light tags is noise for near-miss
    if "no p_model" in reason and not _is_mid_band(_odds_of(row)):
        if not any(
            tok in reason
            for tok in ("light-pass", "deep queue", "blocked", "prefilter", "min_ev", "ev ")
        ):
            return False

    if ev is None:
        # Gate / grade / EV-floor language without computed ev still counts
        return any(
            tok in reason
            for tok in (
                "ev ",
                "min_ev",
                "below min",
                "haircut",
                "temp_ev_relax",
                "process_gate",
                "insufficient remaining",
                "grade",
                "evidence",
                "high odds",
                "band",
                "correlation",
                "diversif",
                "prefilter",
                "light-pass",
                "deep queue",
                "blocked",
            )
        ) or (_is_mid_band(_odds_of(row)) and "no p_model" in reason)
    if any(
        tok in reason
        for tok in (
            "ev",
            "min_ev",
            "floor",
            "grade",
            "high odds",
            "process_gate",
            "temp_ev",
            "band",
            "insufficient remaining",
            "correlation",
            "diversif",
            "prefilter",
        )
    ):
        return True
    # Within slack of zero EV still interesting
    return abs(float(ev)) <= float(slack) + 0.05


def _row_priority(r: dict[str, Any]) -> tuple:
    """
    Sort key for near-miss volume cap.
    Prefer: mid-band (1.80–2.20) → light-pass / deep_queue → higher promo → higher EV.
    """
    odds = _odds_of(r)
    mid = 1 if _is_mid_band(odds) else (1 if _is_surv_band(odds) else 0)
    stage = str(r.get("rejected_at_stage") or r.get("source") or "").lower()
    light_pass = 1 if (
        "light" in stage
        or stage in ("light_pass_no_pack", "deep_queue", "light_pass")
        or r.get("source") in ("light", "deep_queue", "light_pass")
    ) else 0
    promo = _as_float(r.get("promotion_score"))
    if promo is None:
        light = r.get("light") if isinstance(r.get("light"), dict) else {}
        promo = _as_float(light.get("promotion_score")) if light else None
    ev = _as_float(r.get("ev"))
    return (
        mid,
        light_pass,
        promo if promo is not None else -99.0,
        ev if ev is not None else -99.0,
    )


def select_near_misses(
    rejects: list[Any],
    *,
    max_n: int = 8,
    slack: float = 0.04,
) -> list[dict[str, Any]]:
    rows = [r for r in rejects if isinstance(r, dict) and is_near_miss_reject(r, slack=slack)]
    # Deduplicate by line key (keep highest priority)
    best: dict[str, dict[str, Any]] = {}
    for r in rows:
        key = _line_key(r.get("match"), r.get("selection"))
        if key == "||":
            continue
        prev = best.get(key)
        if prev is None or _row_priority(r) > _row_priority(prev):
            best[key] = r
    ranked = sorted(best.values(), key=_row_priority, reverse=True)
    return ranked[: max(0, int(max_n))]


def collect_near_miss_candidates(
    cfg: dict[str, Any],
    rejects: list[Any] | None,
    *,
    light_payload: dict[str, Any] | None = None,
    light_by_key: dict[str, dict[str, Any]] | None = None,
    pick_keys: set[str] | None = None,
    max_n: int | None = None,
    slack: float | None = None,
) -> list[dict[str, Any]]:
    """
    Build near-miss / rejected rows from portfolio rejects + light LATEST.

    Sources (capped by max_near_miss, prefer mid-band + light-pass):
      - portfolio rejects (EV/gate/grade)
      - light-pass without p_model
      - deep_queue high-promo lines still without pack
      - prefilter / mid-band grade-F style discards
    """
    rc = reasoning_cfg(cfg)
    max_n = int(max_n if max_n is not None else rc.get("max_near_miss") or 8)
    slack = float(slack if slack is not None else rc.get("near_miss_ev_slack") or 0.04)
    picked = pick_keys or set()
    light_map = light_by_key if light_by_key is not None else build_light_by_key(cfg, light_payload)
    payload = light_payload if light_payload is not None else load_light_payload(cfg)

    candidates: list[dict[str, Any]] = []

    # --- portfolio rejects ---
    for r in rejects or []:
        if not isinstance(r, dict):
            continue
        key = _line_key(r.get("match"), r.get("selection"))
        if key in picked:
            continue
        row = dict(r)
        reason_l = str(row.get("reason") or "").lower()
        grade = str(row.get("grade") or "").upper()
        odds = _odds_of(row)
        if "prefilter" in reason_l or row.get("kind") == "rejected_prefilter":
            row["kind"] = "rejected_prefilter"
            row["rejected_at_stage"] = row.get("rejected_at_stage") or "prefilter"
            row["source"] = row.get("source") or "prefilter"
        elif grade == "F" or "grade f" in reason_l:
            row["kind"] = "near_miss" if _is_mid_band(odds) else "near_miss"
            row["rejected_at_stage"] = row.get("rejected_at_stage") or "grade_F"
            row["source"] = row.get("source") or "reject"
        else:
            row.setdefault("kind", "near_miss")
            row.setdefault("rejected_at_stage", "portfolio")
            row.setdefault("source", "reject")
        if key in light_map:
            row["light"] = light_map[key]
            if light_map[key].get("promotion_score") is not None:
                row.setdefault("promotion_score", light_map[key]["promotion_score"])
        candidates.append(row)

    # --- light records ---
    records = (payload or {}).get("records") or []
    dq_keys = {
        _line_key(d.get("match"), d.get("selection"))
        for d in ((payload or {}).get("deep_queue") or [])
        if isinstance(d, dict)
    }
    for rec in records:
        if not isinstance(rec, dict):
            continue
        key = _line_key(rec.get("match"), rec.get("selection"))
        if not key or key == "||" or key in picked:
            continue
        odds = _as_float(rec.get("decimal_odds"))
        lite = light_map.get(key) or enrich_light_for_chain(rec, cfg)
        has_p = bool(rec.get("has_p_model"))
        verdict = str(rec.get("verdict") or "").lower()
        promo = lite.get("promotion_score")
        stage1 = str(rec.get("prefilter_stage1") or "")
        stage2 = str(rec.get("prefilter_stage2") or "")
        discarded = bool(rec.get("discarded")) or (
            "fail" in stage1.lower() or "fail" in stage2.lower() or "discard" in stage1.lower()
        )

        # Prefilter discards in mid-band
        if discarded and _is_mid_band(odds) and verdict != "pass":
            candidates.append(
                {
                    "match": rec.get("match"),
                    "selection": rec.get("selection"),
                    "odds": odds,
                    "decimal_odds": odds,
                    "sport": rec.get("sport"),
                    "grade": rec.get("grade") or "",
                    "kind": "rejected_prefilter",
                    "rejected_at_stage": (
                        "prefilter_stage1"
                        if stage1 and "fail" in stage1.lower()
                        else ("prefilter_stage2" if stage2 else "prefilter")
                    ),
                    "source": "prefilter",
                    "reason": stage1 or stage2 or rec.get("reason") or "prefilter discard",
                    "promotion_score": promo,
                    "promotion_score_components": lite.get("promotion_score_components"),
                    "light": lite,
                    "near_miss": True,
                }
            )
            continue

        # Light-pass without p_model (research near-miss)
        if verdict == "pass" and not has_p:
            stage = "deep_queue" if key in dq_keys or rec.get("promote_to_deep") else "light_pass_no_pack"
            candidates.append(
                {
                    "match": rec.get("match"),
                    "selection": rec.get("selection"),
                    "odds": odds,
                    "decimal_odds": odds,
                    "sport": rec.get("sport"),
                    "kind": "near_miss",
                    "rejected_at_stage": stage,
                    "source": "light" if stage == "light_pass_no_pack" else "deep_queue",
                    "reason": rec.get("reason")
                    or (
                        "light-pass on deep_queue — no p_model pack yet"
                        if stage == "deep_queue"
                        else "light-pass without p_model"
                    ),
                    "promotion_score": promo,
                    "promotion_score_components": lite.get("promotion_score_components"),
                    "light": lite,
                    "near_miss": True,
                    "rough_ev_note": rec.get("rough_ev_note") or "",
                }
            )

    # --- deep_queue explicit (if not already covered via records) ---
    for dq in (payload or {}).get("deep_queue") or []:
        if not isinstance(dq, dict):
            continue
        key = _line_key(dq.get("match"), dq.get("selection"))
        if not key or key == "||" or key in picked:
            continue
        # skip if already have this key in candidates
        if any(_line_key(c.get("match"), c.get("selection")) == key for c in candidates):
            continue
        odds = _as_float(dq.get("decimal_odds") if dq.get("decimal_odds") is not None else dq.get("odds"))
        lite = light_map.get(key) or enrich_light_for_chain(dq, cfg)
        candidates.append(
            {
                "match": dq.get("match"),
                "selection": dq.get("selection"),
                "odds": odds,
                "decimal_odds": odds,
                "sport": dq.get("sport"),
                "kind": "near_miss",
                "rejected_at_stage": "deep_queue",
                "source": "deep_queue",
                "reason": dq.get("reason") or "deep_queue candidate without pack",
                "promotion_score": lite.get("promotion_score"),
                "promotion_score_components": lite.get("promotion_score_components"),
                "light": lite,
                "near_miss": True,
            }
        )

    return select_near_misses(candidates, max_n=max_n, slack=slack)


def format_near_miss_md(chains: list[dict[str, Any]]) -> str:
    """Collapsible-style ## Near-miss / Rejected section for PLACE_THESE.md."""
    lines = ["## Near-miss / Rejected", ""]
    misses = [c for c in chains if c.get("kind") != "pick"]
    if not misses:
        lines.append("_No near-miss / rejected lines (empty audit set)._")
        lines.append("")
        return "\n".join(lines)

    for c in misses:
        odds = c.get("decimal_odds")
        odds_s = f"{float(odds):.2f}" if odds is not None else "?"
        title = f"{c.get('match') or '?'} / {c.get('selection') or '?'} @ {odds_s}"
        stage = c.get("rejected_at_stage") or c.get("source") or c.get("kind") or "?"
        reason = (c.get("reject_reason") or c.get("notes") or "")[:160]
        light = c.get("light") or {}
        promo = c.get("promotion_score")
        if promo is None:
            promo = light.get("promotion_score")
        promo_s = f"{float(promo):.1f}" if promo is not None else "—"
        comps = light.get("promotion_score_components") or {}
        bit = f"- **{title}** — stage: {stage} reason: {reason} promo={promo_s}"
        if comps and isinstance(comps, dict):
            top = sorted(comps.items(), key=lambda kv: abs(float(kv[1])), reverse=True)[:4]
            if top:
                bit += " [" + ", ".join(f"{k}:{v:+.0f}" for k, v in top) + "]"
        lines.append(bit)
    lines.append("")
    return "\n".join(lines)


def format_reasoning_md(chains: list[dict[str, Any]]) -> str:
    """Markdown ## Reasoning + ## Near-miss / Rejected for PLACE_THESE.md."""
    lines = ["## Reasoning", ""]
    picks = [c for c in chains if c.get("kind") == "pick"]
    misses = [c for c in chains if c.get("kind") != "pick"]

    if not picks and not misses:
        lines.append("_No reasoning chains (empty slip / no near-misses)._")
        lines.append("")
    elif not picks:
        lines.append("_Empty slip — see Near-miss / Rejected below._")
        lines.append("")
    else:
        lines.append(f"**Picks ({len(picks)})**")
        lines.append("")
        for i, c in enumerate(picks, 1):
            lines.extend(_format_one_md(i, c))

    # Always append near-miss section (even empty) so outbox is consistent
    lines.append(format_near_miss_md(chains).rstrip())
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _format_one_md(i: int, c: dict[str, Any]) -> list[str]:
    odds = c.get("decimal_odds")
    odds_s = f"{float(odds):.2f}" if odds is not None else "?"
    title = f"{c.get('match') or '?'} / {c.get('selection') or '?'} @ {odds_s}"
    bits = []
    if c.get("p_model") is not None:
        bits.append(f"p_model={float(c['p_model']):.3f}")
    if c.get("haircut") is not None:
        bits.append(f"haircut={float(c['haircut']):.0%}")
    ev = c.get("ev_after_haircut") if c.get("ev_after_haircut") is not None else c.get("ev")
    if ev is not None:
        bits.append(f"EV={float(ev):+.3f}")
    if c.get("stake_nok") is not None:
        bits.append(f"stake={float(c['stake_nok']):.0f}")
    if c.get("grade"):
        bits.append(f"grade={c['grade']}")
    if c.get("phase"):
        bits.append(f"phase={c['phase']}")
    if c.get("odds_confidence_band"):
        bits.append(f"odds_conf_band={c['odds_confidence_band']}")
    controls = c.get("controls") or {}
    light = c.get("light") or {}
    out = [f"### {i}. {title}", ""]
    if bits:
        out.append("- " + " · ".join(bits))
    oc = c.get("odds_confidence")
    if isinstance(oc, dict) and oc:
        oc_bits = []
        if oc.get("band_label"):
            oc_bits.append(str(oc["band_label"]))
        if oc.get("ok") is not None:
            oc_bits.append("pass" if oc.get("ok") else "FAIL")
        fails = oc.get("failures") or []
        if fails:
            oc_bits.append("fail:" + "; ".join(str(f) for f in fails[:3]))
        passes = oc.get("passes") or []
        if passes and not fails:
            oc_bits.append("ok:" + ",".join(str(p) for p in passes[:3]))
        if oc.get("min_ev") is not None:
            oc_bits.append(f"band_min_ev={float(oc['min_ev']):.3f}")
        if oc.get("stake_mult") is not None and abs(float(oc["stake_mult"]) - 1.0) > 1e-9:
            oc_bits.append(f"stake×{float(oc['stake_mult']):.2f}")
        if oc_bits:
            out.append(f"- odds_confidence: {' · '.join(oc_bits)}")
    if controls:
        ctrl = ", ".join(f"{k}={v}" for k, v in controls.items())
        out.append(f"- controls: {ctrl}")
    if light:
        # Structured promo first — never notes-only when light exists
        lite_bits = []
        if light.get("promotion_score") is not None:
            lite_bits.append(f"promo={light['promotion_score']}")
        if light.get("verdict"):
            lite_bits.append(f"verdict={light['verdict']}")
        if light.get("promote_to_deep") is not None:
            lite_bits.append(f"promote={light['promote_to_deep']}")
        comps = light.get("promotion_score_components")
        if isinstance(comps, dict) and comps:
            top = sorted(comps.items(), key=lambda kv: abs(float(kv[1])), reverse=True)[:5]
            lite_bits.append("comps={" + ", ".join(f"{k}:{v:+.0f}" for k, v in top) + "}")
        elif light.get("promo_scorer"):
            lite_bits.append(f"scorer={light['promo_scorer']}")
        if lite_bits:
            out.append(f"- light/promo: {', '.join(lite_bits)}")
        else:
            lite = ", ".join(f"{k}={v}" for k, v in light.items() if k not in ("notes",))
            if lite:
                out.append(f"- light/promo: {lite}")
    if c.get("reject_reason"):
        out.append(f"- reject: {c['reject_reason']}")
    if c.get("notes"):
        out.append(f"- notes: {c['notes'][:220]}")
    out.append("")
    return out


def append_reasoning_chains(cfg: dict[str, Any], chains: list[dict[str, Any]]) -> Path:
    """Append chain dicts to reasoning_chains.jsonl. Returns path written."""
    path = reasoning_chains_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not chains:
        return path
    with open(path, "a", encoding="utf-8") as f:
        for c in chains:
            f.write(json.dumps(c, ensure_ascii=False, default=str) + "\n")
    return path


def count_reasoning_chains(cfg: dict[str, Any]) -> int:
    path = reasoning_chains_path(cfg)
    if not path.exists():
        return 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def build_recommend_chains(
    cfg: dict[str, Any],
    picked: list[Any],
    rejects: list[Any] | None = None,
    *,
    phase_id: str | None = None,
    bet_ids: list[str] | None = None,
    light_by_key: dict[str, dict[str, Any]] | None = None,
    light_payload: dict[str, Any] | None = None,
    blocked: bool = False,
    block_reason: str | None = None,
) -> list[dict[str, Any]]:
    """
    Build pick + near-miss chains for one recommend run.

    Always joins light LATEST when available. Emits near-miss chains even when
    picks empty or recommend blocked.
    """
    rc = reasoning_cfg(cfg)
    if not rc.get("enabled", True):
        return []
    haircut = None
    try:
        haircut = float((cfg.get("selection") or {}).get("probability_haircut", 0.03))
    except (TypeError, ValueError):
        haircut = 0.03

    # Light SSOT join
    payload = light_payload
    if payload is None and rc.get("join_light", True):
        payload = load_light_payload(cfg)
    light_map = light_by_key if light_by_key is not None else (
        build_light_by_key(cfg, payload) if rc.get("join_light", True) else {}
    )

    chains: list[dict[str, Any]] = []
    ids = list(bet_ids or [])
    pick_keys: set[str] = set()
    for i, p in enumerate(picked or []):
        key = _line_key(_pick_attr(p, "match"), _pick_attr(p, "selection"))
        pick_keys.add(key)
        bid = ids[i] if i < len(ids) else None
        extra = None
        if blocked and block_reason:
            extra = {"blocked": True, "block_reason": block_reason}
        chains.append(
            build_chain_from_pick(
                p,
                haircut=haircut,
                phase_id=phase_id,
                bet_id=bid,
                light=light_map.get(key),
                extra=extra,
            )
        )

    misses = collect_near_miss_candidates(
        cfg,
        list(rejects or []),
        light_payload=payload,
        light_by_key=light_map,
        pick_keys=pick_keys,
        max_n=int(rc.get("max_near_miss") or 8),
        slack=float(rc.get("near_miss_ev_slack") or 0.04),
    )
    for row in misses:
        key = _line_key(row.get("match"), row.get("selection"))
        if blocked and block_reason:
            row = dict(row)
            row.setdefault("notes", "")
            # annotate without inventing p_model
            if block_reason not in str(row.get("reason") or ""):
                row["reason"] = (
                    f"{row.get('reason') or 'near-miss'}; recommend_blocked:{block_reason}"
                )
        chains.append(
            build_chain_from_near_miss(
                row,
                haircut=haircut,
                phase_id=phase_id,
                light=light_map.get(key) or row.get("light"),
                source=str(row.get("source") or "reject"),
            )
        )
    return chains


def dump_reasoning_for_recommend(
    cfg: dict[str, Any],
    picked: list[Any],
    rejects: list[Any] | None,
    *,
    place_md: str,
    phase_id: str | None = None,
    bet_ids: list[str] | None = None,
    light_by_key: dict[str, dict[str, Any]] | None = None,
    light_payload: dict[str, Any] | None = None,
    blocked: bool = False,
    block_reason: str | None = None,
) -> tuple[str, list[dict[str, Any]], Path | None]:
    """
    Append chains to JSONL and inject ## Reasoning + ## Near-miss / Rejected
    into PLACE_THESE markdown.

    Returns (updated_md, chains, jsonl_path_or_none).
    """
    rc = reasoning_cfg(cfg)
    if not rc.get("enabled", True):
        return place_md, [], None

    chains = build_recommend_chains(
        cfg,
        picked,
        rejects,
        phase_id=phase_id,
        bet_ids=bet_ids,
        light_by_key=light_by_key,
        light_payload=light_payload,
        blocked=blocked,
        block_reason=block_reason,
    )
    path = append_reasoning_chains(cfg, chains) if chains else reasoning_chains_path(cfg)

    md = place_md
    if rc.get("place_md_section", True):
        section = format_reasoning_md(chains)
        # Drop prior chain sections (Reasoning and/or Near-miss), then append
        md = re.sub(r"(?ms)^## Reasoning\s*\n.*?(?=^## |\Z)", "", md, count=1)
        md = re.sub(
            r"(?ms)^## Near-miss / Rejected\s*\n.*?(?=^## |\Z)",
            "",
            md,
            count=1,
        )
        md = md.rstrip() + "\n\n" + section
    return md, chains, path
