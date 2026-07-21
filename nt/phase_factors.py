"""
Phase v5 multi-factor health scores (advisory + hard floors).

Does not replace the 1A–5 ladder; supplies process_error_rate, calibration,
concentration, and learning health for phase/risk overlays.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nt.bets_io import fnum, is_open_risk
from nt.config import path_from_config


def phase_health_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = dict(cfg.get("phase_health") or {})
    action = str(raw.get("process_error_action") or "REDUCED").upper()
    if action not in ("REDUCED", "RESEARCH_ONLY"):
        action = "REDUCED"
    return {
        "enabled": bool(raw.get("enabled", True)),
        "process_error_window_days": int(raw.get("process_error_window_days") or 14),
        "process_error_rate_threshold": float(
            raw.get("process_error_rate_threshold") or 0.25
        ),
        "process_error_min_reviews": int(raw.get("process_error_min_reviews") or 4),
        "process_error_action": action,
        "process_error_hold_days": int(raw.get("process_error_hold_days") or 7),
        "concentration_block_share": float(raw.get("concentration_block_share") or 0.55),
        "calibration_poor_brier": float(raw.get("calibration_poor_brier") or 0.28),
        "calibration_min_n": int(raw.get("calibration_min_n") or 15),
    }


def _parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        raw = s.replace("Z", "+00:00") if str(s).endswith("Z") else str(s)
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _reviews_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("settlement_reviews_jsonl"):
        return path_from_config(cfg, "settlement_reviews_jsonl")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "settlement_reviews.jsonl"


def load_reviews_window(
    cfg: dict[str, Any],
    *,
    days: int = 14,
) -> list[dict[str, Any]]:
    path = _reviews_path(cfg)
    if not path.is_file():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            ts = _parse_ts(str(rec.get("ts") or ""))
            if ts is None or ts >= cutoff:
                out.append(rec)
    except Exception:
        return []
    return out


def process_error_rate_14d(
    cfg: dict[str, Any],
    *,
    days: int | None = None,
) -> dict[str, Any]:
    h = phase_health_cfg(cfg)
    days = int(days if days is not None else h["process_error_window_days"])
    reviews = load_reviews_window(cfg, days=days)
    n = len(reviews)
    n_pe = sum(
        1
        for r in reviews
        if str(r.get("variance_class") or "") == "process_error"
    )
    min_n = int(h["process_error_min_reviews"])
    if n < min_n:
        rate = 0.0
        force = False
    else:
        rate = n_pe / n if n else 0.0
        force = rate > float(h["process_error_rate_threshold"])
    return {
        "n_reviews_14d": n,
        "n_process_error_14d": n_pe,
        "process_error_rate_14d": round(rate, 4),
        "force_process_health": force,
    }


def open_risk_concentration(rows: list[dict[str, str]]) -> dict[str, Any]:
    by_sport: dict[str, float] = defaultdict(float)
    total = 0.0
    for r in rows:
        if not is_open_risk(r.get("result")):
            continue
        st = fnum(r.get("stake_nok")) or 0.0
        if st <= 0:
            continue
        sp = (r.get("sport") or "(unknown)").strip().lower() or "(unknown)"
        by_sport[sp] += st
        total += st
    if total <= 0:
        return {
            "open_risk_concentration": 0.0,
            "top_open_sport": None,
            "top_open_share": 0.0,
            "open_stake_total": 0.0,
        }
    top_sp, top_st = max(by_sport.items(), key=lambda kv: kv[1])
    share = top_st / total
    return {
        "open_risk_concentration": round(share, 4),
        "top_open_sport": top_sp,
        "top_open_share": round(share, 4),
        "open_stake_total": round(total, 2),
    }


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def compute_phase_factors(
    cfg: dict[str, Any],
    *,
    equity: float,
    peak: float,
    rows: list[dict[str, str]],
    baseline: float = 500.0,
) -> dict[str, Any]:
    """
    Multi-factor PhaseState scores. Higher score = healthier (except raw rates).
    """
    h = phase_health_cfg(cfg)
    pe = process_error_rate_14d(cfg)
    conc = open_risk_concentration(rows)

    # Equity progress toward phase 5 enter (default 5000)
    phases = cfg.get("phases") or {}
    target = 5000.0
    if "5" in phases:
        target = float(phases["5"].get("enter_equity") or 5000)
    base = float(baseline or 500)
    if target > base:
        equity_score = _clamp01((float(equity) - base) / (target - base))
    else:
        equity_score = 0.5

    dd = 0.0
    if peak and peak > 0:
        dd = max(0.0, (float(peak) - float(equity)) / float(peak))
    dd_score = _clamp01(1.0 - dd)

    # Calibration
    cal_n, brier = 0, None
    try:
        from nt.calibrate import load_calibration_quality

        cq = load_calibration_quality(cfg)
        cal_n = int(cq.get("n") or 0)
        if cq.get("brier") is not None:
            brier = float(cq["brier"])
    except Exception:
        pass

    min_cal = int(h["calibration_min_n"])
    if cal_n >= min_cal and brier is not None:
        # 0.15 excellent → 1.0; 0.35 poor → 0.0
        calibration_score = _clamp01(1.0 - (float(brier) - 0.15) / 0.20)
        cal_poor = float(brier) > float(h["calibration_poor_brier"])
    else:
        calibration_score = 0.5  # neutral thin sample
        cal_poor = False

    # Learning health
    learning_health = 1.0
    n_blocked = 0
    n_sports = 0
    try:
        from nt.learning import load_learning

        learn = load_learning(cfg) or {}
        sports = learn.get("sports") or {}
        n_sports = len(sports)
        n_blocked = sum(1 for s in sports.values() if isinstance(s, dict) and s.get("blocked"))
        if n_sports > 0:
            learning_health = _clamp01(1.0 - (n_blocked / n_sports))
            thin = sum(
                1
                for s in sports.values()
                if isinstance(s, dict) and str(s.get("status") or "") == "thin"
            )
            if thin / n_sports > 0.7:
                learning_health = min(learning_health, 0.65)
    except Exception:
        pass

    rate = float(pe["process_error_rate_14d"])
    # Healthier when process errors low
    process_health_score = _clamp01(1.0 - rate * 2.0) if pe["n_reviews_14d"] >= h["process_error_min_reviews"] else 0.5

    share = float(conc["open_risk_concentration"] or 0)
    high_odds_stress = False
    if h["enabled"]:
        if share + 1e-12 >= float(h["concentration_block_share"]):
            high_odds_stress = True
        if cal_poor:
            high_odds_stress = True

    return {
        "equity_score": round(equity_score, 4),
        "dd_score": round(dd_score, 4),
        "process_error_rate_14d": pe["process_error_rate_14d"],
        "calibration_score": round(calibration_score, 4),
        "open_risk_concentration": conc["open_risk_concentration"],
        "learning_health": round(learning_health, 4),
        "process_health_score": round(process_health_score, 4),
        "high_odds_stress_block": high_odds_stress,
        "force_process_health": bool(pe["force_process_health"]) and h["enabled"],
        "raw": {
            "n_reviews_14d": pe["n_reviews_14d"],
            "n_process_error_14d": pe["n_process_error_14d"],
            "brier": brier,
            "cal_n": cal_n,
            "top_open_sport": conc.get("top_open_sport"),
            "top_open_share": conc.get("top_open_share"),
            "open_stake_total": conc.get("open_stake_total"),
            "n_blocked_sports": n_blocked,
            "n_sports": n_sports,
            "dd_from_peak": round(dd, 4),
            "cal_poor": cal_poor,
        },
    }
