"""
Capital v2 pure foundation + unit stake sizing (Phases 2.1–2.3).

Unit ladder, size modes, peak/DD (settlement-day), secure-transfer math,
portfolio open-risk limit helpers, NT floor, unit-based stake decisions.

Live risk/sizing gated by ``capital_v2.enabled`` (default false). Pure helpers
here have no file I/O. StakeDecision is emitted in-memory (JSONL later).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Literal

from nt.bets_io import fnum, is_performance_settled, settlement_calendar_day

RULE_BUNDLE_VERSION = "br_v2.0.0"
STAKE_DECISION_SCHEMA_VERSION = 1

SizeMode = Literal["NORMAL", "REDUCED", "FROZEN"]


# ── defaults (overridable via capital_v2_cfg) ─────────────────────────────

# High-Volume v2: base unit 12 under 1500 liquid (was 10).
DEFAULT_UNIT_LADDER: list[dict[str, Any]] = [
    {"max_liquid_exclusive": 1500.0, "unit": 12.0},
    {"max_liquid_exclusive": 2500.0, "unit": 15.0},
    {"max_liquid_exclusive": None, "unit": 20.0},
]

DEFAULT_GRADE_STAKE_MULT: dict[str, float] = {
    "C": 1.0,
    "B": 1.4,
    "A": 2.0,
    "A_high_conf": 2.2,
}


def capital_v2_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Merge capital_v2 section with design defaults. Does not enable live risk."""
    raw = dict((cfg or {}).get("capital_v2") or {})
    nt_floor = float(((cfg or {}).get("norsk_tipping") or {}).get("min_stake_nok") or 10.0)
    defaults: dict[str, Any] = {
        "enabled": False,  # live risk/sizing OFF until Phase 2.7
        "rule_bundle_version": RULE_BUNDLE_VERSION,
        "min_stake_nok": nt_floor,
        "unit_ladder": list(DEFAULT_UNIT_LADDER),
        "drawdown": {
            "reduce_at": 0.15,
            "freeze_at": 0.25,
            "reduce_mode": "half_unit",  # half of active unit; step down if < floor
        },
        "daily_loss": {
            "hard_pct_of_liquid": 0.04,
            "hard_units": 3.0,
            "soft_pct_of_liquid": 0.02,
            "shrink_remaining": True,
        },
        "weekly_loss": {
            "hard_pct_of_liquid": 0.08,
            "hard_units": 6.0,
            "soft_pct_of_liquid": 0.05,
        },
        "portfolio_open_risk": {
            # Max simultaneous open (Pending+ConfirmedPlaced) as fraction of
            # riskable liquid *before* new stakes (equity - secure - open).
            "max_pct_of_riskable_liquid": 0.18,
        },
        "secure_bucket": {
            "enabled": True,
            # Variant A (live default): soft 1.25×/15%, hard 1.50×/30% (hard replaces soft)
            "variant": "A",
            "soft_trigger_multiple_of_ref": 1.25,
            "soft_transfer_fraction": 0.15,
            "hard_trigger_multiple_of_ref": 1.50,
            "hard_transfer_fraction": 0.30,
            # Variant B legacy single-tier (1.30× / 0.27) — still parsed if variant=B or soft/hard unset
            "trigger_multiple_of_ref": 1.30,
            "transfer_fraction_of_profit_above_ref": 0.27,
            # Softener: after transfer, working equity ≥ max(frac×ledger, units×unit)
            "min_working_frac_of_equity": 0.55,
            "min_working_units": 8.0,
            # Unlock secure → liquid
            "unlock_after_settled": 25,
            "manual_unlock_cooldown_days": 7,
        },
        "grade_stake_mult": dict(DEFAULT_GRADE_STAKE_MULT),
        "kelly": {
            "enabled": True,
            "enabled_above_liquid": 1500.0,
            "fraction_cap": 0.30,
            "max_units": 1.5,
            "max_brier": 0.28,
            "min_calibration_n": 30,
            "brier_soft_scale": True,
        },
        "audit": {
            "stake_decisions_jsonl": "data/state/stake_decisions.jsonl",
        },
        "segments_path_key": "capital_segments",  # under state_dir if not in paths
    }
    # shallow merge top-level; nested dicts merge one level
    out = {**defaults, **raw}
    for k in (
        "drawdown",
        "daily_loss",
        "weekly_loss",
        "portfolio_open_risk",
        "secure_bucket",
        "kelly",
        "audit",
        "grade_stake_mult",
    ):
        if isinstance(raw.get(k), dict):
            out[k] = {**(defaults.get(k) or {}), **raw[k]}
    if raw.get("unit_ladder"):
        out["unit_ladder"] = list(raw["unit_ladder"])
    out["min_stake_nok"] = float(out.get("min_stake_nok") or nt_floor)
    # Environment override (Phase 2.7) — default remains false unless explicitly set.
    # Accept: CAPITAL_V2_ENABLED or NT_CAPITAL_V2_ENABLED = 1|true|yes|on
    import os

    env_raw = (os.environ.get("CAPITAL_V2_ENABLED") or os.environ.get("NT_CAPITAL_V2_ENABLED") or "").strip()
    if env_raw:
        out["enabled"] = env_raw.lower() in ("1", "true", "yes", "on")
    return out


# ── NT floor / whole kroner ───────────────────────────────────────────────


def whole_krone(x: float) -> float:
    """Integer NOK (floor toward zero for positive stakes)."""
    if x <= 0:
        return 0.0
    return float(int(x))


def apply_nt_floor(stake: float, min_stake: float) -> float:
    """
    Fail-closed floor: if stake is positive but below min_stake → 0.
    Never return a partial illegal stake in (0, min_stake).
    """
    min_stake = float(min_stake)
    stake = float(stake)
    if stake <= 0:
        return 0.0
    if stake + 1e-9 < min_stake:
        return 0.0
    return whole_krone(stake)


# ── Unit ladder ───────────────────────────────────────────────────────────


def unit_size(working_liquid: float, cfg_v2: dict[str, Any] | None = None) -> float:
    """
    Absolute unit in NOK from working liquid (riskable liquid before new stakes).

    Ladder (Set B): <1500 → 10; <2500 → 15; else → 20.
    Always at least min_stake_nok.
    """
    v2 = cfg_v2 or capital_v2_cfg({})
    floor = float(v2.get("min_stake_nok") or 10.0)
    liquid = max(0.0, float(working_liquid))
    ladder = v2.get("unit_ladder") or DEFAULT_UNIT_LADDER
    chosen = float(ladder[-1].get("unit") or 20.0)
    for step in ladder:
        cap = step.get("max_liquid_exclusive")
        u = float(step.get("unit") or floor)
        if cap is None:
            chosen = u
            break
        if liquid < float(cap):
            chosen = u
            break
    return max(floor, chosen)


def reduced_unit(active_unit: float, min_stake: float) -> float:
    """
    REDUCED at 15% DD: exactly half current unit, or next lower ladder step
    if half would fall below floor — never below min_stake.
    """
    min_stake = float(min_stake)
    u = float(active_unit)
    half = whole_krone(u / 2.0)
    if half >= min_stake:
        return half
    # step down ladder
    for step_u in (20.0, 15.0, 12.0, 10.0):
        if step_u < u and step_u >= min_stake:
            return step_u
    return min_stake


def active_unit_for_mode(
    unit_size_nok: float,
    size_mode: str,
    min_stake: float,
) -> float:
    """Unit after size_mode (NORMAL / REDUCED / FROZEN→0)."""
    mode = (size_mode or "NORMAL").upper()
    if mode == "FROZEN":
        return 0.0
    u = max(float(min_stake), float(unit_size_nok))
    if mode == "REDUCED":
        return reduced_unit(u, min_stake)
    return u


# ── Unit stake decision (Phase 2.3 pure sizing) ────────────────────────────


@dataclass
class StakeDecision:
    """Structured stake decision (emitted in-memory; JSONL persistence later)."""

    schema_version: int
    rule_bundle_version: str
    match: str
    selection: str
    recommended_stake_nok: float
    final_stake_nok: float
    reject_reason: str | None
    size_mode: str
    unit_size_nok: float
    active_unit_nok: float
    remaining_room_nok: float
    min_stake_nok: float
    constraints_applied: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)

    def to_audit_dict(self) -> dict[str, Any]:
        """Shape aligned with design §4.7 stake_decisions.jsonl (no bet_id/ts yet)."""
        d = asdict(self)
        return d


def grade_stake_multiplier(
    grade: str,
    *,
    high_confidence: bool = False,
    v2: dict[str, Any] | None = None,
) -> float:
    """
    High-Volume v2 grade stake mults: C 1.0 · B 1.4 · A 2.0 · A high-conf 2.2.
    """
    mults = dict(DEFAULT_GRADE_STAKE_MULT)
    if v2 and isinstance(v2.get("grade_stake_mult"), dict):
        mults.update({str(k).upper(): float(v) for k, v in v2["grade_stake_mult"].items()})
    g = (grade or "C").strip().upper()
    if g == "A" and high_confidence:
        return float(mults.get("A_HIGH_CONF") or mults.get("A_high_conf") or 2.2)
    if g in mults:
        return float(mults[g])
    # map A_high_conf key variants
    if g == "A":
        return float(mults.get("A") or 2.0)
    if g == "B":
        return float(mults.get("B") or 1.4)
    return float(mults.get("C") or 1.0)


def compute_unit_stake(
    *,
    size_mode: str,
    unit_size_nok: float,
    remaining_room_nok: float,
    min_stake: float = 10.0,
    stopped: bool = False,
    can_bet: bool = True,
    high_odds: bool = False,
    high_odds_mult: float = 1.0,
    learning_stake_mult: float = 1.0,
    grade_mult: float = 1.0,
    match: str = "",
    selection: str = "",
    inputs: dict[str, Any] | None = None,
    rule_bundle_version: str = RULE_BUNDLE_VERSION,
) -> StakeDecision:
    """
    Pure per-bet unit sizing (capital_v2).

    NORMAL → full unit; REDUCED → half / next lower step; FROZEN or risk stop → 0.
    Grade mult (High-Volume v2) scales unit before room clip.
    Clip to remaining open-risk room; whole kroner; never (0, min_stake).
    """
    min_stake = float(min_stake)
    room = max(0.0, float(remaining_room_nok))
    mode = (size_mode or "NORMAL").upper()
    constraints: list[str] = []
    base_inputs = dict(inputs or {})
    base_inputs.setdefault("size_mode", mode)
    base_inputs.setdefault("unit_size", float(unit_size_nok))
    base_inputs.setdefault("remaining_room", room)
    base_inputs.setdefault("high_odds", high_odds)
    base_inputs.setdefault("learning_stake_mult", float(learning_stake_mult or 1.0))
    base_inputs.setdefault("grade_mult", float(grade_mult or 1.0))
    def _done(
        final: float,
        *,
        recommended: float | None = None,
        reason: str | None = None,
        active: float = 0.0,
    ) -> StakeDecision:
        return StakeDecision(
            schema_version=STAKE_DECISION_SCHEMA_VERSION,
            rule_bundle_version=rule_bundle_version,
            match=match,
            selection=selection,
            recommended_stake_nok=float(recommended if recommended is not None else final),
            final_stake_nok=float(final),
            reject_reason=reason,
            size_mode=mode if not (stopped or not can_bet) else "FROZEN",
            unit_size_nok=float(unit_size_nok),
            active_unit_nok=float(active),
            remaining_room_nok=room,
            min_stake_nok=min_stake,
            constraints_applied=list(constraints),
            inputs=base_inputs,
        )

    if stopped or not can_bet or mode == "FROZEN":
        constraints.append("frozen_or_stopped")
        return _done(0.0, reason="frozen_or_stopped", active=0.0)

    active = active_unit_for_mode(unit_size_nok, mode, min_stake)
    constraints.append(f"unit_ladder:{whole_krone(unit_size_nok)}")
    if mode == "REDUCED":
        constraints.append(f"reduced_unit:{active}")

    if active + 1e-9 < min_stake:
        constraints.append("active_unit_below_floor")
        return _done(0.0, recommended=active, reason="active_unit_below_floor", active=active)

    # Target stake = active unit × grade mult (High-Volume v2) × high-odds / learning
    raw = float(active)
    gm = max(0.5, float(grade_mult or 1.0))
    if abs(gm - 1.0) > 0.01:
        raw *= gm
        constraints.append(f"grade_mult:{gm}")
    if high_odds and float(high_odds_mult) > 0:
        raw *= float(high_odds_mult)
        constraints.append(f"high_odds_mult:{high_odds_mult}")
    raw *= max(0.5, float(learning_stake_mult or 1.0))
    if abs(float(learning_stake_mult or 1.0) - 1.0) > 0.01:
        constraints.append(f"learning_stake_mult:{learning_stake_mult}")

    recommended = whole_krone(raw)
    # Mult must not create illegal partial: hold at floor when unit was legal
    if 0 < recommended < min_stake:
        recommended = min_stake
        constraints.append("clamp_up_to_floor_after_mult")

    constraints.append(f"nt_floor:{min_stake}")
    constraints.append(f"remaining_room:{room}")

    clipped = min(recommended, room)
    final = apply_nt_floor(clipped, min_stake)
    if final <= 0:
        reason = "insufficient_remaining_room" if room + 1e-9 < min_stake else "stake_below_floor_after_clip"
        constraints.append(reason)
        return _done(0.0, recommended=recommended, reason=reason, active=active)

    constraints.append(f"final:{final}")
    return _done(final, recommended=recommended, reason=None, active=active)


# ── Size mode from drawdown ───────────────────────────────────────────────


def size_mode_from_dd(
    dd_from_peak: float,
    *,
    freeze_active: bool = False,
    reduce_at: float = 0.15,
    freeze_at: float = 0.25,
) -> SizeMode:
    if freeze_active or dd_from_peak >= freeze_at - 1e-12:
        return "FROZEN"
    if dd_from_peak >= reduce_at - 1e-12:
        return "REDUCED"
    return "NORMAL"


# ── Peak equity & drawdown (settlement-day consistent) ────────────────────


def peak_equity_settlement(
    rows: list[dict[str, str]],
    baseline: float,
) -> float:
    """
    Max end-of-day equity on the **settlement calendar day** curve
    (Europe/Oslo via updated_at). Performance-settled only (Win/Loss/Refunded).
    """
    baseline = float(baseline)
    settled = [r for r in rows if is_performance_settled(r.get("result"))]
    if not settled:
        return round(baseline, 2)

    def sort_key(r: dict[str, str]) -> tuple[str, str]:
        d = settlement_calendar_day(r) or (r.get("date") or "")
        ts = r.get("updated_at") or r.get("created_at") or ""
        return (d, ts)

    settled.sort(key=sort_key)
    peak = baseline
    cum = 0.0
    by_day: dict[str, float] = {}
    for r in settled:
        cum += fnum(r.get("p_l_nok")) or 0.0
        d = settlement_calendar_day(r) or (r.get("date") or "")
        if not d:
            continue
        by_day[d] = baseline + cum
    for eq in by_day.values():
        if eq > peak:
            peak = eq
    # also consider running peak after each bet (intra-day)
    cum = 0.0
    eq = baseline
    if eq > peak:
        peak = eq
    for r in settled:
        cum += fnum(r.get("p_l_nok")) or 0.0
        eq = baseline + cum
        if eq > peak:
            peak = eq
    return round(peak, 2)


def drawdown_from_peak(equity: float, peak: float) -> float:
    """Fraction in [0, 1]. Peak ≤ 0 → 0."""
    peak = float(peak)
    equity = float(equity)
    if peak <= 0:
        return 0.0
    return max(0.0, min(1.0, (peak - equity) / peak))


# ── Riskable liquid & portfolio open-risk limit ───────────────────────────


def riskable_equity(ledger_equity: float, secure_nok: float) -> float:
    """Equity available for risk = ledger equity − secure bucket."""
    return max(0.0, round(float(ledger_equity) - float(secure_nok), 2))


def riskable_liquid(ledger_equity: float, secure_nok: float, open_risk: float) -> float:
    """Riskable equity minus open Pending+ConfirmedPlaced stakes."""
    return max(0.0, round(riskable_equity(ledger_equity, secure_nok) - float(open_risk), 2))


def portfolio_open_risk_cap(
    riskable_liquid_before_new: float,
    *,
    max_pct: float = 0.18,
) -> float:
    """
    Max simultaneous open risk (Pending+ConfirmedPlaced), NOK.

    Cap = max_pct × riskable liquid *before* adding new stakes
    (equity − secure − already-open). Set B addition.
    """
    liq = max(0.0, float(riskable_liquid_before_new))
    pct = max(0.0, float(max_pct))
    return round(liq * pct, 2)


def portfolio_open_room(
    open_risk_now: float,
    riskable_liquid_before_new: float,
    *,
    max_pct: float = 0.18,
) -> float:
    """
    Additional stake room under portfolio open-risk limit.

    Cap on simultaneous open risk = max_pct × riskable_liquid_before_new
    where riskable liquid = equity − secure − already-open.
    Room = max(0, cap − open_risk_now).
    """
    cap = portfolio_open_risk_cap(riskable_liquid_before_new, max_pct=max_pct)
    room = cap - float(open_risk_now)
    return max(0.0, round(room, 2))


# ── Loss limit helpers (pure; used by 2.2 later) ──────────────────────────


def loss_limit_nok(
    liquid_start: float,
    unit_size_nok: float,
    *,
    pct: float,
    units: float,
) -> float:
    """Hard loss magnitude = min(pct * liquid, units * unit_size)."""
    a = max(0.0, float(pct)) * max(0.0, float(liquid_start))
    b = max(0.0, float(units)) * max(0.0, float(unit_size_nok))
    if a <= 0 and b <= 0:
        return 0.0
    if a <= 0:
        return round(b, 2)
    if b <= 0:
        return round(a, 2)
    return round(min(a, b), 2)


def is_hard_loss_stopped(realized_pl: float, limit_nok: float) -> bool:
    """True if realized P/L (negative on losses) has hit/exceeded hard limit."""
    if limit_nok <= 0:
        return False
    return float(realized_pl) <= -float(limit_nok) + 1e-9


# ── Secure bucket transfer (pure) ─────────────────────────────────────────


@dataclass
class SecureTransferResult:
    transferred: float
    secure_after: float
    ref_hwm_after: float
    working_equity_after: float
    triggered: bool
    reason: str
    min_working_required: float = 0.0
    transfer_capped_by_buffer: bool = False
    # Variant A tier: "soft" | "hard" | "legacy" | None (no trigger)
    tier: str | None = None
    transfer_capped_by_liquid_floor: bool = False
    liquid_floor_required: float = 0.0


def min_working_buffer_nok(
    ledger_equity: float,
    *,
    unit_size_nok: float = 10.0,
    min_working_frac: float = 0.55,
    min_working_units: float = 8.0,
) -> float:
    """
    Minimum working equity that must remain after a secure transfer.
    max(frac × ledger equity, units × current unit).
    """
    eq = max(0.0, float(ledger_equity))
    u = max(0.0, float(unit_size_nok))
    by_frac = float(min_working_frac) * eq
    by_units = float(min_working_units) * u
    return round(max(by_frac, by_units), 2)


def _resolve_secure_tier(
    *,
    equity: float,
    ref: float,
    trigger_multiple: float,
    transfer_fraction: float,
    soft_trigger_multiple: float | None,
    soft_transfer_fraction: float | None,
    hard_trigger_multiple: float | None,
    hard_transfer_fraction: float | None,
) -> tuple[str | None, float, float]:
    """
    Pick skim tier and (trigger_level, fraction).

    Variant A: hard (if equity ≥ hard trigger) replaces soft — never stacked.
    Legacy single-tier when soft/hard not configured.
    Returns (tier, trigger_equity, fraction) or (None, trigger, 0) when below all.
    """
    use_variant_a = (
        soft_trigger_multiple is not None
        and soft_transfer_fraction is not None
        and hard_trigger_multiple is not None
        and hard_transfer_fraction is not None
    )
    if use_variant_a:
        hard_trig = ref * float(hard_trigger_multiple)
        soft_trig = ref * float(soft_trigger_multiple)
        if equity + 1e-9 >= hard_trig:
            return "hard", hard_trig, float(hard_transfer_fraction)
        if equity + 1e-9 >= soft_trig:
            return "soft", soft_trig, float(soft_transfer_fraction)
        return None, soft_trig, 0.0
    # Legacy / Variant B single trigger
    trig = ref * float(trigger_multiple)
    if equity + 1e-9 >= trig:
        return "legacy", trig, float(transfer_fraction)
    return None, trig, 0.0


def compute_secure_transfer(
    *,
    ledger_equity: float,
    secure_nok: float,
    ref_hwm: float,
    trigger_multiple: float = 1.30,
    transfer_fraction: float = 0.27,  # Variant B legacy single-tier (was 0.40)
    unit_size_nok: float | None = None,
    min_working_frac: float = 0.55,
    min_working_units: float = 8.0,
    # Variant A soft/hard (when all four set, hard replaces soft — not stacked)
    soft_trigger_multiple: float | None = None,
    soft_transfer_fraction: float | None = None,
    hard_trigger_multiple: float | None = None,
    hard_transfer_fraction: float | None = None,
    # Never skim if post-skim liquid would fall below phase daily_risk_ceil
    phase_daily_risk_ceil: float | None = None,
    open_risk: float = 0.0,
) -> SecureTransferResult:
    """
    When equity hits a secure-bucket trigger, move a fraction of
    (equity - ref_hwm) into secure, subject to:
    - never secure more than current working equity (secure ≤ equity)
    - after transfer, working ≥ max(55% equity, 8 × unit) (softener)
    - after transfer, liquid (equity − secure_after − open_risk) ≥ phase daily_risk_ceil
      when phase_daily_risk_ceil is provided

    Variant A (preferred): soft 1.25×/15%, hard 1.50×/30% (hard only if hard fires).
    Legacy: single trigger_multiple / transfer_fraction.

    Reset ref HWM to **new working equity** after transfer.
    """
    equity = float(ledger_equity)
    secure = max(0.0, float(secure_nok))
    ref = float(ref_hwm)
    if ref <= 0:
        ref = equity
    unit = float(unit_size_nok) if unit_size_nok is not None else unit_size(
        riskable_equity(equity, secure)
    )
    min_work = min_working_buffer_nok(
        equity,
        unit_size_nok=unit,
        min_working_frac=min_working_frac,
        min_working_units=min_working_units,
    )
    open_r = max(0.0, float(open_risk))
    liquid_floor = (
        max(0.0, float(phase_daily_risk_ceil))
        if phase_daily_risk_ceil is not None
        else 0.0
    )

    tier, _trig_level, frac = _resolve_secure_tier(
        equity=equity,
        ref=ref,
        trigger_multiple=trigger_multiple,
        transfer_fraction=transfer_fraction,
        soft_trigger_multiple=soft_trigger_multiple,
        soft_transfer_fraction=soft_transfer_fraction,
        hard_trigger_multiple=hard_trigger_multiple,
        hard_transfer_fraction=hard_transfer_fraction,
    )
    working_before = riskable_equity(equity, secure)
    if tier is None:
        return SecureTransferResult(
            transferred=0.0,
            secure_after=secure,
            ref_hwm_after=ref,
            working_equity_after=working_before,
            triggered=False,
            reason="below_trigger",
            min_working_required=min_work,
            tier=None,
            liquid_floor_required=liquid_floor,
        )

    profit_above = equity - ref
    transfer = whole_krone(float(frac) * profit_above)
    # Cap 1: cannot move more than current working
    max_by_working = whole_krone(working_before)
    # Cap 2: leave minimum working buffer
    room_above_buffer = working_before - min_work
    max_by_buffer = whole_krone(max(0.0, room_above_buffer))
    # Cap 3: liquid floor — equity − secure_after − open ≥ daily_risk_ceil
    # ⇒ secure_after ≤ equity − open − ceil ⇒ transfer ≤ that − secure
    capped_by_liquid = False
    max_by_liquid = max_by_working  # no extra cap when floor unset
    if phase_daily_risk_ceil is not None:
        max_secure_total = equity - open_r - liquid_floor
        max_by_liquid = whole_krone(max(0.0, max_secure_total - secure))

    capped_by_buffer = False
    if max_by_working >= 1.0:
        if transfer > max_by_buffer + 1e-9:
            capped_by_buffer = True
        if transfer > max_by_liquid + 1e-9:
            capped_by_liquid = True
        transfer = min(transfer, max_by_working, max_by_buffer, max_by_liquid)
    else:
        transfer = 0.0

    if transfer < 1.0:
        reason = "transfer_below_1_nok_or_buffer"
        if phase_daily_risk_ceil is not None and max_by_liquid < 1.0:
            reason = "liquid_floor_blocks_skim"
            capped_by_liquid = True
        elif capped_by_buffer or max_by_buffer < 1.0:
            reason = "transfer_below_1_nok_or_buffer"
        return SecureTransferResult(
            transferred=0.0,
            secure_after=secure,
            ref_hwm_after=ref,
            working_equity_after=working_before,
            triggered=False,
            reason=reason,
            min_working_required=min_work,
            transfer_capped_by_buffer=capped_by_buffer or max_by_buffer < 1.0,
            tier=None,
            transfer_capped_by_liquid_floor=capped_by_liquid,
            liquid_floor_required=liquid_floor,
        )

    secure_after = round(secure + transfer, 2)
    if secure_after > equity:
        secure_after = round(equity, 2)
        transfer = round(max(0.0, secure_after - secure), 2)
    working_after = riskable_equity(equity, secure_after)

    # Final buffer enforce (float safety)
    if working_after + 1e-9 < min_work and transfer >= 1.0:
        allowed_secure = round(max(0.0, equity - min_work), 2)
        if allowed_secure + 1e-9 < secure:
            return SecureTransferResult(
                transferred=0.0,
                secure_after=secure,
                ref_hwm_after=ref,
                working_equity_after=working_before,
                triggered=False,
                reason="already_at_working_buffer",
                min_working_required=min_work,
                transfer_capped_by_buffer=True,
                tier=None,
                liquid_floor_required=liquid_floor,
            )
        transfer = whole_krone(max(0.0, allowed_secure - secure))
        if transfer < 1.0:
            return SecureTransferResult(
                transferred=0.0,
                secure_after=secure,
                ref_hwm_after=ref,
                working_equity_after=working_before,
                triggered=False,
                reason="transfer_below_1_nok_or_buffer",
                min_working_required=min_work,
                transfer_capped_by_buffer=True,
                tier=None,
                liquid_floor_required=liquid_floor,
            )
        secure_after = round(secure + transfer, 2)
        working_after = riskable_equity(equity, secure_after)
        capped_by_buffer = True

    # Final liquid-floor enforce
    if phase_daily_risk_ceil is not None:
        liquid_after = equity - secure_after - open_r
        if liquid_after + 1e-9 < liquid_floor and transfer >= 1.0:
            allowed_secure = round(max(0.0, equity - open_r - liquid_floor), 2)
            if allowed_secure + 1e-9 < secure:
                return SecureTransferResult(
                    transferred=0.0,
                    secure_after=secure,
                    ref_hwm_after=ref,
                    working_equity_after=working_before,
                    triggered=False,
                    reason="liquid_floor_blocks_skim",
                    min_working_required=min_work,
                    transfer_capped_by_liquid_floor=True,
                    tier=None,
                    liquid_floor_required=liquid_floor,
                )
            transfer = whole_krone(max(0.0, allowed_secure - secure))
            if transfer < 1.0:
                return SecureTransferResult(
                    transferred=0.0,
                    secure_after=secure,
                    ref_hwm_after=ref,
                    working_equity_after=working_before,
                    triggered=False,
                    reason="liquid_floor_blocks_skim",
                    min_working_required=min_work,
                    transfer_capped_by_liquid_floor=True,
                    tier=None,
                    liquid_floor_required=liquid_floor,
                )
            secure_after = round(secure + transfer, 2)
            working_after = riskable_equity(equity, secure_after)
            capped_by_liquid = True

    ref_after = working_after
    reason_bits = [f"secure_transfer_{tier}"]
    if capped_by_buffer:
        reason_bits.append("buffer_capped")
    if capped_by_liquid:
        reason_bits.append("liquid_floor_capped")
    return SecureTransferResult(
        transferred=transfer,
        secure_after=secure_after,
        ref_hwm_after=ref_after,
        working_equity_after=working_after,
        triggered=True,
        reason="_".join(reason_bits) if len(reason_bits) > 1 else reason_bits[0],
        min_working_required=min_work,
        transfer_capped_by_buffer=capped_by_buffer,
        tier=tier,
        transfer_capped_by_liquid_floor=capped_by_liquid,
        liquid_floor_required=liquid_floor,
    )


def compute_secure_transfer_variant_a(
    *,
    ledger_equity: float,
    secure_nok: float,
    ref_hwm: float,
    soft_trigger_multiple: float = 1.25,
    soft_transfer_fraction: float = 0.15,
    hard_trigger_multiple: float = 1.50,
    hard_transfer_fraction: float = 0.30,
    unit_size_nok: float | None = None,
    min_working_frac: float = 0.55,
    min_working_units: float = 8.0,
    phase_daily_risk_ceil: float | None = None,
    open_risk: float = 0.0,
) -> SecureTransferResult:
    """Variant A skim: soft 1.25×/15%, hard 1.50×/30% (hard replaces soft)."""
    return compute_secure_transfer(
        ledger_equity=ledger_equity,
        secure_nok=secure_nok,
        ref_hwm=ref_hwm,
        soft_trigger_multiple=soft_trigger_multiple,
        soft_transfer_fraction=soft_transfer_fraction,
        hard_trigger_multiple=hard_trigger_multiple,
        hard_transfer_fraction=hard_transfer_fraction,
        unit_size_nok=unit_size_nok,
        min_working_frac=min_working_frac,
        min_working_units=min_working_units,
        phase_daily_risk_ceil=phase_daily_risk_ceil,
        open_risk=open_risk,
    )


# ── Day / week ids (Europe/Oslo) ──────────────────────────────────────────


def oslo_today() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Europe/Oslo")).date().isoformat()
    except Exception:
        return date.today().isoformat()


def oslo_iso_week_id(d: str | None = None) -> str:
    """ISO week id YYYY-Www in Europe/Oslo calendar."""
    if d:
        y, m, day = (int(x) for x in d[:10].split("-"))
        dt = date(y, m, day)
    else:
        try:
            from zoneinfo import ZoneInfo

            dt = datetime.now(ZoneInfo("Europe/Oslo")).date()
        except Exception:
            dt = date.today()
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def empty_segments(
    *,
    baseline_nok: float = 500.0,
    oslo_date: str | None = None,
) -> dict[str, Any]:
    """Canonical capital_segments.json structure (Phase 2.1)."""
    day = oslo_date or oslo_today()
    return {
        "schema_version": 1,
        "rule_bundle_version": RULE_BUNDLE_VERSION,
        "secure_nok": 0.0,
        "secure_transfers": [],
        "unit_hwm_reset_equity_nok": float(baseline_nok),
        # Unlock epoch: settled_count at last skim (or unlock). Auto-unlock after N more.
        "secure_lock_settled_count": 0,
        "last_manual_unlock_at": None,
        "secure_unlocks": [],
        "freeze": {
            "active": False,
            "reason": None,
            "activated_at": None,
            "unfreeze_requires": "manual",
        },
        "day_snapshot": {
            "oslo_date": day,
            "liquid_start_nok": None,
            "unit_size_nok": 10.0,
            "realized_pl_nok": 0.0,
        },
        "week_snapshot": {
            "week_id": oslo_iso_week_id(day),
            "liquid_start_nok": None,
            "unit_size_nok": 10.0,
            "realized_pl_nok": 0.0,
        },
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
