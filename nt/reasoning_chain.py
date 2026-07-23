from __future__ import annotations

"""
Minimal reasoning-chain dump for recommend (dry-run OK).

Append-only JSONL: data/state/reasoning_chains.jsonl
PLACE_THESE.md section: ## Reasoning

Does not invent p_model, stakes, or bankroll math — only records what
recommend / light already computed.
"""

import json
import re
from pathlib import Path
from typing import Any

from nt.bets_io import utc_now
from nt.config import path_from_config
from nt.paths import resolve

SCHEMA_VERSION = 1


def reasoning_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = dict(cfg.get("reasoning") or {})
    defaults = {
        "enabled": True,
        "jsonl": "data/state/reasoning_chains.jsonl",
        "max_near_miss": 8,
        "near_miss_ev_slack": 0.04,  # include rejects within this of clearing EV
        "place_md_section": True,
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


def _light_from_notes_or_dict(notes: str = "", light: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(light, dict):
        for k in (
            "verdict",
            "promotion_score",
            "promo_score",
            "promote_to_deep",
            "rough_ev_note",
            "notes",
            "preferred",
            "short_main",
        ):
            if light.get(k) is not None:
                out[k if k != "promo_score" else "promotion_score"] = light.get(k)
    n = notes or ""
    if "promo_score=" in n and "promotion_score" not in out:
        try:
            out["promotion_score"] = float(
                n.split("promo_score=")[-1].split()[0].split("|")[0].rstrip(";")
            )
        except (TypeError, ValueError, IndexError):
            pass
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
    Build a chain for a light near-miss or portfolio reject close to the bar.
    """
    notes = str(row.get("notes") or row.get("rough_ev_note") or "")
    reason = str(row.get("reason") or row.get("reject_reason") or "")
    p_model = _as_float(row.get("p_model"))
    odds = _as_float(row.get("decimal_odds") if row.get("decimal_odds") is not None else row.get("odds"))
    ev = _as_float(row.get("ev"))
    hair = _as_float(haircut if haircut is not None else row.get("haircut"))
    ev_h = None
    if p_model is not None and odds is not None and hair is not None:
        from nt.evidence import ev_after_haircut

        ev_h = round(ev_after_haircut(p_model, odds, hair), 4)

    chain: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "ts": utc_now(),
        "kind": "near_miss",
        "source": source,
        "match": str(row.get("match") or ""),
        "selection": str(row.get("selection") or ""),
        "decimal_odds": odds,
        "sport": str(row.get("sport") or ""),
        "market_type": str(row.get("market_type") or ""),
        "grade": str(row.get("grade") or ""),
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
        "light": _light_from_notes_or_dict(notes, light or row.get("light")),
        "notes": (notes or reason)[:400],
    }
    return chain


def is_near_miss_reject(row: dict[str, Any], *, slack: float = 0.04) -> bool:
    """Heuristic: reject with EV present and reason suggesting EV/floor miss."""
    if not isinstance(row, dict):
        return False
    reason = str(row.get("reason") or "").lower()
    ev = _as_float(row.get("ev"))
    # Explicit near-miss tags from light research
    if row.get("near_miss") or row.get("kind") == "near_miss":
        return True
    if "promo_score" in reason or "light" in reason:
        return True
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
            )
        )
    # Has EV: prefer rows that failed EV / gate bars (not pure no-p_model noise)
    if "no p_model" in reason:
        return False
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
        )
    ):
        return True
    # Within slack of zero EV still interesting
    return abs(float(ev)) <= float(slack) + 0.05


def select_near_misses(
    rejects: list[Any],
    *,
    max_n: int = 8,
    slack: float = 0.04,
) -> list[dict[str, Any]]:
    rows = [r for r in rejects if isinstance(r, dict) and is_near_miss_reject(r, slack=slack)]
    # Prefer higher EV (closest to clearing) then mid-band odds
    def _key(r: dict[str, Any]) -> tuple:
        ev = _as_float(r.get("ev"))
        odds = _as_float(r.get("decimal_odds") if r.get("decimal_odds") is not None else r.get("odds"))
        mid = 0
        if odds is not None and 1.85 <= odds <= 2.60:
            mid = 1
        return (ev if ev is not None else -99.0, mid)

    rows.sort(key=_key, reverse=True)
    return rows[: max(0, int(max_n))]


def format_reasoning_md(chains: list[dict[str, Any]]) -> str:
    """Markdown ## Reasoning section for PLACE_THESE.md."""
    lines = ["## Reasoning", ""]
    if not chains:
        lines.append("_No reasoning chains (empty slip / no near-misses)._")
        lines.append("")
        return "\n".join(lines)

    picks = [c for c in chains if c.get("kind") == "pick"]
    misses = [c for c in chains if c.get("kind") != "pick"]

    if picks:
        lines.append(f"**Picks ({len(picks)})**")
        lines.append("")
        for i, c in enumerate(picks, 1):
            lines.extend(_format_one_md(i, c))
    if misses:
        lines.append(f"**Near-misses ({len(misses)})**")
        lines.append("")
        for i, c in enumerate(misses, 1):
            lines.extend(_format_one_md(i, c))
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
    controls = c.get("controls") or {}
    light = c.get("light") or {}
    out = [f"### {i}. {title}", ""]
    if bits:
        out.append("- " + " · ".join(bits))
    if controls:
        ctrl = ", ".join(f"{k}={v}" for k, v in controls.items())
        out.append(f"- controls: {ctrl}")
    if light:
        lite = ", ".join(f"{k}={v}" for k, v in light.items())
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
) -> list[dict[str, Any]]:
    """
    Build pick + near-miss chains for one recommend run.
    """
    rc = reasoning_cfg(cfg)
    if not rc.get("enabled", True):
        return []
    haircut = None
    try:
        haircut = float((cfg.get("selection") or {}).get("probability_haircut", 0.03))
    except (TypeError, ValueError):
        haircut = 0.03

    light_map = light_by_key or {}
    chains: list[dict[str, Any]] = []
    ids = list(bet_ids or [])
    for i, p in enumerate(picked or []):
        key = _line_key(_pick_attr(p, "match"), _pick_attr(p, "selection"))
        bid = ids[i] if i < len(ids) else None
        chains.append(
            build_chain_from_pick(
                p,
                haircut=haircut,
                phase_id=phase_id,
                bet_id=bid,
                light=light_map.get(key),
            )
        )

    misses = select_near_misses(
        list(rejects or []),
        max_n=int(rc.get("max_near_miss") or 8),
        slack=float(rc.get("near_miss_ev_slack") or 0.04),
    )
    for row in misses:
        key = _line_key(row.get("match"), row.get("selection"))
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


def _line_key(match: Any, selection: Any) -> str:
    return f"{str(match or '').strip().lower()}||{str(selection or '').strip().lower()}"


def dump_reasoning_for_recommend(
    cfg: dict[str, Any],
    picked: list[Any],
    rejects: list[Any] | None,
    *,
    place_md: str,
    phase_id: str | None = None,
    bet_ids: list[str] | None = None,
    light_by_key: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, list[dict[str, Any]], Path | None]:
    """
    Append chains to JSONL and inject ## Reasoning into PLACE_THESE markdown.

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
    )
    path = append_reasoning_chains(cfg, chains) if chains else reasoning_chains_path(cfg)

    md = place_md
    if rc.get("place_md_section", True):
        section = format_reasoning_md(chains)
        # Replace existing ## Reasoning or append
        if re.search(r"(?m)^## Reasoning\s*$", md):
            md = re.sub(
                r"(?ms)^## Reasoning\s*\n.*?(?=^## |\Z)",
                section + "\n",
                md,
                count=1,
            )
        else:
            md = md.rstrip() + "\n\n" + section
    return md, chains, path
