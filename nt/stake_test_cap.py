"""
Temporary FEH 10 NOK test stake cap.

Config: selection.test_stake_cap
State:  data/state/feh_test_cap.json (configurable)

Absolute-last ceiling on seat stakes after all portfolio mutations
(rebalance, EXPLORE_REGIME clamp, whole-krone, run-sum). Does not change
capital_v2 unit sizing, phase ladder, or grade_mult formulas.

Counter increments only on place-ack (Pending → ConfirmedPlaced) for bets
whose notes carry TEST_CAP:<system_tag> (legacy FEH_TEST_CAP: also accepted).
Pre-tag untagged acks are excluded.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from nt.paths import resolve

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
DEFAULT_STATE_REL = "data/state/feh_test_cap.json"
CONSTRAINT_TAG = "feh_test_cap_10nok"
NOTE_TAG_PREFIX = "TEST_CAP:"
LEGACY_NOTE_TAG_PREFIX = "FEH_TEST_CAP:"


def stake_test_cap_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Normalized selection.test_stake_cap block with defaults."""
    raw = {}
    if isinstance(cfg, dict):
        sel = cfg.get("selection") or {}
        if isinstance(sel, dict):
            raw = dict(sel.get("test_stake_cap") or {})
    return {
        "enabled": bool(raw.get("enabled", False)),
        "max_bets": int(raw.get("max_bets") or 10),
        "max_stake_nok": float(raw.get("max_stake_nok") or 10.0),
        "system_tag": str(raw.get("system_tag") or "feh_v1").strip() or "feh_v1",
        "state_path": str(raw.get("state_path") or DEFAULT_STATE_REL),
    }


def state_path(cfg: dict[str, Any] | None) -> Path:
    """Resolve path to feh_test_cap.json."""
    tsc = stake_test_cap_cfg(cfg)
    rel = tsc["state_path"]
    if isinstance(cfg, dict):
        paths = cfg.get("paths") or {}
        if paths.get("feh_test_cap_json"):
            from nt.config import path_from_config

            return path_from_config(cfg, "feh_test_cap_json")
        # Prefer under state_dir when relative default
        if paths.get("state_dir") and rel in (DEFAULT_STATE_REL, "feh_test_cap.json"):
            from nt.config import path_from_config

            return path_from_config(cfg, "state_dir") / "feh_test_cap.json"
    p = Path(rel)
    return p if p.is_absolute() else resolve(rel)


def _default_state(tsc: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "enabled": bool(tsc.get("enabled", True)),
        "max_bets": int(tsc.get("max_bets") or 10),
        "max_stake_nok": float(tsc.get("max_stake_nok") or 10.0),
        "n_placed": 0,
        "bet_ids": [],
        "system_tag": str(tsc.get("system_tag") or "feh_v1"),
        "excluded_bet_ids": [],
    }


def load_state(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """
    Load counter state. Missing file → fail-closed safety:
    create with n_placed=0 so cap is active when config enables it.
    system_tag mismatch resets n_placed for the new tag.
    """
    tsc = stake_test_cap_cfg(cfg)
    path = state_path(cfg)
    state = _default_state(tsc)
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                state["n_placed"] = int(raw.get("n_placed") or 0)
                state["bet_ids"] = list(raw.get("bet_ids") or [])
                state["excluded_bet_ids"] = list(raw.get("excluded_bet_ids") or [])
                prev_tag = str(raw.get("system_tag") or "").strip()
                if prev_tag and prev_tag != state["system_tag"]:
                    # New system_tag resets counter for the new window
                    state["n_placed"] = 0
                    state["bet_ids"] = []
                    # keep excluded history optional
                elif prev_tag:
                    state["system_tag"] = prev_tag
                if raw.get("max_bets") is not None:
                    # Prefer live config for max_bets / max_stake; state mirrors for audit
                    pass
                if raw.get("schema_version") is not None:
                    state["schema_version"] = int(raw.get("schema_version") or SCHEMA_VERSION)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("feh_test_cap state unreadable (%s); using n_placed=0", e)
    # Always mirror live config knobs
    state["enabled"] = bool(tsc["enabled"])
    state["max_bets"] = int(tsc["max_bets"])
    state["max_stake_nok"] = float(tsc["max_stake_nok"])
    state["system_tag"] = str(tsc["system_tag"])
    # Persist missing file so desk sees the counter
    if not path.is_file() and tsc["enabled"]:
        try:
            save_state(cfg, state)
        except OSError as e:
            logger.warning("could not create feh_test_cap state: %s", e)
    return state


def save_state(cfg: dict[str, Any] | None, state: dict[str, Any]) -> Path:
    path = state_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": int(state.get("schema_version") or SCHEMA_VERSION),
        "enabled": bool(state.get("enabled", True)),
        "max_bets": int(state.get("max_bets") or 10),
        "max_stake_nok": float(state.get("max_stake_nok") or 10.0),
        "n_placed": int(state.get("n_placed") or 0),
        "bet_ids": list(state.get("bet_ids") or []),
        "system_tag": str(state.get("system_tag") or "feh_v1"),
        "excluded_bet_ids": list(state.get("excluded_bet_ids") or []),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def cap_enabled_from_cfg(cfg: dict[str, Any] | None) -> bool:
    """
    Best-effort read of selection.test_stake_cap.enabled. Never raises.

    Used for fail-closed decisions when the full module path may be broken.
    """
    try:
        return bool(stake_test_cap_cfg(cfg).get("enabled"))
    except Exception:
        try:
            raw = ((cfg or {}).get("selection") or {}).get("test_stake_cap")
            if isinstance(raw, dict):
                return bool(raw.get("enabled", False))
        except Exception:
            pass
        return False


def is_test_cap_active(cfg: dict[str, Any] | None, state: dict[str, Any] | None = None) -> bool:
    """
    True when config enables cap and n_placed < max_bets.

    Clip gate shares ``enabled`` with tagging (should_tag_pending) so the
    temporary window always advances via place-ack tags and can expire.
    """
    tsc = stake_test_cap_cfg(cfg)
    if not tsc["enabled"]:
        return False
    st = state if state is not None else load_state(cfg)
    n = int(st.get("n_placed") or 0)
    max_b = int(tsc["max_bets"])
    return n < max_b


def max_stake_when_active(
    cfg: dict[str, Any] | None, state: dict[str, Any] | None = None
) -> float | None:
    """Return max_stake_nok if cap is active, else None."""
    if not is_test_cap_active(cfg, state):
        return None
    tsc = stake_test_cap_cfg(cfg)
    return float(tsc["max_stake_nok"])


def feh_place_owning(cfg: dict[str, Any] | None) -> bool:
    """True when FEH owns place grade (triple gate). Informational only for cap."""
    try:
        from nt.evidence_hierarchy.score import place_uses_saef

        return bool(place_uses_saef(cfg))
    except Exception:
        return False


def should_tag_pending(cfg: dict[str, Any] | None) -> bool:
    """
    Tag Pending when test_stake_cap.enabled (system_tag path active).

    Aligned with clip: both use ``enabled`` so notes always carry
    TEST_CAP:<system_tag> whenever stakes may be clipped, the place-ack
    counter advances, and the 10-bet window can expire. Does **not** require
    FEH place-owning (avoids permanent 10 NOK era if shadow_mode flips while
    cap remains enabled). Tagging always applies when clip is applied.
    """
    return cap_enabled_from_cfg(cfg)


def system_tag_note(system_tag: str) -> str:
    return f"{NOTE_TAG_PREFIX}{system_tag}"


def display_cap_note(n_placed: int, max_bets: int, max_stake_nok: float) -> str:
    return f"{NOTE_TAG_PREFIX}{int(max_stake_nok)}NOK ({int(n_placed)}/{int(max_bets)})"


def notes_have_system_tag(notes: str | None, system_tag: str) -> bool:
    """True if notes carry TEST_CAP:<tag> or legacy FEH_TEST_CAP:<tag>."""
    if not notes or not system_tag:
        return False
    s = str(notes)
    if f"{NOTE_TAG_PREFIX}{system_tag}" in s:
        return True
    # Accept legacy FEH-branded prefix for place-ack counting
    if f"{LEGACY_NOTE_TAG_PREFIX}{system_tag}" in s:
        return True
    return False


def annotate_notes_for_cap(
    notes: str | None,
    cfg: dict[str, Any] | None,
    *,
    state: dict[str, Any] | None = None,
    max_len: int = 400,
) -> str:
    """
    Prepend TEST_CAP tags so they survive notes truncation.
    - Always when enabled: TEST_CAP:<system_tag>
    - When cap active (n_placed < max): TEST_CAP:10NOK (k/10)
    """
    base = (notes or "").strip()
    if not should_tag_pending(cfg):
        return base[:max_len]
    tsc = stake_test_cap_cfg(cfg)
    st = state if state is not None else load_state(cfg)
    tags: list[str] = []
    tag = system_tag_note(tsc["system_tag"])
    if tag not in base:
        tags.append(tag)
    if is_test_cap_active(cfg, st):
        disp = display_cap_note(
            int(st.get("n_placed") or 0),
            int(tsc["max_bets"]),
            float(tsc["max_stake_nok"]),
        )
        if disp not in base:
            tags.append(disp)
    if not tags:
        return base[:max_len]
    prefix = "; ".join(tags)
    # Prefer keeping tags; trim body if needed
    if not base:
        return prefix[:max_len]
    combined = f"{prefix}; {base}"
    return combined[:max_len]


def apply_test_stake_cap_to_picked(
    picked: list[Any],
    cfg: dict[str, Any] | None,
    *,
    state: dict[str, Any] | None = None,
) -> int:
    """
    Absolute-last clip: for each seat, stake_nok = min(stake, max_stake_nok)
    when cap is active. Syncs stake_decision.final_stake_nok and appends
    constraints_applied feh_test_cap_10nok. Leaves unit_size_nok / grade_mult
    / recommended_stake_nok inputs unchanged.

    Tags notes with TEST_CAP whenever enabled (same gate as clip path so
    tagging always occurs when clip is applied).

    Returns number of seats whose stake was reduced.
    """
    st = state if state is not None else load_state(cfg)
    tsc = stake_test_cap_cfg(cfg)
    active = is_test_cap_active(cfg, st)
    # Tag whenever enabled; clip only while active window (n < max)
    do_tag = should_tag_pending(cfg)
    cap = float(tsc["max_stake_nok"]) if active else None
    n_clipped = 0

    for rec in picked:
        # Tag notes whenever enabled (eligibility for counter) — always when clipping
        if do_tag:
            notes = getattr(rec, "notes", None) or ""
            new_notes = annotate_notes_for_cap(notes, cfg, state=st)
            if new_notes != notes:
                rec.notes = new_notes

        if cap is None:
            # Tag-only path (enabled but window full) still records system_tag sidecar
            sd = getattr(rec, "stake_decision", None)
            if isinstance(sd, dict) and do_tag:
                sd = dict(sd)
                inputs = dict(sd.get("inputs") or {})
                inputs["feh_system_tag"] = tsc["system_tag"]
                sd["inputs"] = inputs
                rec.stake_decision = sd
            continue

        stake = float(getattr(rec, "stake_nok", 0) or 0)
        capped = float(int(cap)) if abs(cap - int(cap)) < 1e-9 else float(cap)
        if stake > cap + 1e-9:
            rec.stake_nok = capped
            n_clipped += 1
        else:
            # Keep whole-krone stake; only enforce ceiling
            rec.stake_nok = stake

        sd = getattr(rec, "stake_decision", None)
        if isinstance(sd, dict):
            sd = dict(sd)
            final = min(float(getattr(rec, "stake_nok", 0) or 0), cap)
            if abs(final - int(final)) < 1e-9:
                rec.stake_nok = float(int(final))
            else:
                rec.stake_nok = final
            sd["final_stake_nok"] = rec.stake_nok
            caps = list(sd.get("constraints_applied") or [])
            if CONSTRAINT_TAG not in caps:
                caps.append(CONSTRAINT_TAG)
            sd["constraints_applied"] = caps
            # Sidecar for ack / audit — do not alter unit_size_nok / grade_mult
            inputs = dict(sd.get("inputs") or {})
            inputs["feh_system_tag"] = tsc["system_tag"]
            inputs["feh_test_cap_active"] = True
            inputs["feh_test_cap_max_nok"] = cap
            sd["inputs"] = inputs
            rec.stake_decision = sd

    return n_clipped


def run_absolute_last_stake_cap(
    picked: list[Any],
    cfg: dict[str, Any] | None,
    *,
    state: dict[str, Any] | None = None,
) -> int:
    """
    Portfolio/recommend entry for absolute-last clip + tags.

    Fail-closed when selection.test_stake_cap.enabled: any failure re-raises
    RuntimeError so the 10 NOK ceiling cannot silently disappear. When disabled,
    errors are logged and the call is a no-op.
    """
    try:
        n = apply_test_stake_cap_to_picked(picked, cfg, state=state)
        # Post-condition: active window must leave no seat above max
        if is_test_cap_active(cfg, state):
            assert_stakes_within_cap(picked, cfg)
        return n
    except RuntimeError:
        raise
    except Exception as e:
        logger.exception("FEH test stake cap absolute-last failed")
        if cap_enabled_from_cfg(cfg):
            raise RuntimeError(f"test stake cap failed closed: {e}") from e
        return 0


def inject_seat_max(seat_cap: float, cfg: dict[str, Any] | None, state: dict[str, Any] | None = None) -> float:
    """min(seat_cap, max_stake_nok) when cap active."""
    cap = max_stake_when_active(cfg, state)
    if cap is None:
        return float(seat_cap)
    return min(float(seat_cap), float(cap))


def clip_stake_nok(stake: float, cfg: dict[str, Any] | None, state: dict[str, Any] | None = None) -> float:
    """Clip a single stake (e.g. combo ticket) when cap active."""
    cap = max_stake_when_active(cfg, state)
    if cap is None:
        return float(stake)
    s = float(stake)
    if s > cap + 1e-9:
        if abs(cap - int(cap)) < 1e-9:
            return float(int(cap))
        return float(cap)
    return s


def clip_stake_nok_fail_closed(
    stake: float, cfg: dict[str, Any] | None, state: dict[str, Any] | None = None
) -> float:
    """
    Combo/ticket clip entry. Fail-closed when cap enabled — never silently
    skip the ceiling on error.
    """
    try:
        return clip_stake_nok(stake, cfg, state)
    except Exception as e:
        logger.exception("FEH test stake cap clip failed")
        if cap_enabled_from_cfg(cfg):
            raise RuntimeError(f"test stake cap failed closed: {e}") from e
        return float(stake)


def assert_stakes_within_cap(picked: list[Any], cfg: dict[str, Any] | None) -> None:
    """Raise if any seat exceeds max when cap is active (recommend hard check)."""
    cap = max_stake_when_active(cfg)
    if cap is None:
        return
    for rec in picked:
        stake = float(getattr(rec, "stake_nok", 0) or 0)
        if stake > cap + 1e-9:
            raise RuntimeError(
                f"FEH test stake cap active: stake {stake} NOK exceeds max {cap} NOK "
                f"for {getattr(rec, 'match', '?')} / {getattr(rec, 'selection', '?')}"
            )


def fail_closed_hook_error(cfg: dict[str, Any] | None, err: BaseException, *, where: str) -> None:
    """
    Call-site helper after import/apply failure.

    Re-raises RuntimeError when cap is enabled (or enabled cannot be read →
    treat as enabled). When disabled, logs and returns so callers may continue.
    """
    logger.exception("FEH test stake cap hook failed at %s", where)
    enabled = cap_enabled_from_cfg(cfg)
    if not enabled:
        # Double-check raw cfg if helper path was the failure
        try:
            raw = ((cfg or {}).get("selection") or {}).get("test_stake_cap")
            if isinstance(raw, dict) and raw.get("enabled"):
                enabled = True
        except Exception:
            # Cannot determine — fail closed for real-money ceiling safety
            enabled = True
    if enabled:
        raise RuntimeError(f"test stake cap failed closed ({where}): {err}") from err


def record_placed_bet(
    cfg: dict[str, Any] | None,
    bet_id: str,
    notes: str | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    place_ack hook: count toward n_placed only if notes carry TEST_CAP:<system_tag>
    (or legacy FEH_TEST_CAP:<system_tag>). Idempotent on bet_id. Untagged → excluded.
    """
    tsc = stake_test_cap_cfg(cfg)
    bid = (bet_id or "").strip()
    result: dict[str, Any] = {
        "bet_id": bid,
        "counted": False,
        "excluded": False,
        "already_counted": False,
        "n_placed": None,
        "active": None,
        "log": "",
    }
    if not bid:
        result["log"] = "empty bet_id"
        return result
    if not tsc["enabled"]:
        result["log"] = "test_stake_cap disabled"
        return result

    st = load_state(cfg)
    tag = tsc["system_tag"]
    result["n_placed"] = int(st.get("n_placed") or 0)
    result["active"] = is_test_cap_active(cfg, st)

    if bid in (st.get("bet_ids") or []):
        result["already_counted"] = True
        result["counted"] = True
        result["log"] = f"already counted bet_id={bid}"
        return result
    if bid in (st.get("excluded_bet_ids") or []):
        result["excluded"] = True
        result["log"] = f"already excluded bet_id={bid}"
        return result

    if notes_have_system_tag(notes, tag):
        st["bet_ids"] = list(st.get("bet_ids") or []) + [bid]
        st["n_placed"] = int(st.get("n_placed") or 0) + 1
        result["counted"] = True
        result["n_placed"] = st["n_placed"]
        result["active"] = is_test_cap_active(cfg, st)
        result["log"] = f"counted TEST_CAP:{tag} bet_id={bid} n_placed={st['n_placed']}"
        if not dry_run:
            save_state(cfg, st)
        logger.info(result["log"])
    else:
        st["excluded_bet_ids"] = list(st.get("excluded_bet_ids") or []) + [bid]
        result["excluded"] = True
        result["log"] = (
            f"excluded untagged place-ack bet_id={bid} "
            f"(missing {system_tag_note(tag)}; pre-FEH or hand-edited)"
        )
        if not dry_run:
            save_state(cfg, st)
        logger.info(result["log"])

    return result


def status_line(cfg: dict[str, Any] | None) -> str:
    """Human line for status.md observability."""
    tsc = stake_test_cap_cfg(cfg)
    if not tsc["enabled"]:
        return "test_cap: disabled"
    st = load_state(cfg)
    n = int(st.get("n_placed") or 0)
    max_b = int(tsc["max_bets"])
    active = "active" if is_test_cap_active(cfg, st) else "inactive"
    return (
        f"test_cap: {n}/{max_b} {active} (max {tsc['max_stake_nok']:g} NOK) "
        f"| system_tag: {tsc['system_tag']}"
    )


__all__ = [
    "CONSTRAINT_TAG",
    "LEGACY_NOTE_TAG_PREFIX",
    "NOTE_TAG_PREFIX",
    "annotate_notes_for_cap",
    "apply_test_stake_cap_to_picked",
    "assert_stakes_within_cap",
    "cap_enabled_from_cfg",
    "clip_stake_nok",
    "clip_stake_nok_fail_closed",
    "display_cap_note",
    "fail_closed_hook_error",
    "feh_place_owning",
    "inject_seat_max",
    "is_test_cap_active",
    "load_state",
    "max_stake_when_active",
    "notes_have_system_tag",
    "record_placed_bet",
    "run_absolute_last_stake_cap",
    "save_state",
    "should_tag_pending",
    "state_path",
    "status_line",
    "system_tag_note",
    "stake_test_cap_cfg",
]
