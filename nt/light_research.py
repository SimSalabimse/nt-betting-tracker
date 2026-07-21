from __future__ import annotations

"""
Tiered research — Stage 1 (Light) vs Stage 2 (Deep).

Light: broad, structured, fast filter over most of the shortlist.
Deep: full evidence/*.json + p_model (only deep lines may be recommended).

Coverage targets (config research.tiers):
  light_coverage_target: 0.70–1.0 of shortlist
  min_light_per_sport_when_n: if sport has ≥N shortlist lines, light at least K
"""

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from nt.bets_io import odds_band, utc_now
from nt.config import path_from_config
from nt.defaults import research_cfg
from nt.odds_parse import Candidate, attach_evidence, parse_odds_file
from nt.research_gates.infer import selection_family


def tiers_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    rcfg = research_cfg(cfg)
    raw = dict(rcfg.get("tiers") or {})
    defaults = {
        "light_coverage_target": 0.85,  # fraction of shortlist
        "light_coverage_min_n": 8,  # always light at least this many if shortlist ≥ this
        "min_light_per_sport_when_n": 5,  # if sport has ≥5 shortlist lines…
        "min_light_per_sport": 3,  # …light at least 3
        "deep_target_n": 8,  # promote ~this many to deep when auto
        "deep_max_n": 12,  # cap auto deep promotions
        "auto_light_on_board": True,
        "auto_promote_to_deep": False,  # P1: never auto-promote; agent/manual only
        "fail_odds_below": 1.35,  # light-fail ultra-short unless exceptional
        "fail_odds_above": 4.0,  # light-fail longshots without deep plan
        "pass_odds_lo": 1.45,
        "pass_odds_hi": 2.50,
    }
    return {**defaults, **raw}


@dataclass
class LightRecord:
    match: str
    selection: str
    sport: str
    decimal_odds: float
    odds_band: str
    market_family: str
    tier: str = "light"  # light | deep | skipped
    verdict: str = "pass"  # pass | fail | skip
    promote_to_deep: bool = False
    script_lean: str = "unknown"
    script_conflict: bool = False
    base_rate_conflict: bool = False
    rough_p_needed: float | None = None
    rough_ev_note: str = ""
    strength_notes: str = ""
    weakness_notes: str = ""
    reason: str = ""
    has_deep_pack: bool = False
    has_p_model: bool = False
    researched_at: str = ""
    source: str = "auto"  # auto | agent | merge

    def key(self) -> tuple[str, str]:
        return (self.match or "", self.selection or "")


def _p_needed_for_min_ev(odds: float, min_ev: float = 0.03, haircut: float = 0.05) -> float:
    """p_model needed so (p - haircut)*odds - 1 >= min_ev."""
    if odds <= 1.0:
        return 0.99
    return min(0.99, max(0.01, (1.0 + min_ev) / odds + haircut))


def auto_light_assess(
    *,
    match: str,
    selection: str,
    sport: str,
    odds: float,
    cfg: dict[str, Any],
    has_deep: bool = False,
    has_p: bool = False,
    p_model: float | None = None,
    score: float = 0.0,
) -> LightRecord:
    """Heuristic light research (no web). Agent may overwrite with richer notes."""
    tcfg = tiers_cfg(cfg)
    sel_cfg = cfg.get("selection") or {}
    haircut = float(sel_cfg.get("probability_haircut", 0.05))
    min_ev = float(sel_cfg.get("standard_min_ev", 0.03))
    thr_high = float(sel_cfg.get("high_odds_threshold", 2.5))

    family = selection_family(selection, (sport or "").lower())
    band = odds_band(odds)
    need_p = _p_needed_for_min_ev(odds, min_ev, haircut)

    rec = LightRecord(
        match=match,
        selection=selection,
        sport=sport or "unknown",
        decimal_odds=float(odds),
        odds_band=band,
        market_family=family,
        rough_p_needed=round(need_p, 3),
        has_deep_pack=has_deep,
        has_p_model=has_p,
        researched_at=utc_now(),
        source="auto",
    )

    # Already deep
    if has_deep and has_p and p_model is not None:
        rec.tier = "deep"
        rec.verdict = "pass"
        rec.promote_to_deep = False
        rec.reason = "already has deep pack + p_model"
        rec.strength_notes = f"p_model={p_model}"
        rec.rough_ev_note = f"need p≥{need_p:.2f} for min EV; have {p_model}"
        return rec

    lo_fail = float(tcfg["fail_odds_below"])
    hi_fail = float(tcfg["fail_odds_above"])
    lo_pass = float(tcfg["pass_odds_lo"])
    hi_pass = float(tcfg["pass_odds_hi"])

    strengths: list[str] = []
    weaknesses: list[str] = []

    if lo_pass <= odds <= hi_pass:
        strengths.append(f"mid odds band {band} tradeable for Phase 1A")
    if score >= 90:
        strengths.append("high board research score")
    if family in ("totals_under", "totals_over", "btts_no", "btts_yes", "ml", "handicap"):
        strengths.append(f"core family {family}")

    if odds < lo_fail:
        weaknesses.append(f"odds {odds:.2f} too short — need p≥{need_p:.0%} after haircut")
        rec.verdict = "fail"
        rec.promote_to_deep = False
        rec.reason = "light-fail: odds too short for realistic EV"
    elif odds > hi_fail:
        weaknesses.append(f"odds {odds:.2f} longshot — needs grade A deep pack")
        rec.verdict = "fail"
        rec.promote_to_deep = False
        rec.reason = "light-fail: longshot without deep plan (auto)"
    elif need_p >= 0.78:
        weaknesses.append(f"EV bar needs p≥{need_p:.2f} — hard for honest model")
        rec.verdict = "fail"
        rec.promote_to_deep = False
        rec.reason = "light-fail: EV bar too high vs price"
    else:
        rec.verdict = "pass"
        # P1: auto light never auto-promotes to deep (agent/manual only)
        rec.promote_to_deep = False
        rec.reason = "light-pass: mid-band / tradeable — deep only via agent promote"
        if odds > thr_high:
            weaknesses.append("high odds — deep needs grade A + elevated EV")
        if family in ("totals_under", "btts_no"):
            rec.script_lean = "unknown"
            weaknesses.append("unders/BTTS No need script + availability in deep")
        if family in ("totals_over", "btts_yes"):
            weaknesses.append("overs/BTTS Yes need script lean not cagey")

    rec.strength_notes = "; ".join(strengths) or "none flagged"
    rec.weakness_notes = "; ".join(weaknesses) or "none flagged"
    rec.rough_ev_note = f"min EV bar needs honest p_model ≥ {need_p:.2f} at odds {odds:.2f}"
    rec.script_conflict = False
    rec.base_rate_conflict = False
    return rec


def light_path(cfg: dict[str, Any], day: str | None = None) -> Path:
    outbox = path_from_config(cfg, "outbox")
    d = day or date.today().isoformat()
    return outbox / "light_research" / f"{d}.json"


def load_light_batch(cfg: dict[str, Any], day: str | None = None) -> dict[str, Any]:
    path = light_path(cfg, day)
    if not path.exists():
        return {"records": [], "path": str(path), "day": day or date.today().isoformat()}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"records": data, "path": str(path), "day": day or date.today().isoformat()}
    return data


def save_light_batch(cfg: dict[str, Any], payload: dict[str, Any], day: str | None = None) -> Path:
    path = light_path(cfg, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # latest pointer
    latest = path.parent / "LATEST.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def coverage_stats(records: list[dict[str, Any]], shortlist_n: int) -> dict[str, Any]:
    n = len(records)
    by_verdict = Counter(r.get("verdict") for r in records)
    by_tier = Counter(r.get("tier") for r in records)
    by_sport = Counter((r.get("sport") or "unknown").lower() for r in records)
    light_n = sum(1 for r in records if r.get("tier") in ("light", "deep") or r.get("verdict") in ("pass", "fail"))
    # Any structured light assessment counts as "received light research"
    assessed = sum(1 for r in records if r.get("source") in ("auto", "agent", "merge") and r.get("verdict"))
    deep_n = sum(1 for r in records if r.get("tier") == "deep" or r.get("has_p_model"))
    promote = [r for r in records if r.get("promote_to_deep") and r.get("verdict") == "pass"]
    pct = (assessed / shortlist_n) if shortlist_n else 0.0
    return {
        "shortlist_n": shortlist_n,
        "assessed_n": assessed,
        "light_coverage_pct": round(100.0 * pct, 1),
        "deep_n": deep_n,
        "promote_to_deep_n": len(promote),
        "by_verdict": dict(by_verdict),
        "by_tier": dict(by_tier),
        "by_sport": dict(by_sport),
    }


def sport_min_coverage_ok(
    records: list[dict[str, Any]],
    shortlist_by_sport: dict[str, int],
    tcfg: dict[str, Any],
) -> list[str]:
    """Return human warnings if sport minimums not met."""
    warnings: list[str] = []
    thr_n = int(tcfg["min_light_per_sport_when_n"])
    min_k = int(tcfg["min_light_per_sport"])
    assessed_by_sp: dict[str, int] = defaultdict(int)
    for r in records:
        if r.get("verdict") in ("pass", "fail", "skip"):
            assessed_by_sp[(r.get("sport") or "unknown").lower()] += 1
    for sp, n in shortlist_by_sport.items():
        if n >= thr_n and assessed_by_sp.get(sp, 0) < min_k:
            warnings.append(
                f"sport {sp}: shortlist n={n} but light assessed only {assessed_by_sp.get(sp, 0)} "
                f"(need ≥{min_k})"
            )
    return warnings


def run_light_research(
    cfg: dict[str, Any],
    odds_path: Path,
    shortlist: list[Any],
    *,
    write: bool = True,
    day: str | None = None,
) -> dict[str, Any]:
    """
    Stage 1: light-assess shortlist items (auto heuristics).
    Enforces coverage targets by assessing enough lines.
    """
    tcfg = tiers_cfg(cfg)
    target = float(tcfg["light_coverage_target"])
    min_n = int(tcfg["light_coverage_min_n"])

    # Normalize shortlist to dicts
    items: list[dict[str, Any]] = []
    for it in shortlist:
        if hasattr(it, "match"):
            items.append(
                {
                    "match": it.match,
                    "selection": it.selection,
                    "sport": it.sport,
                    "decimal_odds": it.decimal_odds,
                    "score": getattr(it, "score", 0),
                    "has_evidence": getattr(it, "has_evidence", False),
                    "has_p_model": getattr(it, "has_p_model", False),
                    "p_model": getattr(it, "p_model", None),
                }
            )
        else:
            items.append(dict(it))

    shortlist_n = len(items)
    need = max(min_n, int(round(target * shortlist_n))) if shortlist_n else 0
    need = min(need, shortlist_n)

    # Sort: already deep first, then by score
    items_sorted = sorted(
        items,
        key=lambda x: (
            0 if x.get("has_p_model") else 1,
            -float(x.get("score") or 0),
            float(x.get("decimal_odds") or 99),
        ),
    )

    # Ensure sport minimums get assessed
    by_sport: dict[str, list[dict]] = defaultdict(list)
    for it in items_sorted:
        by_sport[(it.get("sport") or "unknown").lower()].append(it)

    must: list[dict] = []
    thr_n = int(tcfg["min_light_per_sport_when_n"])
    min_k = int(tcfg["min_light_per_sport"])
    seen: set[tuple[str, str]] = set()

    def _add(it: dict) -> None:
        k = (it.get("match") or "", it.get("selection") or "")
        if k in seen:
            return
        seen.add(k)
        must.append(it)

    for sp, lst in by_sport.items():
        if len(lst) >= thr_n:
            for it in lst[:min_k]:
                _add(it)

    for it in items_sorted:
        if len(must) >= need:
            break
        _add(it)

    # Fill to 100% of shortlist if target ≥ 0.99
    if target >= 0.99:
        for it in items_sorted:
            _add(it)

    records: list[LightRecord] = []
    for it in must:
        rec = auto_light_assess(
            match=str(it.get("match") or ""),
            selection=str(it.get("selection") or ""),
            sport=str(it.get("sport") or ""),
            odds=float(it.get("decimal_odds") or 1.5),
            cfg=cfg,
            has_deep=bool(it.get("has_evidence")),
            has_p=bool(it.get("has_p_model")),
            p_model=it.get("p_model"),
            score=float(it.get("score") or 0),
        )
        records.append(rec)

    # Cap promote_to_deep — only explicit agent/merge promotes (P1: no auto-promote)
    deep_max = int(tcfg["deep_max_n"])
    deep_target = int(tcfg["deep_target_n"])
    auto_promote = bool(tcfg.get("auto_promote_to_deep", False))
    promotable = [
        r
        for r in records
        if r.verdict == "pass"
        and r.promote_to_deep
        and not r.has_p_model
        and (auto_promote or r.source in ("agent", "merge"))
    ]
    # Fail/conflict demotion: never keep promote on fail
    for r in records:
        if r.verdict == "fail":
            r.promote_to_deep = False
    promotable.sort(key=lambda r: (-(1 if r.odds_band in ("1.5-1.8", "1.8-2.2") else 0), r.decimal_odds))
    # diversify sports in deep queue
    deep_queue: list[LightRecord] = []
    sp_count: dict[str, int] = defaultdict(int)
    for r in promotable:
        sp = (r.sport or "").lower()
        if sp_count[sp] >= 3 and len(deep_queue) < deep_target:
            continue
        if len(deep_queue) >= deep_max:
            r.promote_to_deep = False
            r.reason += " | deep queue full"
            continue
        deep_queue.append(r)
        sp_count[sp] += 1
    promote_keys = {r.key() for r in deep_queue}
    for r in records:
        if r.key() not in promote_keys and r.promote_to_deep and not r.has_p_model:
            r.promote_to_deep = False
            if "deep queue" not in r.reason:
                r.reason += " | not selected for deep this round"

    rec_dicts = [asdict(r) for r in records]
    shortlist_by_sport = {sp: len(lst) for sp, lst in by_sport.items()}
    stats = coverage_stats(rec_dicts, shortlist_n)
    warnings = sport_min_coverage_ok(rec_dicts, shortlist_by_sport, tcfg)
    target_pct = 100.0 * target
    if stats["light_coverage_pct"] + 0.1 < target_pct * (shortlist_n and 1 or 0) and shortlist_n:
        # compare to target fraction
        if stats["assessed_n"] < need:
            warnings.append(
                f"light coverage {stats['light_coverage_pct']}% < target {target_pct:.0f}% "
                f"({stats['assessed_n']}/{shortlist_n})"
            )

    payload = {
        "day": day or date.today().isoformat(),
        "odds_path": str(odds_path),
        "generated_at": utc_now(),
        "tiers_config": tcfg,
        "stats": stats,
        "warnings": warnings,
        "coverage_ok": stats["assessed_n"] >= need and not any("sport " in w for w in warnings),
        "deep_queue": [
            {
                "match": r.match,
                "selection": r.selection,
                "sport": r.sport,
                "decimal_odds": r.decimal_odds,
                "reason": r.reason,
            }
            for r in deep_queue
        ],
        "records": rec_dicts,
        "shortlist_n": shortlist_n,
        "assessed_n": len(records),
    }

    path = None
    if write:
        path = save_light_batch(cfg, payload, day=day)
        md_path = path.with_suffix(".md")
        md_path.write_text(render_light_markdown(payload), encoding="utf-8")
        (path.parent / "LATEST.md").write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
        payload["path"] = str(path)
        payload["md_path"] = str(md_path)

    return payload


def render_light_markdown(payload: dict[str, Any]) -> str:
    stats = payload.get("stats") or {}
    lines = [
        f"# Light Research Report — {payload.get('day')}",
        "",
        f"**Odds:** `{payload.get('odds_path')}`  ",
        f"**Generated:** {payload.get('generated_at')}  ",
        f"**Coverage OK:** {payload.get('coverage_ok')}",
        "",
        "## Coverage",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Shortlist | {stats.get('shortlist_n', 0)} |",
        f"| Light assessed | {stats.get('assessed_n', 0)} |",
        f"| Light coverage | **{stats.get('light_coverage_pct', 0)}%** |",
        f"| Already deep / p_model | {stats.get('deep_n', 0)} |",
        f"| Promote to deep | {stats.get('promote_to_deep_n', 0)} |",
        "",
        f"By verdict: `{stats.get('by_verdict')}`  ",
        f"By sport: `{stats.get('by_sport')}`",
        "",
    ]
    warns = payload.get("warnings") or []
    if warns:
        lines.append("## Warnings")
        lines.append("")
        for w in warns:
            lines.append(f"- ⚠ {w}")
        lines.append("")

    dq = payload.get("deep_queue") or []
    lines.append("## Deep research queue (Stage 2)")
    lines.append("")
    if not dq:
        lines.append("_Empty — no light-pass promotions._")
    else:
        lines.append("| # | Sport | Match | Selection | Odds |")
        lines.append("|---|-------|-------|-----------|-----:|")
        for i, r in enumerate(dq, 1):
            lines.append(
                f"| {i} | {r.get('sport')} | {r.get('match','')[:32]} | "
                f"{(r.get('selection') or '')[:40]} | {r.get('decimal_odds')} |"
            )
    lines.append("")
    lines.append("## All light assessments")
    lines.append("")
    lines.append("| Sport | Match | Selection | Odds | Verdict | Deep? | Reason |")
    lines.append("|-------|-------|-----------|-----:|---------|:-----:|--------|")
    for r in payload.get("records") or []:
        lines.append(
            f"| {r.get('sport','')} | {(r.get('match') or '')[:28]} | "
            f"{(r.get('selection') or '')[:36]} | {r.get('decimal_odds')} | "
            f"**{r.get('verdict')}** | {'Y' if r.get('promote_to_deep') else ''} | "
            f"{(r.get('reason') or '')[:50]} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("_Stage 1 Light Research. Only **deep** packs (evidence + p_model) can be recommended._")
    lines.append("")
    return "\n".join(lines)


def merge_deep_status(cfg: dict[str, Any], day: str | None = None) -> dict[str, Any]:
    """Refresh light batch flags from current evidence dir."""
    from nt.board import shortlist_board
    from nt.odds_parse import parse_odds_file, attach_evidence

    payload = load_light_batch(cfg, day)
    records = payload.get("records") or []
    if not records:
        return payload

    # Build deep index from evidence files
    ev_dir = path_from_config(cfg, "evidence")
    deep_keys: set[tuple[str, str]] = set()
    p_by_key: dict[tuple[str, str], float] = {}
    if ev_dir.exists():
        for p in ev_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            m = str(data.get("match") or "").strip()
            s = str(data.get("selection") or "").strip()
            if m and s and data.get("p_model") is not None:
                deep_keys.add((m, s))
                try:
                    p_by_key[(m, s)] = float(data["p_model"])
                except (TypeError, ValueError):
                    pass

    for r in records:
        k = (r.get("match") or "", r.get("selection") or "")
        if k in deep_keys:
            r["tier"] = "deep"
            r["has_deep_pack"] = True
            r["has_p_model"] = True
            r["promote_to_deep"] = False
            if k in p_by_key:
                r["strength_notes"] = (r.get("strength_notes") or "") + f" | deep p={p_by_key[k]}"
            r["reason"] = (r.get("reason") or "") + " | deep pack present"

    payload["records"] = records
    payload["stats"] = coverage_stats(records, int(payload.get("shortlist_n") or len(records)))
    payload["merged_at"] = utc_now()
    save_light_batch(cfg, payload, day=day)
    return payload
