"""
P0: ControlSignals — primary closed-loop actuators after process misses.

Store: data/state/control_signals.jsonl (append-only; active = non-expired).

Signals:
  temp_gate_raise  → min_ev raise + force confirmed lineup (TTL 7–14 days)
  temp_ev_relax    → per-line min_ev soften + stake haircut (TTL hours; safety net)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from nt.bets_io import utc_now
from nt.config import path_from_config

# Active signal kinds that load_active_signals returns by default
_ACTIVE_KINDS = frozenset({"temp_gate_raise", "temp_ev_relax"})


def control_signals_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    learn = cfg.get("learning") or {}
    raw = dict(learn.get("control_signals") or {})
    # Back-compat: also read process_gate knobs for min_ev/max
    pg = dict(learn.get("process_gate") or {})
    ttl = float(raw.get("ttl_days") or 10)
    ttl = max(7.0, min(14.0, ttl))
    return {
        "enabled": bool(raw.get("enabled", True)),
        "min_ev_raise": float(
            raw.get("min_ev_raise") or pg.get("min_ev_raise") or 0.02
        ),
        "max_raise": float(raw.get("max_raise") or pg.get("max_raise") or 0.05),
        "ttl_days": ttl,
        "force_confirmed_lineup": bool(raw.get("force_confirmed_lineup", True)),
        "temp_ev_relax": temp_ev_relax_cfg(cfg),
        "coverage_priority": dict(raw.get("coverage_priority") or {}),
    }


def temp_ev_relax_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    """Mechanism B knobs (defaults safe for missing config)."""
    learn = cfg.get("learning") or {}
    cs = dict(learn.get("control_signals") or {})
    raw = dict(cs.get("temp_ev_relax") or {})
    # Optional mirror under research.coverage_floor.ev_relax
    try:
        from nt.defaults import research_cfg

        rcfg = research_cfg(cfg)
        floor = dict(rcfg.get("coverage_floor") or {})
        mirror = dict(floor.get("ev_relax") or {})
    except Exception:
        mirror = {}
    merged = {**mirror, **raw}
    return {
        "enabled": bool(merged.get("enabled", True)),
        "delta_min": float(merged.get("delta_min", 0.01)),
        "delta_max": float(merged.get("delta_max", 0.02)),
        "ttl_hours": float(merged.get("ttl_hours", 24)),
        "clear_on_settle": bool(merged.get("clear_on_settle", True)),
        "stake_mult": float(merged.get("stake_mult", 0.80)),
        "top_n_survivors": int(merged.get("top_n_survivors", 3)),
        "min_board_matches": int(merged.get("min_board_matches", 15)),
        "require_coverage_warn": bool(merged.get("require_coverage_warn", True)),
        "exclude_high_odds": bool(merged.get("exclude_high_odds", True)),
        "exclude_grade_c": bool(merged.get("exclude_grade_c", True)),
    }


def control_signals_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("control_signals_jsonl"):
        return path_from_config(cfg, "control_signals_jsonl")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "control_signals.jsonl"


def _parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        raw = s.replace("Z", "+00:00") if s.endswith("Z") else s
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def load_all_signals(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    path = control_signals_path(cfg)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    except Exception:
        return []
    return out


def _normalize_line_key(item: Any) -> str:
    """Normalize allowlist entry to 'match|selection'."""
    if item is None:
        return ""
    if isinstance(item, str):
        s = item.strip()
        if not s:
            return ""
        if "|" in s:
            parts = s.split("|", 1)
            return f"{parts[0].strip()}|{parts[1].strip()}"
        return s
    if isinstance(item, dict):
        m = str(item.get("match") or "").strip()
        sel = str(item.get("selection") or "").strip()
        if m or sel:
            return f"{m}|{sel}"
        return ""
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return f"{str(item[0]).strip()}|{str(item[1]).strip()}"
    return str(item).strip()


def normalize_line_keys(items: Iterable[Any] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for it in items or []:
        k = _normalize_line_key(it)
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def line_key_match(match: str, selection: str) -> str:
    return f"{(match or '').strip()}|{(selection or '').strip()}"


def _signal_revoked(
    rec: dict[str, Any],
    revokes: list[dict[str, Any]],
    sig_ts: datetime,
) -> bool:
    """Apply tombstones (sport/market and/or kind-scoped)."""
    kind = str(rec.get("kind") or "")
    sp = str(rec.get("sport") or "").strip().lower()
    mk = str(rec.get("market") or "").strip().lower()
    for r in revokes:
        r_ts = r.get("_ts") or _now()
        if r_ts < sig_ts:
            continue  # revoke only kills signals already present
        r_kinds = r.get("revoke_kinds")
        r_sig_kind = str(r.get("signal_kind") or "").strip()
        if r.get("revoke_all") and not r_kinds and not r_sig_kind:
            return True
        # Kind-scoped revoke (temp_ev_relax clear, etc.)
        if r_kinds:
            kinds_l = {str(x).strip() for x in r_kinds if x is not None}
            if "*" in kinds_l or kind in kinds_l:
                return True
            continue
        if r_sig_kind:
            if r_sig_kind == kind or r_sig_kind == "*":
                # optional sport filter still applies when present
                r_sp = str(r.get("sport") or "").strip().lower()
                if r_sp and r_sp not in ("*", "") and r_sp != sp:
                    continue
                return True
            continue
        # Legacy sport/market revoke — primarily temp_gate_raise
        if kind == "temp_ev_relax":
            # Sport-only revokes do not clear temp_ev_relax (use revoke_kinds)
            continue
        r_sp = str(r.get("sport") or "").strip().lower() or "*"
        r_mk = str(r.get("market") or "").strip().lower() or "*"
        if r.get("revoke_all"):
            return True
        if r_sp == "*" or r_sp == sp:
            if r_mk in ("*", "") or r_mk == mk or not mk:
                return True
    return False


def load_active_by_kind(cfg: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    """Non-expired, non-revoked signals of a single kind."""
    return load_active_signals(cfg, kinds={str(kind)})


def load_active_signals(
    cfg: dict[str, Any],
    kinds: set[str] | frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Non-expired, non-revoked active ControlSignals.

    kinds=None → temp_gate_raise + temp_ev_relax (and future active kinds).
    Pass kinds={'temp_gate_raise'} to preserve gate-only callers.
    """
    now = _now()
    want = set(kinds) if kinds is not None else set(_ACTIVE_KINDS)
    all_recs = load_all_signals(cfg)

    revokes: list[dict[str, Any]] = []
    for rec in all_recs:
        if str(rec.get("kind") or "") != "revoke":
            continue
        ts = _parse_ts(str(rec.get("ts") or "")) or now
        r = dict(rec)
        r["_ts"] = ts
        revokes.append(r)

    active: list[dict[str, Any]] = []
    for rec in all_recs:
        if rec.get("revoked"):
            continue
        kind = str(rec.get("kind") or "")
        if kind not in want:
            continue
        exp = _parse_ts(str(rec.get("expires_at") or ""))
        if exp and exp < now:
            continue
        sig_ts = _parse_ts(str(rec.get("ts") or "")) or now
        if _signal_revoked(rec, revokes, sig_ts):
            continue
        active.append(rec)
    return active


def revoke_signals(
    cfg: dict[str, Any],
    *,
    sport: str = "",
    market: str = "",
    revoke_all: bool = False,
    actor: str = "cli",
    reason: str = "manual_expire",
    revoke_kinds: list[str] | None = None,
    signal_kind: str = "",
) -> dict[str, Any]:
    """Append revoke tombstone so matching active signals stop applying."""
    rec: dict[str, Any] = {
        "kind": "revoke",
        "ts": utc_now(),
        "sport": (sport or "").strip().lower() or None,
        "market": (market or "").strip().lower() or None,
        "revoke_all": bool(revoke_all),
        "actor": actor,
        "reason": reason,
        "schema_version": 1,
    }
    if revoke_kinds:
        rec["revoke_kinds"] = list(revoke_kinds)
    if signal_kind:
        rec["signal_kind"] = str(signal_kind).strip()
    if (
        not revoke_all
        and not rec["sport"]
        and not revoke_kinds
        and not signal_kind
    ):
        return {"ok": False, "error": "sport required unless --all / revoke_kinds"}
    path = _append_signal(cfg, rec)
    still = load_active_signals(cfg)
    return {"ok": True, "revoke": rec, "path": str(path), "n_active_remaining": len(still)}


def _append_signal(cfg: dict[str, Any], rec: dict[str, Any]) -> Path:
    path = control_signals_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def emit_temp_gate_raise(
    cfg: dict[str, Any],
    *,
    sport: str,
    market: str = "",
    bet_id: str = "",
    source: str = "process_error",
    process_root_cause: str = "",
    packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Emit temp_gate_raise for sport (and market if known).
    Always allowed on n=1 — primary closed-loop after process miss.
    """
    cs = control_signals_cfg(cfg)
    if not cs["enabled"]:
        return {"ok": False, "reason": "disabled"}

    sp = (sport or "").strip().lower() or "unknown"
    mk = (market or "").strip().lower()
    if mk in ("", "unknown"):
        mk = ""

    ttl_days = float(cs["ttl_days"])
    expires = (_now() + timedelta(days=ttl_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise_amt = float(cs["min_ev_raise"])
    max_raise = float(cs["max_raise"])

    # Stack: sum prior active raises for same sport, then add, cap
    active = load_active_by_kind(cfg, "temp_gate_raise")
    prior = 0.0
    for a in active:
        if str(a.get("sport") or "").lower() == sp:
            prior = max(prior, float(a.get("min_ev_raise") or 0))
        if mk and str(a.get("market") or "").lower() == mk:
            prior = max(prior, float(a.get("min_ev_raise") or 0))
    stacked = min(max_raise, prior + raise_amt if prior > 0 else raise_amt)

    root = process_root_cause or (
        str((packet or {}).get("process_root_cause") or "") if packet else ""
    )

    rec = {
        "kind": "temp_gate_raise",
        "ts": utc_now(),
        "expires_at": expires,
        "ttl_days": ttl_days,
        "sport": sp,
        "market": mk or None,
        "min_ev_raise": round(stacked, 4),
        "force_confirmed_lineup": bool(cs["force_confirmed_lineup"]),
        "source": source,
        "bet_id": bet_id or None,
        "process_root_cause": root or None,
        "schema_version": 1,
    }
    path = _append_signal(cfg, rec)
    return {"ok": True, "signal": rec, "path": str(path)}


def active_temp_gate_overlay(
    cfg: dict[str, Any],
    *,
    sport: str = "",
    market: str = "",
) -> dict[str, Any]:
    """
    Aggregate overlay for a candidate sport/market.
    Returns min_ev_raise (capped) and force_confirmed_lineup.
    """
    cs = control_signals_cfg(cfg)
    if not cs["enabled"]:
        return {
            "min_ev_raise": 0.0,
            "force_confirmed_lineup": False,
            "n_signals": 0,
            "sources": [],
        }

    sp = (sport or "").strip().lower()
    mk = (market or "").strip().lower()
    raise_amt = 0.0
    force = False
    sources: list[str] = []
    n = 0
    for a in load_active_by_kind(cfg, "temp_gate_raise"):
        a_sp = str(a.get("sport") or "").lower()
        a_mk = str(a.get("market") or "").lower()
        hit = False
        if sp and a_sp == sp:
            hit = True
        if mk and a_mk and a_mk == mk:
            hit = True
        if not hit:
            continue
        n += 1
        raise_amt = max(raise_amt, float(a.get("min_ev_raise") or 0))
        if a.get("force_confirmed_lineup"):
            force = True
        sources.append(str(a.get("source") or "temp_gate_raise"))

    max_raise = float(cs["max_raise"])
    return {
        "min_ev_raise": min(max_raise, raise_amt),
        "force_confirmed_lineup": force,
        "n_signals": n,
        "sources": sources[:8],
    }


# ---------------------------------------------------------------------------
# Mechanism B: temp_ev_relax (per-line min_ev soften + stake haircut)
# ---------------------------------------------------------------------------


def emit_temp_ev_relax(
    cfg: dict[str, Any],
    *,
    delta_ev: float,
    line_keys: list[Any],
    source: str = "empty_deep_queue",
    coverage_level: str = "",
    board_matches: int = 0,
    actor: str = "engine",
    force: bool = False,
) -> dict[str, Any]:
    """
    Append temp_ev_relax JSONL record.

    delta_ev clamped to [delta_min, delta_max].
    Skips emit when an active signal already covers the same line_keys (unless force).
    """
    cs = control_signals_cfg(cfg)
    ter = temp_ev_relax_cfg(cfg)
    if not cs.get("enabled", True) or not ter.get("enabled", True):
        return {"ok": False, "reason": "disabled"}

    keys = normalize_line_keys(line_keys)
    if not keys:
        return {"ok": False, "reason": "no_line_keys"}

    d_min = float(ter["delta_min"])
    d_max = float(ter["delta_max"])
    if d_max < d_min:
        d_min, d_max = d_max, d_min
    delta = max(d_min, min(d_max, float(delta_ev)))

    if not force:
        ov = active_temp_ev_relax_overlay(cfg)
        if ov.get("active"):
            existing = set(normalize_line_keys(ov.get("line_keys") or []))
            if existing and existing == set(keys):
                return {
                    "ok": False,
                    "reason": "already_active_same_keys",
                    "active": ov,
                }
            # Also skip spam when any active relax still covers all requested keys
            if existing and set(keys).issubset(existing):
                return {
                    "ok": False,
                    "reason": "already_active_covers_keys",
                    "active": ov,
                }

    ttl_h = float(ter["ttl_hours"])
    expires = (_now() + timedelta(hours=ttl_h)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stake_mult = float(ter["stake_mult"])

    rec = {
        "kind": "temp_ev_relax",
        "ts": utc_now(),
        "expires_at": expires,
        "ttl_hours": ttl_h,
        "delta_ev": round(delta, 4),
        "stake_mult": round(stake_mult, 4),
        "line_keys": keys,
        "clear_on_settle": bool(ter.get("clear_on_settle", True)),
        "source": source,
        "actor": actor,
        "coverage_level": (coverage_level or "").strip().lower() or None,
        "board_matches": int(board_matches) if board_matches else None,
        "schema_version": 1,
    }
    path = _append_signal(cfg, rec)
    return {"ok": True, "signal": rec, "path": str(path)}


def active_temp_ev_relax_overlay(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Aggregate active temp_ev_relax overlay for portfolio.

    Returns:
      active, delta_ev, stake_mult, line_keys (list), line_key_set, expires_at, sources
    """
    ter = temp_ev_relax_cfg(cfg)
    empty = {
        "active": False,
        "delta_ev": 0.0,
        "stake_mult": 1.0,
        "line_keys": [],
        "line_key_set": set(),
        "expires_at": None,
        "sources": [],
        "n_signals": 0,
        "exclude_high_odds": bool(ter.get("exclude_high_odds", True)),
        "exclude_grade_c": bool(ter.get("exclude_grade_c", True)),
    }
    cs = control_signals_cfg(cfg)
    if not cs.get("enabled", True) or not ter.get("enabled", True):
        return empty

    active = load_active_by_kind(cfg, "temp_ev_relax")
    if not active:
        return empty

    keys: list[str] = []
    key_set: set[str] = set()
    delta = 0.0
    stake_mult = 1.0
    sources: list[str] = []
    expires_at: str | None = None
    for a in active:
        for k in normalize_line_keys(a.get("line_keys") or []):
            if k not in key_set:
                key_set.add(k)
                keys.append(k)
        delta = max(delta, float(a.get("delta_ev") or 0.0))
        sm = a.get("stake_mult")
        if sm is not None:
            # Tightest (lowest) stake mult wins when multiple
            stake_mult = min(stake_mult, float(sm)) if stake_mult < 1.0 else float(sm)
        sources.append(str(a.get("source") or "temp_ev_relax"))
        exp = str(a.get("expires_at") or "") or None
        if exp and (expires_at is None or exp < expires_at):
            expires_at = exp

    if stake_mult >= 1.0 and active:
        # default from latest / config if signals omitted stake_mult
        stake_mult = float(ter.get("stake_mult") or 0.80)

    # Clamp delta to config band (fail-closed vs runaway records)
    d_min = float(ter["delta_min"])
    d_max = float(ter["delta_max"])
    if d_max < d_min:
        d_min, d_max = d_max, d_min
    if delta > 0:
        delta = max(d_min, min(d_max, delta))

    return {
        "active": bool(keys) and delta > 0,
        "delta_ev": round(delta, 4),
        "stake_mult": round(float(stake_mult), 4),
        "line_keys": keys,
        "line_key_set": key_set,
        "expires_at": expires_at,
        "sources": sources[:8],
        "n_signals": len(active),
        "exclude_high_odds": bool(ter.get("exclude_high_odds", True)),
        "exclude_grade_c": bool(ter.get("exclude_grade_c", True)),
    }


def clear_temp_ev_relax_on_settle(
    cfg: dict[str, Any],
    *,
    actor: str = "settle",
    reason: str = "clear_on_settle",
) -> dict[str, Any]:
    """
    Revoke active temp_ev_relax signals when clear_on_settle is enabled.

    Soft-fail friendly: returns ok=False only on write issues; no-op if none active.
    """
    ter = temp_ev_relax_cfg(cfg)
    if not ter.get("clear_on_settle", True):
        return {"ok": True, "cleared": 0, "skipped": "clear_on_settle_false"}
    active = load_active_by_kind(cfg, "temp_ev_relax")
    if not active:
        return {"ok": True, "cleared": 0}
    # Only clear signals that opted into clear_on_settle (default true)
    n_clearable = sum(1 for a in active if a.get("clear_on_settle", True))
    if n_clearable == 0:
        return {"ok": True, "cleared": 0, "skipped": "signals_not_clearable"}
    try:
        out = revoke_signals(
            cfg,
            revoke_kinds=["temp_ev_relax"],
            actor=actor,
            reason=reason,
        )
        out["cleared"] = n_clearable
        return out
    except Exception as ex:  # noqa: BLE001
        return {"ok": False, "cleared": 0, "error": str(ex)}


def load_coverage_health_level(cfg: dict[str, Any]) -> str:
    """Read data/state/coverage_health.json level if present (ok|warn|critical)."""
    paths = cfg.get("paths") or {}
    try:
        if paths.get("coverage_health_json"):
            path = path_from_config(cfg, "coverage_health_json")
        elif paths.get("state_dir"):
            path = path_from_config(cfg, "state_dir") / "coverage_health.json"
        else:
            path = Path("data/state/coverage_health.json")
        if not path.is_file():
            return "ok"
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            lvl = str(data.get("level") or "ok").strip().lower()
            if lvl in ("ok", "warn", "critical"):
                return lvl
    except Exception:
        pass
    return "ok"


def maybe_emit_temp_ev_relax(
    cfg: dict[str, Any],
    *,
    board_matches: int,
    coverage_level: str,
    deep_queue_n: int,
    survivors: list[dict[str, Any]],
    source: str = "empty_deep_queue",
) -> dict[str, Any]:
    """
    Emit temp_ev_relax when safety-net conditions hold.

    Conditions:
      - enabled
      - unique board matches >= min_board_matches
      - coverage_level in {warn, critical} when require_coverage_warn
      - deep_queue_n == 0
      - ≥1 light-pass survivor (non-high-odds when exclude_high_odds)
    Selects top_n by promotion_score (or score field).
    """
    ter = temp_ev_relax_cfg(cfg)
    if not control_signals_cfg(cfg).get("enabled", True) or not ter.get("enabled", True):
        return {"ok": False, "reason": "disabled"}

    min_m = int(ter["min_board_matches"])
    if int(board_matches) < min_m:
        return {
            "ok": False,
            "reason": "board_matches_below_min",
            "board_matches": board_matches,
            "min_board_matches": min_m,
        }

    lvl = (coverage_level or "ok").strip().lower()
    if ter.get("require_coverage_warn", True) and lvl not in ("warn", "critical"):
        return {
            "ok": False,
            "reason": "coverage_not_warn_or_critical",
            "coverage_level": lvl,
        }

    if int(deep_queue_n) > 0:
        return {"ok": False, "reason": "deep_queue_not_empty", "deep_queue_n": deep_queue_n}

    thr = 2.5
    try:
        thr = float((cfg.get("selection") or {}).get("high_odds_threshold") or 2.5)
    except (TypeError, ValueError):
        thr = 2.5

    ranked: list[tuple[float, dict[str, Any]]] = []
    for s in survivors or []:
        if not isinstance(s, dict):
            continue
        odds = float(s.get("decimal_odds") or s.get("odds") or 0)
        if ter.get("exclude_high_odds", True) and odds >= thr:
            continue
        match = str(s.get("match") or "").strip()
        sel = str(s.get("selection") or "").strip()
        if not match or not sel:
            continue
        score = float(
            s.get("promotion_score")
            if s.get("promotion_score") is not None
            else (s.get("score") or s.get("promo_score") or 0)
        )
        ranked.append((score, s))

    if not ranked:
        return {"ok": False, "reason": "no_survivors"}

    ranked.sort(key=lambda x: (-x[0], float(x[1].get("decimal_odds") or x[1].get("odds") or 99)))
    top_n = max(1, int(ter["top_n_survivors"]))
    chosen = [s for _sc, s in ranked[:top_n]]
    keys = [
        line_key_match(str(s.get("match") or ""), str(s.get("selection") or ""))
        for s in chosen
    ]
    # Use max delta (strongest soften within band) for empty-queue safety net
    delta = float(ter["delta_max"])
    return emit_temp_ev_relax(
        cfg,
        delta_ev=delta,
        line_keys=keys,
        source=source,
        coverage_level=lvl,
        board_matches=int(board_matches),
        actor="engine",
    )


def maybe_emit_temp_ev_relax_from_light(
    cfg: dict[str, Any],
    *,
    records: list[Any],
    deep_queue: list[Any],
    board_matches: int | None = None,
    coverage_level: str | None = None,
    shortlist_n: int | None = None,
) -> dict[str, Any]:
    """
    Trigger helper used after build_deep_queue in run_light_research.

    Collects light-pass survivors without p_model (actionable research survivors).
    """
    matches: set[str] = set()
    survivors: list[dict[str, Any]] = []
    for r in records or []:
        if hasattr(r, "match"):
            match = str(getattr(r, "match", "") or "")
            sel = str(getattr(r, "selection", "") or "")
            sport = str(getattr(r, "sport", "") or "")
            odds = float(getattr(r, "decimal_odds", 0) or 0)
            verdict = str(getattr(r, "verdict", "") or "")
            has_p = bool(getattr(r, "has_p_model", False))
            script_c = bool(getattr(r, "script_conflict", False))
            base_c = bool(getattr(r, "base_rate_conflict", False))
            note = str(getattr(r, "rough_ev_note", "") or "")
            promo = None
            if "promo_score=" in note:
                try:
                    promo = float(note.split("promo_score=")[-1].split()[0].split("|")[0])
                except (TypeError, ValueError, IndexError):
                    promo = None
        else:
            d = dict(r) if isinstance(r, dict) else {}
            match = str(d.get("match") or "")
            sel = str(d.get("selection") or "")
            sport = str(d.get("sport") or "")
            odds = float(d.get("decimal_odds") or d.get("odds") or 0)
            verdict = str(d.get("verdict") or "")
            has_p = bool(d.get("has_p_model") or d.get("has_p"))
            script_c = bool(d.get("script_conflict"))
            base_c = bool(d.get("base_rate_conflict"))
            promo = d.get("promotion_score")
            note = str(d.get("rough_ev_note") or "")

        if match:
            matches.add(match)
        if verdict != "pass" or has_p or script_c or base_c:
            continue
        survivors.append(
            {
                "match": match,
                "selection": sel,
                "sport": sport,
                "decimal_odds": odds,
                "promotion_score": promo if promo is not None else 0.0,
            }
        )

    # Prefer unique shortlist match count when provided; else unique matches on records
    n_matches = (
        int(board_matches)
        if board_matches is not None
        else (int(shortlist_n) if shortlist_n is not None else len(matches))
    )
    # For min_board_matches the spec says "unique matches on board"
    if board_matches is None and shortlist_n is None:
        n_matches = len(matches)

    lvl = (
        (coverage_level or "").strip().lower()
        if coverage_level is not None
        else load_coverage_health_level(cfg)
    )
    return maybe_emit_temp_ev_relax(
        cfg,
        board_matches=n_matches,
        coverage_level=lvl,
        deep_queue_n=len(deep_queue or []),
        survivors=survivors,
        source="empty_deep_queue",
    )


def active_coverage_priority_overlay(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    force_coverage_priority overlay (read-only helper for deep-queue weights).

    Returns inactive defaults when no coverage signal is stored / module unused.
    Kept here so light_research import does not fail.
    """
    cs = control_signals_cfg(cfg)
    cov = dict(cs.get("coverage_priority") or {})
    if not cs.get("enabled", True) or not bool(cov.get("enabled", True)):
        return {"active": False}

    # Optional future: load kind == force_coverage_priority from JSONL
    active = [
        a
        for a in load_all_signals(cfg)
        if str(a.get("kind") or "") == "force_coverage_priority"
        and not a.get("revoked")
    ]
    now = _now()
    live: list[dict[str, Any]] = []
    for a in active:
        exp = _parse_ts(str(a.get("expires_at") or ""))
        if exp and exp < now:
            continue
        live.append(a)
    if not live:
        return {"active": False}

    latest = live[-1]
    return {
        "active": True,
        "target_odds_band": latest.get("target_odds_band")
        or cov.get("target_odds_band")
        or "1.85-2.60",
        "prefer": latest.get("prefer") or cov.get("prefer") or [],
        "min_deep_packs": latest.get("min_deep_packs") or cov.get("min_deep_packs"),
        "coverage_preferred_share": latest.get("coverage_preferred_share")
        or cov.get("coverage_preferred_share"),
        "weight_boost": latest.get("weight_boost")
        if latest.get("weight_boost") is not None
        else cov.get("weight_boost", 30.0),
        "sources": [str(a.get("source") or "force_coverage_priority") for a in live[:4]],
    }
