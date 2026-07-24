from __future__ import annotations

import json
from typing import Any

from nt.bets_io import band_roi_stats, is_open_risk, load_bets
from nt.config import path_from_config


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _load_light_latest(cfg: dict[str, Any]) -> dict[str, Any] | None:
    """Soft-load outbox/light_research/LATEST.json (or today's batch)."""
    try:
        outbox = path_from_config(cfg, "outbox")
        latest = outbox / "light_research" / "LATEST.json"
        if latest.is_file():
            data = json.loads(latest.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        # Fallback: day-stamped batch via light_research helper
        try:
            from nt.light_research import load_light_batch

            payload = load_light_batch(cfg)
            if payload and (payload.get("records") or payload.get("shortlist_n")):
                return payload
        except Exception:
            pass
    except Exception:
        pass
    return None


def _load_deep_queue_state(cfg: dict[str, Any]) -> dict[str, Any] | None:
    try:
        from nt.deep_queue_state import load_deep_queue_state

        return load_deep_queue_state(cfg)
    except Exception:
        return None


def _count_floor_tags(records: list[Any]) -> dict[str, int]:
    """Count coverage_floor annotation tags on light records."""
    scaffold = 0
    scaffold_blocked = 0
    rotation = 0
    rotation_blocked = 0
    rotation_none = 0
    for r in records or []:
        if isinstance(r, dict):
            note = f"{r.get('rough_ev_note') or ''} {r.get('reason') or ''}"
        else:
            note = f"{getattr(r, 'rough_ev_note', '') or ''} {getattr(r, 'reason', '') or ''}"
        if "coverage_floor:top_promo_scaffold:blocked" in note:
            scaffold_blocked += 1
        elif "coverage_floor:top_promo_scaffold" in note:
            scaffold += 1
        if "coverage_floor:sport_rotation:no_eligible" in note:
            rotation_none += 1
        elif "coverage_floor:sport_rotation:blocked" in note:
            rotation_blocked += 1
        elif "coverage_floor:sport_rotation" in note:
            rotation += 1
    return {
        "scaffold": scaffold,
        "scaffold_blocked": scaffold_blocked,
        "sport_rotation": rotation,
        "sport_rotation_blocked": rotation_blocked,
        "sport_rotation_no_eligible": rotation_none,
    }


def collect_coverage_floor_status(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Gather compact coverage-floor + temp_ev_relax operator snapshot.

    Soft-fail: never raises; missing files → partial / unavailable fields.
    """
    out: dict[str, Any] = {
        "available": False,
        "coverage_floor_enabled": None,
        "deep_target_n_effective": None,
        "board_lines": None,
        "deep_target_dynamic": None,
        "scaffold_pct": None,
        "sport_rotation_min_lines": None,
        "scaffold_tagged_n": None,
        "sport_rotation_tagged_n": None,
        "deep_queue_n": None,
        "temp_ev_relax": {
            "active": False,
            "delta_ev": 0.0,
            "stake_mult": 1.0,
            "expires_at": None,
            "line_keys_n": 0,
        },
        "notes": [],
    }

    # Config knobs (always available if cfg present)
    try:
        from nt.light_research import coverage_floor_cfg, dynamic_deep_target_n, tiers_cfg

        cfc = coverage_floor_cfg(cfg)
        tcfg = tiers_cfg(cfg)
        out["coverage_floor_enabled"] = bool(cfc.get("enabled", True))
        out["scaffold_pct"] = float(cfc.get("top_promo_scaffold_pct", 0.20) or 0.0)
        out["sport_rotation_min_lines"] = int(cfc.get("sport_rotation_min_lines", 5) or 0)
        out["deep_target_dynamic"] = bool(tcfg.get("deep_target_dynamic", False))
        out["deep_target_n_static"] = int(tcfg.get("deep_target_n") or 8)
        out["available"] = True
    except Exception as ex:  # noqa: BLE001
        out["notes"].append(f"cfg_unavailable:{ex}")
        cfc = {}
        tcfg = {}
        dynamic_deep_target_n = None  # type: ignore[assignment]

    light = _load_light_latest(cfg)
    board_lines: int | None = None
    if light:
        board_lines = _safe_int(light.get("shortlist_n"), 0) or None
        if board_lines is None:
            recs = light.get("records") or []
            if recs:
                board_lines = len(recs)
        tags = _count_floor_tags(list(light.get("records") or []))
        out["scaffold_tagged_n"] = tags["scaffold"]
        out["sport_rotation_tagged_n"] = tags["sport_rotation"]
        if tags["scaffold_blocked"] or tags["sport_rotation_blocked"] or tags["sport_rotation_no_eligible"]:
            out["notes"].append(
                "blocked_or_empty_rotation="
                f"scaffold_blocked:{tags['scaffold_blocked']},"
                f"rot_blocked:{tags['sport_rotation_blocked']},"
                f"rot_none:{tags['sport_rotation_no_eligible']}"
            )
        dq = light.get("deep_queue") or []
        if isinstance(dq, list):
            out["deep_queue_n"] = len(dq)
        comp = light.get("deep_queue_composition") or {}
        if isinstance(comp, dict) and comp.get("n") is not None:
            out["deep_queue_n"] = _safe_int(comp.get("n"), out.get("deep_queue_n") or 0)
        # light may carry temp_ev_relax emit result
        ter_payload = light.get("temp_ev_relax")
        if isinstance(ter_payload, dict) and ter_payload.get("ok") is False:
            reason = ter_payload.get("reason") or ter_payload.get("error")
            if reason:
                out["notes"].append(f"last_ter_emit:{reason}")

    dq_state = _load_deep_queue_state(cfg)
    if dq_state and out.get("deep_queue_n") is None:
        comp = dq_state.get("deep_queue_composition") or {}
        if isinstance(comp, dict) and comp.get("n") is not None:
            out["deep_queue_n"] = _safe_int(comp.get("n"), 0)
        else:
            q = dq_state.get("deep_queue") or []
            if isinstance(q, list):
                out["deep_queue_n"] = len(q)

    out["board_lines"] = board_lines
    # Only set deep_target_n_effective when we have a real board/shortlist size.
    # Without board size, keep effective=None and surface static via deep_target_n_static
    # so operators do not misread "effective=8" as this board's floor target.
    if dynamic_deep_target_n is not None and board_lines is not None:
        try:
            out["deep_target_n_effective"] = int(dynamic_deep_target_n(cfg, board_lines))
            out["deep_target_source"] = "board"
        except Exception as ex:  # noqa: BLE001
            out["notes"].append(f"target_compute:{ex}")
            out["deep_target_source"] = "unavailable"
    elif out.get("deep_target_n_static") is not None:
        out["deep_target_n_effective"] = None
        out["deep_target_source"] = "static_fallback_no_board"
        out["notes"].append("target_from_static_no_board")
    else:
        out["deep_target_source"] = "unavailable"

    # Active temp_ev_relax overlay (ControlSignals)
    try:
        from nt.control_signals import active_temp_ev_relax_overlay

        ov = active_temp_ev_relax_overlay(cfg)
        keys = list(ov.get("line_keys") or [])
        out["temp_ev_relax"] = {
            "active": bool(ov.get("active")),
            "delta_ev": float(ov.get("delta_ev") or 0.0),
            "stake_mult": float(ov.get("stake_mult") or 1.0),
            "expires_at": ov.get("expires_at"),
            "line_keys_n": len(keys),
            "n_signals": int(ov.get("n_signals") or 0),
            "sources": list(ov.get("sources") or [])[:4],
        }
        out["available"] = True
    except Exception as ex:  # noqa: BLE001
        out["notes"].append(f"temp_ev_relax_unavailable:{ex}")

    return out


def format_coverage_floor_section(info: dict[str, Any]) -> str:
    """Compact markdown block for operators."""
    lines = ["## Coverage floor", ""]
    if not info.get("available") and info.get("coverage_floor_enabled") is None:
        lines.append("_Coverage floor status unavailable (soft-fail)._")
        lines.append("")
        return "\n".join(lines)

    # deep_target — distinguish board-sized effective vs static fallback (no board)
    target = info.get("deep_target_n_effective")
    board = info.get("board_lines")
    dyn = info.get("deep_target_dynamic")
    src = info.get("deep_target_source")
    static_n = info.get("deep_target_n_static")
    target_bits = []
    if target is not None and src == "board":
        target_bits.append(f"**deep_target_n_effective**: {target}")
        meta = []
        if board is not None:
            meta.append(f"board/shortlist n={board}")
        if dyn is not None:
            meta.append("dynamic on" if dyn else "dynamic off")
        if meta:
            target_bits.append(f"({'; '.join(meta)})")
    elif src == "static_fallback_no_board" or (target is None and static_n is not None):
        # No board size — do not label static as "effective"
        dyn_s = "dynamic on" if dyn else "dynamic off" if dyn is not None else "dynamic n/a"
        target_bits.append(
            f"**deep_target_n_effective**: n/a (static fallback={static_n}; {dyn_s}; no board)"
        )
    else:
        target_bits.append("**deep_target_n_effective**: n/a")
    lines.append("- " + " ".join(target_bits))

    # floor config summary
    en = info.get("coverage_floor_enabled")
    if en is None:
        floor_s = "cfg n/a"
    elif en:
        pct = info.get("scaffold_pct")
        rot = info.get("sport_rotation_min_lines")
        pct_s = f"top {pct*100:.0f}% scaffold" if pct is not None else "scaffold n/a"
        rot_s = f"sport rotation ≥{rot} eligible" if rot is not None else "rotation n/a"
        floor_s = f"enabled · {pct_s} · {rot_s}"
    else:
        floor_s = "disabled"
    lines.append(f"- **coverage_floor**: {floor_s}")

    # tags / queue
    sc_n = info.get("scaffold_tagged_n")
    rot_n = info.get("sport_rotation_tagged_n")
    dq_n = info.get("deep_queue_n")
    tag_bits = []
    if sc_n is not None:
        tag_bits.append(f"scaffold tags={sc_n}")
    if rot_n is not None:
        tag_bits.append(f"sport_rotation tags={rot_n}")
    if dq_n is not None:
        tag_bits.append(f"deep_queue n={dq_n}")
    if tag_bits:
        lines.append(f"- light/queue: {', '.join(tag_bits)}")
    else:
        lines.append("- light/queue: _no light LATEST / deep_queue state_")

    # temp_ev_relax
    ter = info.get("temp_ev_relax") or {}
    if ter.get("active"):
        lines.append(
            f"- **temp_ev_relax**: active · ΔEV −{float(ter.get('delta_ev') or 0):.3f} · "
            f"stake×{float(ter.get('stake_mult') or 1):.2f} · "
            f"expires {ter.get('expires_at') or '?'} · "
            f"line_keys={int(ter.get('line_keys_n') or 0)}"
        )
    else:
        lines.append("- **temp_ev_relax**: inactive")

    notes = info.get("notes") or []
    if notes:
        # keep compact — one line max
        lines.append(f"- notes: {'; '.join(str(n) for n in notes[:3])}")

    lines.append("")
    return "\n".join(lines)


def collect_feh_status(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Compact FEH + test-cap flags for status.md (config only — no secrets).

    Soft-fail friendly: missing imports / keys yield safe defaults.
    """
    info: dict[str, Any] = {
        "enabled": False,
        "shadow_mode": True,
        "fail_closed": True,
        "place_owning": False,
        "checklist_required": True,
        "anti_soft_underdog": True,
        "side_first": True,
        "soft_ud_hard_band": "1.70–2.20",
        "soft_ud_outer": "2.60",
        "natural_market_elevation": False,
        "test_cap_line": "test_cap: disabled",
        "cards_onboarded": [],
        "notes": [],
    }
    try:
        sel = dict((cfg or {}).get("selection") or {})
        raw = dict(sel.get("evidence") or {})
        fh = dict(raw.get("forced_hierarchy") or {})
        info["enabled"] = bool(raw.get("enabled", False))
        info["shadow_mode"] = bool(raw.get("shadow_mode", True))
        info["fail_closed"] = bool(raw.get("fail_closed", True))
        fh_on = bool(fh.get("enabled", False))
        info["checklist_required"] = bool(fh.get("require_checklist", True))
        info["anti_soft_underdog"] = bool(fh.get("anti_soft_underdog", True))
        info["side_first"] = bool(fh.get("side_first", True))
        info["natural_market_elevation"] = bool(fh.get("natural_market_elevation", False))
        lo = float(fh.get("soft_ud_odds_lo") or 1.70)
        hi_h = float(fh.get("soft_ud_odds_hi_hard") or 2.20)
        hi_s = float(fh.get("soft_ud_odds_hi_soft") or 2.60)
        info["soft_ud_hard_band"] = f"{lo:g}–{hi_h:g}"
        info["soft_ud_outer"] = f"{hi_s:g}"
        try:
            from nt.evidence_hierarchy.score import place_uses_saef

            info["place_owning"] = bool(place_uses_saef(cfg))
        except Exception:
            info["place_owning"] = bool(
                info["enabled"] and not info["shadow_mode"] and fh_on
            )
            info["notes"].append("place_uses_saef import soft-fail")
        try:
            from nt.stake_test_cap import status_line

            info["test_cap_line"] = status_line(cfg)
        except Exception as exc:
            info["test_cap_line"] = f"test_cap: unavailable ({type(exc).__name__})"
            info["notes"].append("test_cap soft-fail")
        # Onboarded cards (names only — no pack contents / secrets)
        try:
            from nt.evidence_hierarchy.cards import sport_cards_dir

            p = sport_cards_dir(cfg)
            if p.is_dir():
                names = sorted(
                    f.stem
                    for f in p.glob("*.yaml")
                    if f.is_file() and not f.name.startswith("_")
                )
                info["cards_onboarded"] = names[:20]
        except Exception:
            info["notes"].append("cards list soft-fail")
    except Exception as exc:  # noqa: BLE001
        info["notes"].append(f"feh_status_error:{type(exc).__name__}")
    return info


def format_feh_section(info: dict[str, Any] | None) -> str:
    """Markdown ## Forced Evidence Hierarchy block (template — flags only)."""
    lines = ["## Forced Evidence Hierarchy", ""]
    if not info:
        lines.append("_FEH status unavailable (soft-fail)._")
        lines.append("")
        return "\n".join(lines)

    def _yn(v: Any) -> str:
        return "true" if bool(v) else "false"

    lines.append(
        f"- enabled: {_yn(info.get('enabled'))} | fail_closed: {_yn(info.get('fail_closed'))} "
        f"| checklist_required: {_yn(info.get('checklist_required'))} "
        f"| place_owning: {_yn(info.get('place_owning'))}"
    )
    lines.append(
        f"- shadow_mode: {_yn(info.get('shadow_mode'))} | side_first: {_yn(info.get('side_first'))} "
        f"| natural_market_elevation: {_yn(info.get('natural_market_elevation'))}"
    )
    lines.append(
        f"- anti_soft_underdog: {_yn(info.get('anti_soft_underdog'))} "
        f"| soft_ud_hard_band: {info.get('soft_ud_hard_band') or '1.70–2.20'} "
        f"| outer: {info.get('soft_ud_outer') or '2.60'}"
    )
    lines.append(f"- {info.get('test_cap_line') or 'test_cap: disabled'}")
    cards = info.get("cards_onboarded") or []
    if cards:
        lines.append(f"- cards_onboarded: {', '.join(str(c) for c in cards)}")
    else:
        lines.append("- cards_onboarded: _(none listed)_")
    notes = info.get("notes") or []
    if notes:
        lines.append(f"- notes: {'; '.join(str(n) for n in notes[:3])}")
    lines.append(
        "- law: preferred/mid band = research-rank only · empty slip beats weak soft dogs · "
        "promo/explore/EV-relax cannot bypass FEH F"
    )
    lines.append("")
    return "\n".join(lines)


def generate_status(
    cfg: dict[str, Any],
    bankroll: dict[str, Any],
    phase: dict[str, Any],
    risk: dict[str, Any],
) -> str:
    rows = load_bets(path_from_config(cfg, "bets"))
    bands = band_roi_stats(rows)
    band_lines = []
    for b in sorted(bands.keys()):
        s = bands[b]
        band_lines.append(
            f"| {b} | {int(s['n'])} | {s['roi']*100:.1f}% | {s['pl']:+.1f} |"
        )

    pending = [r for r in rows if is_open_risk(r.get("result"))]
    pend_lines = (
        "\n".join(
            f"- [{r.get('result')}] {r['date']}: {r['match']} / {r['selection']} @ {r['decimal_odds']} "
            f"stake {r['stake_nok']}"
            for r in pending[:20]
        )
        or "_None_"
    )

    thr = cfg["selection"]["high_odds_threshold"]

    # Coverage floor + temp_ev_relax (soft-fail compact section)
    try:
        cov_info = collect_coverage_floor_status(cfg)
        cov_section = format_coverage_floor_section(cov_info)
    except Exception:  # noqa: BLE001
        cov_section = "## Coverage floor\n\n_Coverage floor status unavailable (soft-fail)._\n\n"

    # FEH flags + test cap (soft-fail; template only — no secrets)
    try:
        feh_info = collect_feh_status(cfg)
        feh_section = format_feh_section(feh_info)
    except Exception:  # noqa: BLE001
        feh_section = (
            "## Forced Evidence Hierarchy\n\n"
            "_FEH status unavailable (soft-fail)._\n\n"
        )

    md = f"""# NT Status (auto-generated)

## Bankroll
- **Equity**: {bankroll['equity_nok']:.2f} NOK
- Realized P/L: {bankroll['realized_pl_nok']:+.2f} NOK (baseline {bankroll['baseline_nok']})
- Pending risk: {bankroll['pending_at_risk_nok']:.2f} NOK
- Liquid: {bankroll['liquid_nok']:.2f} NOK
- Ledger: {bankroll['total_bets']} bets ({bankroll['era_archive_bets']} archive + {bankroll['post_archive_bets']} later)

## Phase (auto)
- **{phase['phase_id']}** — {phase.get('label','')}
- Stake band: {phase['stake_min']:.0f}–{phase['stake_max']:.0f} NOK
- Max bets/round: {phase['max_bets_per_round']} | Max doubles: {phase['max_doubles_per_round']}
- Rolling ROI: {f"{phase['rolling_roi']*100:.1f}%" if phase.get('rolling_roi') is not None else "n/a"}

## Daily risk (auto — changes with equity/phase)
- Cap: **{risk['daily_risk_cap_nok']:.2f} NOK** (`{risk['formula']}`)
- Open pending: {risk['open_pending_risk_nok']:.2f}
- Remaining today: **{risk['remaining_risk_nok']:.2f} NOK**
- Today P/L: {risk['today_realized_pl_nok']:+.2f} | Stop if ≤ -{risk['stop_day_loss_limit_nok']:.2f}
- Can bet: **{risk['can_bet']}**

{feh_section}{cov_section}## High odds policy
- Odds **> {thr} are allowed** when evidence grade **A**, EV ≥ high-odds min after haircut, and stake uses high-odds multiplier.
- Historical bad band ROI raises the EV bar further — it does not hard-ban the band.

## ROI by odds band (this era ledger)
| Band | n | ROI | P/L |
|------|---|-----|-----|
{chr(10).join(band_lines) if band_lines else "| — | 0 | — | — |"}

## Open pending
{pend_lines}

## Your workflow
1. Research → `evidence/*.json` (side-first FEH packs; see `nt research scaffold`)
2. Put odds in `inbox/`
3. `python run_nt.py recommend --odds inbox/YOURFILE.txt`
4. Place bets from `outbox/PLACE_THESE.md` (empty slip OK; 10 NOK test cap when active)
5. Put results in `inbox/` → `python run_nt.py settle --results …`
6. Review: `python run_nt.py analyze` · `learn` · `edges`

Optional: `project` (bankroll sim) · `agent ask` (assist only)

Updated: {bankroll.get('updated_at','')}
"""
    return md


def write_status(cfg: dict[str, Any], bankroll: dict[str, Any], phase: dict[str, Any], risk: dict[str, Any]) -> None:
    path = path_from_config(cfg, "status")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_status(cfg, bankroll, phase, risk), encoding="utf-8")
