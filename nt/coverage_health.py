"""
Coverage Health + clearability funnel (HV Research Regime v3 PR6).

Writes data/state/coverage_health.json on board/recommend.
Emits starvation_kind SSOT for Lumina empty-slip taxonomy.

Funnel metrics (never invent p_model):
  n_raw_ev_pass, median_raw_ev, clearable_track_share, second_pass_ran

starvation_kind:
  none | research_starvation | coverage_critical | clearability_miss
  | honest_no_edge | risk_block
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from nt.bets_io import utc_now
from nt.config import path_from_config
from nt.evidence import ev_after_haircut

SCHEMA_VERSION = 2

STARVATION_KINDS = (
    "none",
    "research_starvation",
    "coverage_critical",
    "clearability_miss",
    "honest_no_edge",
    "risk_block",
)


def coverage_health_cfg(cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    cfg = cfg or {}
    research = dict(cfg.get("research") or {})
    raw = dict(research.get("coverage_health") or {})
    tiers = dict(research.get("tiers") or {})
    return {
        "warn_deep_pct": float(raw.get("warn_deep_pct") if raw.get("warn_deep_pct") is not None else 25),
        "critical_deep_pct": float(
            raw.get("critical_deep_pct") if raw.get("critical_deep_pct") is not None else 15
        ),
        "warn_survivable_pct": float(
            raw.get("warn_survivable_pct") if raw.get("warn_survivable_pct") is not None else 45
        ),
        "critical_survivable_pct": float(
            raw.get("critical_survivable_pct")
            if raw.get("critical_survivable_pct") is not None
            else 30
        ),
        "critical_mid_unresearched": int(
            raw.get("critical_mid_unresearched")
            if raw.get("critical_mid_unresearched") is not None
            else 5
        ),
        "warn_mid_unresearched": int(
            raw.get("warn_mid_unresearched") if raw.get("warn_mid_unresearched") is not None else 3
        ),
        "soft_gate": bool(raw.get("soft_gate", True)),
        "auto_expand_deep_queue": bool(raw.get("auto_expand_deep_queue", True)),
        "preferred_odds_lo": float(tiers.get("preferred_odds_lo") or 1.85),
        "preferred_odds_hi": float(tiers.get("preferred_odds_hi") or 2.60),
        "alt_preferred_odds_lo": float(
            tiers.get("alt_preferred_odds_lo") or tiers.get("short_chalk_odds") or 1.80
        ),
    }


def coverage_health_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("coverage_health_json"):
        return path_from_config(cfg, "coverage_health_json")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "coverage_health.json"


def load_coverage_health(cfg: dict[str, Any]) -> dict[str, Any] | None:
    path = coverage_health_path(cfg)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_coverage_health(cfg: dict[str, Any], payload: dict[str, Any]) -> Path:
    path = coverage_health_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _haircut(cfg: Mapping[str, Any]) -> float:
    sel = dict(cfg.get("selection") or {})
    try:
        return float(sel.get("probability_haircut") if sel.get("probability_haircut") is not None else 0.03)
    except (TypeError, ValueError):
        return 0.03


def _min_ev_raw_pass(cfg: Mapping[str, Any]) -> float:
    """Raw EV pass bar for funnel (standard min_ev; no learning boosts)."""
    sel = dict(cfg.get("selection") or {})
    try:
        return float(sel.get("standard_min_ev") if sel.get("standard_min_ev") is not None else 0.02)
    except (TypeError, ValueError):
        return 0.02


def _odds_of(row: Any) -> float:
    if isinstance(row, Mapping):
        for k in ("decimal_odds", "odds"):
            if row.get(k) is not None:
                try:
                    return float(row[k])
                except (TypeError, ValueError):
                    pass
        return 0.0
    for attr in ("decimal_odds", "odds"):
        v = getattr(row, attr, None)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return 0.0


def _p_model_of(row: Any) -> float | None:
    if isinstance(row, Mapping):
        p = row.get("p_model")
        if p is None and isinstance(row.get("evidence"), Mapping):
            p = row["evidence"].get("p_model")
    else:
        p = getattr(row, "p_model", None)
        if p is None:
            ev = getattr(row, "evidence", None)
            if isinstance(ev, Mapping):
                p = ev.get("p_model")
    if p is None:
        return None
    try:
        return float(p)
    except (TypeError, ValueError):
        return None


def _has_deep(row: Any) -> bool:
    """Deep pack present: p_model or evidence attached."""
    if _p_model_of(row) is not None:
        return True
    if isinstance(row, Mapping):
        if row.get("has_p_model") or row.get("has_evidence"):
            return True
        if row.get("evidence"):
            return True
        return False
    if getattr(row, "has_p_model", False) or getattr(row, "has_evidence", False):
        return True
    if getattr(row, "evidence", None):
        return True
    return False


def _selection_of(row: Any) -> str:
    if isinstance(row, Mapping):
        return str(row.get("selection") or "")
    return str(getattr(row, "selection", "") or "")


def _family_of(row: Any) -> str:
    if isinstance(row, Mapping):
        return str(row.get("market_family") or row.get("family") or row.get("market_type") or "")
    return str(
        getattr(row, "market_family", None)
        or getattr(row, "market_type", None)
        or ""
    )


def _is_preferred(row: Any, hcfg: dict[str, Any]) -> bool:
    odds = _odds_of(row)
    sel = _selection_of(row)
    fam = _family_of(row)
    pref_lo = float(hcfg["preferred_odds_lo"])
    alt_lo = float(hcfg["alt_preferred_odds_lo"])
    try:
        from nt.light_research import is_preferred_line

        return bool(
            is_preferred_line(
                sel,
                odds,
                fam,
                preferred_odds_lo=pref_lo,
                alt_preferred_odds_lo=alt_lo,
            )
        )
    except Exception:
        return odds + 1e-12 >= pref_lo


def _in_mid_band(odds: float, hcfg: dict[str, Any]) -> bool:
    lo = float(hcfg["preferred_odds_lo"])
    hi = float(hcfg["preferred_odds_hi"])
    return lo <= float(odds) <= hi


def _read_second_pass_flags(cfg: dict[str, Any]) -> dict[str, Any]:
    """Read second_pass flags from deep_queue.json when present (PR2 may set them)."""
    out = {"second_pass_ran": False, "second_pass_completed": False, "mode": None}
    try:
        from nt.deep_queue_state import load_deep_queue_state

        st = load_deep_queue_state(cfg)
    except Exception:
        st = None
    if not isinstance(st, dict):
        return out
    mode = str(st.get("mode") or "").lower()
    out["mode"] = mode or None
    if mode in ("refresh", "second_pass", "second-pass"):
        out["second_pass_ran"] = True
        out["second_pass_completed"] = bool(st.get("second_pass_completed", True))
    if st.get("second_pass_ran") is not None:
        out["second_pass_ran"] = bool(st.get("second_pass_ran"))
    if st.get("second_pass_completed") is not None:
        out["second_pass_completed"] = bool(st.get("second_pass_completed"))
    return out


def compute_funnel_metrics(
    rows: Sequence[Any],
    cfg: Mapping[str, Any],
    *,
    second_pass_ran: bool | None = None,
    second_pass_completed: bool | None = None,
) -> dict[str, Any]:
    """
    Funnel KPIs from attached packs vs board odds using ev_after_haircut.

    Does not require dual-track (PR2). clearable_track_share ≈ n_raw_ev_pass / n_packs_with_p.
    """
    haircut = _haircut(cfg)
    min_ev = _min_ev_raw_pass(cfg)
    raw_evs: list[float] = []
    n_pass = 0
    for row in rows:
        p = _p_model_of(row)
        odds = _odds_of(row)
        if p is None or odds <= 1.0:
            continue
        raw = float(ev_after_haircut(float(p), float(odds), haircut))
        raw_evs.append(raw)
        if raw + 1e-12 >= min_ev:
            n_pass += 1

    n_packs = len(raw_evs)
    median = float(statistics.median(raw_evs)) if raw_evs else None
    share = (n_pass / n_packs) if n_packs else 0.0

    sp_ran = bool(second_pass_ran) if second_pass_ran is not None else False
    sp_done = bool(second_pass_completed) if second_pass_completed is not None else False

    return {
        "n_packs_with_p": n_packs,
        "n_raw_ev_pass": n_pass,
        "median_raw_ev": round(median, 4) if median is not None else None,
        "clearable_track_share": round(share, 4),
        "second_pass_ran": sp_ran,
        "second_pass_completed": sp_done,
        "raw_ev_min_ev_bar": min_ev,
        "haircut": haircut,
    }


def classify_starvation_kind(
    *,
    level: str,
    mid_unresearched_n: int,
    shortlist_with_deep_n: int,
    n_raw_ev_pass: int,
    n_picked: int = 0,
    second_pass_completed: bool = False,
    can_bet: bool | None = None,
    empty_slip_risk: bool = False,
) -> str:
    """
    Engine-emitted starvation_kind SSOT.

    Priority (fail-closed process first):
      risk_block → coverage_critical → research_starvation →
      clearability_miss → honest_no_edge → none
    """
    if can_bet is False and n_picked == 0:
        return "risk_block"

    lvl = str(level or "").lower()
    mid_u = int(mid_unresearched_n or 0)
    deep_n = int(shortlist_with_deep_n or 0)
    n_pass = int(n_raw_ev_pass or 0)

    if lvl == "critical" or (empty_slip_risk and mid_u > 0 and deep_n == 0):
        return "coverage_critical"

    # Research starvation: critical mid unresearched with thin deep coverage
    if mid_u > 0 and deep_n == 0:
        return "research_starvation"
    if mid_u > 0 and lvl in ("warn", "critical") and n_picked == 0:
        return "research_starvation"

    # After research: deep packs present, mid covered, zero raw EV clears
    if deep_n >= 1 and mid_u == 0 and n_pass == 0 and n_picked == 0:
        if second_pass_completed:
            return "honest_no_edge"
        return "clearability_miss"

    if n_picked == 0 and deep_n >= 1 and mid_u == 0 and n_pass == 0:
        # defensive fallback
        return "honest_no_edge" if second_pass_completed else "clearability_miss"

    return "none"


def compute_coverage_health(
    cfg: dict[str, Any],
    candidates: Sequence[Any] | None = None,
    *,
    shortlist: Sequence[Any] | None = None,
    source: str = "recommend",
    n_picked: int = 0,
    can_bet: bool | None = None,
    second_pass_ran: bool | None = None,
    second_pass_completed: bool | None = None,
    no_pmodel_reject_share: float | None = None,
) -> dict[str, Any]:
    """
    Compute Coverage Health + funnel metrics.

    shortlist preferred for deep/mid counts; falls back to candidates with
    evidence/p_model as pseudo-shortlist when shortlist omitted.
    """
    hcfg = coverage_health_cfg(cfg)
    rows_sl: list[Any] = list(shortlist) if shortlist is not None else []
    rows_all: list[Any] = list(candidates) if candidates is not None else list(rows_sl)

    if not rows_sl and rows_all:
        # Fallback: treat candidates that already have packs as shortlist context
        rows_sl = [r for r in rows_all if _has_deep(r)] or list(rows_all)

    shortlist_n = len(rows_sl)
    deep_rows = [r for r in rows_sl if _has_deep(r)]
    shortlist_with_deep_n = len(deep_rows)
    shortlist_deep_pct = (
        round(100.0 * shortlist_with_deep_n / shortlist_n, 2) if shortlist_n else 0.0
    )

    # Survivable deep: preferred / mid-band packs on shortlist
    surv_rows = [r for r in deep_rows if _is_preferred(r, hcfg) or _in_mid_band(_odds_of(r), hcfg)]
    deep_survivable_n = len(surv_rows)
    deep_survivable_pct = (
        round(100.0 * deep_survivable_n / shortlist_with_deep_n, 2)
        if shortlist_with_deep_n
        else 0.0
    )

    # Mid-band shortlist lines without deep pack
    mid_unresearched = [
        r
        for r in rows_sl
        if _in_mid_band(_odds_of(r), hcfg) and not _has_deep(r)
    ]
    mid_unresearched_n = len(mid_unresearched)

    # Level
    reasons: list[str] = []
    level = "ok"
    if shortlist_deep_pct < hcfg["critical_deep_pct"] or mid_unresearched_n >= hcfg[
        "critical_mid_unresearched"
    ]:
        level = "critical"
        if shortlist_deep_pct < hcfg["critical_deep_pct"]:
            reasons.append(
                f"shortlist_deep_pct {shortlist_deep_pct}% < critical {hcfg['critical_deep_pct']}%"
            )
        if mid_unresearched_n >= hcfg["critical_mid_unresearched"]:
            reasons.append(
                f"mid_unresearched_n {mid_unresearched_n} >= critical "
                f"{hcfg['critical_mid_unresearched']}"
            )
    elif shortlist_deep_pct < hcfg["warn_deep_pct"] or mid_unresearched_n >= hcfg[
        "warn_mid_unresearched"
    ]:
        level = "warn"
        if shortlist_deep_pct < hcfg["warn_deep_pct"]:
            reasons.append(
                f"shortlist_deep_pct {shortlist_deep_pct}% < warn {hcfg['warn_deep_pct']}%"
            )
        if mid_unresearched_n >= hcfg["warn_mid_unresearched"]:
            reasons.append(
                f"mid_unresearched_n {mid_unresearched_n} >= warn {hcfg['warn_mid_unresearched']}"
            )

    if shortlist_with_deep_n and deep_survivable_pct < hcfg["critical_survivable_pct"]:
        if level != "critical":
            level = "critical"
        reasons.append(
            f"deep_survivable_pct {deep_survivable_pct}% < critical "
            f"{hcfg['critical_survivable_pct']}%"
        )
    elif shortlist_with_deep_n and deep_survivable_pct < hcfg["warn_survivable_pct"]:
        if level == "ok":
            level = "warn"
        reasons.append(
            f"deep_survivable_pct {deep_survivable_pct}% < warn {hcfg['warn_survivable_pct']}%"
        )

    empty_slip_risk = level == "critical" or (
        mid_unresearched_n >= hcfg["warn_mid_unresearched"] and shortlist_with_deep_n == 0
    )

    # Funnel — use all candidates with p when available, else shortlist deep
    funnel_rows = rows_all if rows_all else deep_rows
    sp_flags = _read_second_pass_flags(cfg) if second_pass_ran is None else {
        "second_pass_ran": bool(second_pass_ran),
        "second_pass_completed": bool(
            second_pass_completed if second_pass_completed is not None else second_pass_ran
        ),
    }
    if second_pass_ran is not None:
        sp_flags["second_pass_ran"] = bool(second_pass_ran)
    if second_pass_completed is not None:
        sp_flags["second_pass_completed"] = bool(second_pass_completed)

    funnel = compute_funnel_metrics(
        funnel_rows,
        cfg,
        second_pass_ran=sp_flags.get("second_pass_ran"),
        second_pass_completed=sp_flags.get("second_pass_completed"),
    )

    starvation = classify_starvation_kind(
        level=level,
        mid_unresearched_n=mid_unresearched_n,
        shortlist_with_deep_n=shortlist_with_deep_n,
        n_raw_ev_pass=int(funnel["n_raw_ev_pass"]),
        n_picked=int(n_picked),
        second_pass_completed=bool(funnel.get("second_pass_completed")),
        can_bet=can_bet,
        empty_slip_risk=empty_slip_risk,
    )

    # Coverage overlay snapshot (effective active after hygiene no-op)
    force_cov_active = False
    force_cov_signal: dict[str, Any] | None = None
    force_cov_emitted = False
    force_cov_noop = False
    try:
        from nt.control_signals import active_coverage_priority_overlay

        # Pass provisional health for no-op decision
        provisional = {
            "level": level,
            "mid_unresearched_n": mid_unresearched_n,
        }
        ov = active_coverage_priority_overlay(cfg, coverage_health=provisional)
        force_cov_emitted = bool(ov.get("force_coverage_emitted") or ov.get("n_signals"))
        force_cov_noop = bool(ov.get("no_op"))
        force_cov_active = bool(ov.get("active") or ov.get("force_coverage_overlay_active"))
        if force_cov_emitted:
            force_cov_signal = {
                "target_odds_band": ov.get("target_odds_band"),
                "min_deep_packs": ov.get("min_deep_packs"),
                "prefer": ov.get("prefer"),
                "expires_at": ov.get("expires_at"),
                "sources": ov.get("sources"),
                "no_op": force_cov_noop,
            }
    except Exception:
        pass

    force_cl_active = False
    try:
        from nt.control_signals import active_clearability_priority_overlay

        cl_ov = active_clearability_priority_overlay(cfg)
        force_cl_active = bool(cl_ov.get("active") or cl_ov.get("force_clearability_active"))
    except Exception:
        pass

    clearability_block = {
        "n_raw_ev_pass": funnel["n_raw_ev_pass"],
        "median_raw_ev": funnel["median_raw_ev"],
        "clearable_track_share": funnel["clearable_track_share"],
        "second_pass_ran": funnel["second_pass_ran"],
        "second_pass_completed": funnel["second_pass_completed"],
        "n_packs_with_p": funnel["n_packs_with_p"],
        "raw_ev_min_ev_bar": funnel["raw_ev_min_ev_bar"],
        "haircut": funnel["haircut"],
        "force_clearability_active": force_cl_active,
    }

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "updated_at": utc_now(),
        "shortlist_n": shortlist_n,
        "shortlist_with_deep_n": shortlist_with_deep_n,
        "shortlist_deep_pct": shortlist_deep_pct,
        "deep_n": shortlist_with_deep_n,
        "deep_survivable_n": deep_survivable_n,
        "deep_survivable_pct": deep_survivable_pct,
        "mid_unresearched_n": mid_unresearched_n,
        "empty_slip_risk": empty_slip_risk,
        "level": level,
        "reasons": reasons,
        "soft_gate": bool(hcfg["soft_gate"]),
        "force_coverage_active": force_cov_active,
        "force_coverage_emitted": force_cov_emitted,
        "force_coverage_overlay_active": force_cov_active,
        "force_coverage_no_op": force_cov_noop,
        "force_coverage_signal": force_cov_signal,
        "force_clearability_active": force_cl_active,
        "starvation_kind": starvation,
        "n_picked": int(n_picked),
        "n_raw_ev_pass": funnel["n_raw_ev_pass"],
        "median_raw_ev": funnel["median_raw_ev"],
        "clearable_track_share": funnel["clearable_track_share"],
        "second_pass_ran": funnel["second_pass_ran"],
        "second_pass_completed": funnel["second_pass_completed"],
        "clearability": clearability_block,
        "funnel": {
            "n_raw_ev_pass": funnel["n_raw_ev_pass"],
            "median_raw_ev": funnel["median_raw_ev"],
            "clearable_track_share": funnel["clearable_track_share"],
            "second_pass_ran": funnel["second_pass_ran"],
            "second_pass_completed": funnel["second_pass_completed"],
            "n_packs_with_p": funnel["n_packs_with_p"],
        },
    }
    if no_pmodel_reject_share is not None:
        payload["no_pmodel_reject_share"] = float(no_pmodel_reject_share)
    return payload


def soft_gate_blocks_recommend(health: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    """True when Coverage Health critical and soft_gate enabled."""
    hcfg = coverage_health_cfg(cfg)
    if not hcfg.get("soft_gate", True):
        return False
    if health.get("soft_gate") is False:
        return False
    return str(health.get("level") or "").lower() == "critical"


def maybe_emit_force_coverage_from_health(
    cfg: dict[str, Any],
    health: Mapping[str, Any],
    *,
    n_picked: int = 0,
    no_pmodel_reject_share: float | None = None,
) -> dict[str, Any]:
    """
    Emit force_coverage_priority on research starvation (empty/near-empty slip
    with mid unresearched + high no-p_model share). Does not emit on pure
    clearability_miss (deep done, mid=0, EV fails).
    """
    from nt.control_signals import control_signals_cfg, emit_force_coverage_priority

    cs = control_signals_cfg(cfg)
    cov = cs["coverage_priority"]
    if not cov.get("enabled", True):
        return {"ok": False, "reason": "disabled"}

    mid_u = int(health.get("mid_unresearched_n") or 0)
    min_mid = int(cov.get("min_mid_unresearched") or 3)
    near_empty_max = int(cov.get("near_empty_max_picks") or 1)
    min_share = float(cov.get("min_no_pmodel_reject_share") or 0.70)

    sk = str(health.get("starvation_kind") or "")
    # Never use coverage force for pure clearability / honest no-edge
    if sk in ("clearability_miss", "honest_no_edge"):
        return {"ok": True, "emitted": False, "reason": "not_research_starvation"}

    share = no_pmodel_reject_share
    if share is None and health.get("no_pmodel_reject_share") is not None:
        share = float(health["no_pmodel_reject_share"])

    near_empty = int(n_picked) <= near_empty_max
    mid_pressure = mid_u >= min_mid
    level_crit = str(health.get("level") or "").lower() == "critical"
    share_hit = share is not None and float(share) >= min_share

    if not near_empty:
        return {"ok": True, "emitted": False, "reason": "not_near_empty"}
    if not (mid_pressure or level_crit or sk in ("research_starvation", "coverage_critical")):
        return {"ok": True, "emitted": False, "reason": "no_mid_pressure"}
    # Prefer share signal when available; otherwise mid/critical is enough
    if share is not None and not share_hit and not mid_pressure:
        return {"ok": True, "emitted": False, "reason": "share_below_threshold"}

    return emit_force_coverage_priority(
        cfg,
        source="research_starvation",
        reason=f"starvation_kind={sk}; mid_u={mid_u}; n_picked={n_picked}",
        mid_unresearched_n=mid_u,
        n_picked=int(n_picked),
    )


def update_coverage_health_on_recommend(
    cfg: dict[str, Any],
    candidates: Sequence[Any],
    *,
    shortlist: Sequence[Any] | None = None,
    n_picked: int = 0,
    can_bet: bool | None = None,
    second_pass_ran: bool | None = None,
    second_pass_completed: bool | None = None,
    no_pmodel_reject_share: float | None = None,
    emit_coverage_signal: bool = True,
    auto_revoke: bool = True,
) -> dict[str, Any]:
    """
    Full recommend-path: compute health, write file, hygiene revoke, optional emit.
    """
    health = compute_coverage_health(
        cfg,
        candidates,
        shortlist=shortlist,
        source="recommend",
        n_picked=n_picked,
        can_bet=can_bet,
        second_pass_ran=second_pass_ran,
        second_pass_completed=second_pass_completed,
        no_pmodel_reject_share=no_pmodel_reject_share,
    )
    path = write_coverage_health(cfg, health)
    health["path"] = str(path)

    revoke_result: dict[str, Any] | None = None
    if auto_revoke:
        try:
            from nt.control_signals import maybe_auto_revoke_coverage

            revoke_result = maybe_auto_revoke_coverage(
                cfg, coverage_health=health, actor="engine"
            )
            # Recompute overlay flags after revoke
            if revoke_result.get("revoked"):
                health = compute_coverage_health(
                    cfg,
                    candidates,
                    shortlist=shortlist,
                    source="recommend",
                    n_picked=n_picked,
                    can_bet=can_bet,
                    second_pass_ran=second_pass_ran,
                    second_pass_completed=second_pass_completed,
                    no_pmodel_reject_share=no_pmodel_reject_share,
                )
                path = write_coverage_health(cfg, health)
                health["path"] = str(path)
                health["coverage_auto_revoked"] = True
        except Exception as ex:
            revoke_result = {"ok": False, "error": str(ex)}

    emit_result: dict[str, Any] | None = None
    if emit_coverage_signal:
        try:
            emit_result = maybe_emit_force_coverage_from_health(
                cfg,
                health,
                n_picked=n_picked,
                no_pmodel_reject_share=no_pmodel_reject_share,
            )
            if emit_result.get("emitted"):
                # Refresh force_coverage flags
                health = compute_coverage_health(
                    cfg,
                    candidates,
                    shortlist=shortlist,
                    source="recommend",
                    n_picked=n_picked,
                    can_bet=can_bet,
                    second_pass_ran=second_pass_ran,
                    second_pass_completed=second_pass_completed,
                    no_pmodel_reject_share=no_pmodel_reject_share,
                )
                path = write_coverage_health(cfg, health)
                health["path"] = str(path)
        except Exception as ex:
            emit_result = {"ok": False, "error": str(ex)}

    health["auto_revoke_result"] = revoke_result
    health["force_coverage_emit_result"] = emit_result
    return health
