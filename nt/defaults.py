from __future__ import annotations

"""
Backward-compatible defaults for optional v5 config sections.

Old config.yaml files without combos/agent/research/projection keep working:
callers should use these helpers instead of requiring new keys.
"""

from typing import Any


def combos_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = dict(cfg.get("combos") or {})
    defaults = {
        "enabled": False,
        "aggressiveness": "conservative",  # off | conservative | standard | aggressive
        "stake_multiplier": 0.55,
        "min_correlation_score": 0.55,
        "allow_high_odds_legs": False,
        "min_leg_grade": "B",
        "min_leg_ev": 0.03,
        "max_legs": int((cfg.get("norsk_tipping") or {}).get("max_legs_in_combo", 3)),
        "require_per_leg_evidence": True,
        "trebles_min_phase": "4",
    }
    # aggressiveness presets (only fill missing keys)
    preset = str(raw.get("aggressiveness") or defaults["aggressiveness"]).lower()
    if preset == "off":
        defaults.update({"enabled": False, "stake_multiplier": 0.0})
    elif preset == "standard":
        defaults.update({"enabled": True, "stake_multiplier": 0.65, "min_correlation_score": 0.50})
    elif preset == "aggressive":
        defaults.update(
            {
                "enabled": True,
                "stake_multiplier": 0.75,
                "min_correlation_score": 0.40,
                "allow_high_odds_legs": True,
            }
        )
    else:  # conservative
        defaults.update({"enabled": raw.get("enabled", False), "stake_multiplier": 0.55})

    out = {**defaults, **raw}
    # explicit enabled:false always wins
    if raw.get("enabled") is False or preset == "off":
        out["enabled"] = False
    return out


def agent_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = dict(cfg.get("agent") or {})
    defaults = {
        "enabled": False,
        "provider": "auto",
        "model": "",
        "max_tool_rounds": 6,
        "audit_log": "data/state/agent_audit.jsonl",
        "allow_cli_dry_run": True,
        "allow_write_evidence_scaffold": True,
        "temperature": 0.2,
        "base_url_xai": "https://api.x.ai/v1",
        "base_url_openai": "https://api.openai.com/v1",
    }
    return {**defaults, **raw}


def projection_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = dict(cfg.get("projection") or {})
    defaults = {
        "default_years": 2,
        "default_sims": 1000,
        "default_roi": 0.02,
        "default_bets_per_week": 10,
        "default_avg_odds": 1.85,
        "seed": 42,
    }
    return {**defaults, **raw}


def capital_v2_defaults(cfg: dict[str, Any]) -> dict[str, Any]:
    """Phase 2 capital rule bundle defaults (live risk off until enabled)."""
    from nt.capital_v2 import capital_v2_cfg

    return capital_v2_cfg(cfg)


def research_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = dict(cfg.get("research") or {})
    defaults = {
        "templates_dir": "evidence/templates",
        "default_sport": "football",
        "min_summary_chars": 20,
        "min_failure_modes_chars": 10,
        # Board workflow guards
        "require_research_for_recommend": True,
        "board_max_per_match": 6,
        "board_max_total": 24,
        "board_max_football_share": 0.45,
        "board_min_non_football": 4,
        "board_max_props": 5,
        # Market coverage
        "high_volume_market_threshold": 40,
        "market_scan_top_n": 5,
        # Tiered research (Light → Deep)
        "tiers": {
            "light_coverage_target": 0.85,
            "light_coverage_min_n": 8,
            "min_light_per_sport_when_n": 5,
            "min_light_per_sport": 3,
            "deep_target_n": 8,
            "deep_max_n": 15,
            "deep_target_dynamic": True,
            "deep_target_min": 8,
            "deep_target_max": 15,
            "deep_target_divisor": 8,
            "auto_light_on_board": True,
            "auto_promote_to_deep": False,
            "engine_deep_queue": True,
            "deep_min_preferred_share": 0.55,
            "deep_max_short_main_share": 0.25,
            "short_chalk_odds": 1.70,
            "preferred_odds_lo": 1.85,
            "preferred_odds_hi": 2.60,
            "alt_preferred_odds_lo": 1.80,
            "promo_mid_band_boost": 60.0,
            "promo_alt_boost": 14.0,
            "promo_short_chalk_penalty": -55.0,
            "promo_fav_hc_boost": 12.0,
            "promo_natural_total_boost": 10.0,
            "fail_odds_below": 1.40,
            "fail_odds_above": 4.0,
            "pass_odds_lo": 1.40,
            "pass_odds_hi": 2.60,
        },
        "coverage_floor": {
            "enabled": True,
            "top_promo_scaffold_pct": 0.20,
            "sport_rotation_min_lines": 5,
            "require_real_pack": True,
            "coverage_pressure_boost": 40.0,
            # Optional mirror of learning.control_signals.temp_ev_relax (prefer control_signals)
            "ev_relax": {
                "enabled": True,
                "delta_min": 0.01,
                "delta_max": 0.02,
                "ttl_hours": 24,
                "clear_on_settle": True,
                "stake_mult": 0.80,
                "top_n_survivors": 3,
                "min_board_matches": 15,
                "require_coverage_warn": True,
                "exclude_high_odds": True,
                "exclude_grade_c": True,
            },
        },
        # Legacy flat gate keys (aliased into research.gates by research_gates package)
        "require_lineup_status_football": True,
        "predicted_lineup_ok_for_totals_btts": True,
        "require_injury_research_if_predicted": True,
        "require_confirmed_lineup_for_totals_btts": False,
        "high_rotation_stricter_lineup": True,
        "high_rotation_require_confirmed": False,
        "high_odds_prefer_confirmed_lineup": True,
        "lineup_gate_all_football": False,
        "reject_script_conflict": True,
        "reject_base_rate_conflict": True,
        # Nested multi-sport gates (preferred)
        "gates": {
            "enabled": True,
            "reject_script_conflict": True,
            "reject_base_rate_conflict": True,
            "require_availability_status": True,
            "predicted_availability_ok": True,
            "require_availability_research_if_predicted": True,
            "high_context_stricter_notes": True,
            "high_context_min_notes_chars": 40,
            "high_context_require_confirmed": True,
            "strict_confirmed_only": False,
            "high_odds_prefer_confirmed": True,
            "sports": {
                "football": {"enabled": True},
                "tennis": {"enabled": True},
                "basketball": {"enabled": True},
                "default": {"enabled": True},
            },
        },
    }
    # Deep-merge gates / tiers if user provided partial
    out = {**defaults, **raw}
    if isinstance(raw.get("gates"), dict) or defaults.get("gates"):
        base_g = dict(defaults.get("gates") or {})
        user_g = dict(raw.get("gates") or {})
        sports = dict(base_g.get("sports") or {})
        for sk, sv in (user_g.get("sports") or {}).items():
            if isinstance(sv, dict):
                sports[sk] = {**(sports.get(sk) or {}), **sv}
            else:
                sports[sk] = sv
        merged_g = {**base_g, **user_g, "sports": sports}
        out["gates"] = merged_g
    if isinstance(raw.get("tiers"), dict) or defaults.get("tiers"):
        out["tiers"] = {**(defaults.get("tiers") or {}), **(raw.get("tiers") or {})}
    return out


def simulation_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    """Football sim + calibration (optional v6). Nested under simulation: in config."""
    raw = dict(cfg.get("simulation") or {})
    football = dict(raw.get("football") or {})
    defaults = {
        "enabled": True,
        "calibration_enabled": True,
        "audit_sims": True,
        "default_league_avg_xg": 1.35,
        "default_home_advantage": 1.08,
        "default_rho": -0.05,
        "max_goals": 10,
        "sport_scope": ["football"],  # do not expand lightly
    }
    # flatten football overrides
    for k, v in football.items():
        if k not in ("enabled",):
            defaults[k] = v
    out = {**defaults, **{k: v for k, v in raw.items() if k != "football"}}
    if raw.get("enabled") is False:
        out["enabled"] = False
    if football.get("enabled") is False:
        out["enabled"] = False
    return out
