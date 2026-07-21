"""
Forensic process densification helpers.

Soft-match evidence packs → p_model for bets missing process meta.
Default is dry-run / audit only — never invents p_model; never touches bets.csv.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from nt.analytics import infer_market
from nt.bets_io import load_bets, utc_now
from nt.config import path_from_config
from nt.decisions import (
    DECISION_SCHEMA_VERSION,
    append_decision,
    append_evidence_link,
    decisions_path,
    evidence_links_path,
    load_decisions,
    load_evidence_links,
)
from nt.evidence import load_evidence
from nt.sport_taxonomy import normalize_sport


# Confidence thresholds (plan: only auto-accept ≥ 0.85)
CONF_EXACT = 0.95
CONF_NORMALIZED = 0.90
CONF_SLUG = 0.85
CONF_TOKEN = 0.60  # borderline — never auto-write without sport+market gates
DEFAULT_MIN_CONF = 0.85

# Soft-match v2: lower-confidence methods require sport + market-family agreement
SOFT_METHODS = frozenset({"slug", "token_subset", "token_subset_weak"})


def _norm(s: str) -> str:
    t = (s or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    # common NO/EN soft variants
    t = t.replace("nei", "no").replace("ja", "yes")
    t = re.sub(r"[^\w\s./:+-]", "", t)
    return t.strip()


def _tokens(s: str) -> set[str]:
    return {w for w in re.split(r"[\s_/|:,-]+", _norm(s)) if len(w) >= 3}


def _slug_key(match: str, selection: str) -> str:
    raw = f"{match}_{selection}"
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in raw)[:80].lower()


def _sport_key(s: str) -> str:
    """Canonical key so nba/basketball and Darts/darts soft-match agree."""
    if not (s or "").strip():
        return ""
    return normalize_sport(s, default="unknown")


def _market_family(selection: str, market_type: str = "") -> str:
    return infer_market(selection or "", market_type or "") or ""


def soft_context_ok(
    bet_sport: str,
    pack_sport: str,
    bet_sel: str,
    pack_sel: str,
    *,
    bet_market_type: str = "",
    pack_market_type: str = "",
) -> tuple[bool, str]:
    """
    Soft-match v2 gate for slug/token methods.
    Requires same sport (when both known) and same market family.
    """
    bs, ps = _sport_key(bet_sport), _sport_key(pack_sport)
    if bs and ps and bs != ps:
        return False, f"sport_mismatch:{bs}!={ps}"
    if not bs or not ps:
        # Missing sport on either side: refuse soft methods (exact still allowed separately)
        return False, "sport_unknown"

    bf = _market_family(bet_sel, bet_market_type)
    pf = _market_family(pack_sel, pack_market_type)
    if not bf or not pf:
        return False, "market_unknown"
    if bf != pf:
        return False, f"market_mismatch:{bf}!={pf}"
    return True, "ok"


@dataclass
class SoftMatch:
    bet_id: str
    match: str
    selection: str
    source: str
    pack_path: str
    pack_match: str
    pack_selection: str
    p_model: float
    confidence: float
    method: str
    would_write: bool
    skip_reason: str = ""
    existing_p_model: float | None = None
    bet_sport: str = ""
    pack_sport: str = ""
    market_family: str = ""
    gate: str = ""


def _load_packs(evidence_dir: Path) -> list[dict[str, Any]]:
    packs: list[dict[str, Any]] = []
    if not evidence_dir.is_dir():
        return packs
    for p in sorted(evidence_dir.glob("*.json")):
        if p.parent != evidence_dir:
            continue
        data = load_evidence(p)
        if not data:
            continue
        pm = data.get("p_model")
        try:
            p_model = float(pm) if pm is not None else None
        except (TypeError, ValueError):
            p_model = None
        if p_model is None or not (0.01 <= p_model <= 0.99):
            continue
        packs.append(
            {
                "path": p,
                "rel": str(p.as_posix()),
                "match": str(data.get("match") or "").strip(),
                "selection": str(data.get("selection") or "").strip(),
                "sport": str(data.get("sport") or "").strip(),
                "market_type": str(data.get("market_type") or data.get("market") or "").strip(),
                "p_model": p_model,
                "data": data,
            }
        )
    return packs


def score_match(
    bet_match: str,
    bet_sel: str,
    pack: dict[str, Any],
    *,
    bet_sport: str = "",
    bet_market_type: str = "",
    require_soft_gate: bool = True,
) -> tuple[float, str]:
    """
    Return (confidence, method). 0 = no match.

    Soft-match v2: slug/token only accepted when sport + market family agree
    (require_soft_gate=True, default). Exact/normalized identity is always OK.
    """
    pm, ps = pack["match"], pack["selection"]
    if not pm or not ps:
        return 0.0, "none"

    if bet_match == pm and bet_sel == ps:
        return CONF_EXACT, "exact"

    if _norm(bet_match) == _norm(pm) and _norm(bet_sel) == _norm(ps):
        return CONF_NORMALIZED, "normalized"

    conf = 0.0
    method = "none"

    slug_bet = _slug_key(bet_match, bet_sel)
    slug_pack = _slug_key(pm, ps)
    pack_stem = Path(pack["path"]).stem.lower()
    if slug_bet == slug_pack or slug_bet == pack_stem or pack_stem in slug_bet or slug_bet in pack_stem:
        # require both match and selection tokens overlap to avoid filename collisions
        mt = _tokens(bet_match) & _tokens(pm)
        st = _tokens(bet_sel) & _tokens(ps)
        if len(mt) >= 1 and len(st) >= 1:
            conf, method = CONF_SLUG, "slug"

    # Token subset: same match (strong) + selection token overlap
    if conf == 0.0:
        if _norm(bet_match) == _norm(pm) or (
            len(_tokens(bet_match) & _tokens(pm)) >= 2 and len(_tokens(bet_match)) <= 8
        ):
            st = _tokens(bet_sel) & _tokens(ps)
            if len(st) >= 2:
                conf, method = CONF_TOKEN, "token_subset"
            elif len(st) == 1 and any(x in _norm(bet_sel) for x in ("over", "under", "btts", "win")):
                conf, method = CONF_TOKEN, "token_subset_weak"

    if conf == 0.0:
        return 0.0, "none"

    if require_soft_gate and method in SOFT_METHODS:
        ok, reason = soft_context_ok(
            bet_sport,
            str(pack.get("sport") or ""),
            bet_sel,
            ps,
            bet_market_type=bet_market_type,
            pack_market_type=str(pack.get("market_type") or ""),
        )
        if not ok:
            return 0.0, f"rejected_{method}:{reason}"

    return conf, method


def audit_evidence_pmodel(
    cfg: dict[str, Any],
    *,
    min_confidence: float = DEFAULT_MIN_CONF,
    dry_run: bool = True,
    include_borderline: bool = True,
) -> dict[str, Any]:
    """
    Soft-match evidence packs to ledger rows missing p_model.

    dry_run=True (default): no side-car writes.
    Never overwrites existing high-confidence engine/evidence p_model.
    """
    rows = load_bets(path_from_config(cfg, "bets"))
    decisions = load_decisions(cfg)
    links = load_evidence_links(cfg)
    packs = _load_packs(path_from_config(cfg, "evidence"))

    candidates: list[SoftMatch] = []
    borderline: list[SoftMatch] = []
    skipped_has_p = 0
    skipped_no_match = 0
    skipped_soft_gate = 0
    skipped_archive_optional = 0

    # Index packs for exact lookup
    by_exact: dict[tuple[str, str], dict[str, Any]] = {}
    by_norm: dict[tuple[str, str], dict[str, Any]] = {}
    for pk in packs:
        by_exact[(pk["match"], pk["selection"])] = pk
        by_norm[(_norm(pk["match"]), _norm(pk["selection"]))] = pk

    for r in rows:
        bid = str(r.get("bet_id") or "")
        if not bid:
            continue
        prev = decisions.get(bid) or {}
        existing_p = prev.get("p_model")
        if existing_p is not None:
            # Do not overwrite any existing p_model (engine or prior backfill)
            skipped_has_p += 1
            continue

        # Prefer hard link path if already known
        best: SoftMatch | None = None
        link = links.get(bid)
        if link and link.get("evidence_path"):
            ep = Path(str(link["evidence_path"]))
            if not ep.is_file():
                # try relative to project
                ep2 = path_from_config(cfg, "evidence").parent.parent / str(link["evidence_path"])
                if ep2.is_file():
                    ep = ep2
            data = load_evidence(ep) if ep.is_file() else None
            if data and data.get("p_model") is not None:
                try:
                    pm = float(data["p_model"])
                except (TypeError, ValueError):
                    pm = None
                if pm is not None and 0.01 <= pm <= 0.99:
                    conf = float(link.get("confidence") or 0.95)
                    method = str(link.get("match_method") or "link_file")
                    best = SoftMatch(
                        bet_id=bid,
                        match=r.get("match") or "",
                        selection=r.get("selection") or "",
                        source=r.get("source") or "",
                        pack_path=str(ep.as_posix()),
                        pack_match=str(data.get("match") or ""),
                        pack_selection=str(data.get("selection") or ""),
                        p_model=pm,
                        confidence=conf,
                        method=method,
                        would_write=conf >= min_confidence,
                        existing_p_model=None,
                    )

        bm = (r.get("match") or "").strip()
        bs = (r.get("selection") or "").strip()
        b_sport = (r.get("sport") or "").strip()
        b_mtype = (r.get("market_type") or "").strip()

        if best is None:
            # Fast path exact / normalized; soft methods use v2 sport+market gate
            pk = by_exact.get((bm, bs)) or by_norm.get((_norm(bm), _norm(bs)))
            scored: list[tuple[float, str, dict[str, Any]]] = []
            rejected_soft = 0
            scan = [pk] if pk else packs
            for pack in scan:
                if pack is None:
                    continue
                conf, method = score_match(
                    bm,
                    bs,
                    pack,
                    bet_sport=b_sport,
                    bet_market_type=b_mtype,
                    require_soft_gate=True,
                )
                if conf > 0:
                    scored.append((conf, method, pack))
                elif method.startswith("rejected_"):
                    rejected_soft += 1
            if scored:
                scored.sort(key=lambda x: (-x[0], x[1]))
                conf, method, pk = scored[0]
                best = SoftMatch(
                    bet_id=bid,
                    match=bm,
                    selection=bs,
                    source=r.get("source") or "",
                    pack_path=pk["rel"],
                    pack_match=pk["match"],
                    pack_selection=pk["selection"],
                    p_model=float(pk["p_model"]),
                    confidence=conf,
                    method=method,
                    would_write=conf >= min_confidence,
                    existing_p_model=None,
                    bet_sport=b_sport,
                    pack_sport=str(pk.get("sport") or ""),
                    market_family=_market_family(bs, b_mtype),
                    gate="soft_v2" if method in SOFT_METHODS else "identity",
                )
            elif rejected_soft:
                skipped_soft_gate += 1
                continue  # counted under soft gate, not general no-match

        if best is None:
            skipped_no_match += 1
            continue

        if best.confidence >= min_confidence:
            candidates.append(best)
        elif include_borderline and best.confidence >= CONF_TOKEN:
            best.would_write = False
            best.skip_reason = f"below min_confidence {min_confidence}"
            borderline.append(best)
        else:
            skipped_no_match += 1

    # Coverage *before* any write (decisions was loaded at start)
    n_rows = len(rows)
    n_p_rows = sum(
        1
        for r in rows
        if (decisions.get(str(r.get("bet_id") or "")) or {}).get("p_model") is not None
    )

    written = 0
    if not dry_run:
        for m in candidates:
            if not m.would_write:
                continue
            prev = decisions.get(m.bet_id) or {}
            if prev.get("p_model") is not None:
                continue  # race-safe
            row = next((r for r in rows if str(r.get("bet_id")) == m.bet_id), {})
            rec = {
                "bet_id": m.bet_id,
                "date": row.get("date") or "",
                "match": m.match,
                "selection": m.selection,
                "sport": (row.get("sport") or "").strip(),
                "market_type": row.get("market_type") or "",
                "p_model": m.p_model,
                "p_model_source": "evidence_backfill",
                "evidence_path": m.pack_path,
                "evidence_match": "soft",
                "evidence_confidence": m.confidence,
                "market_key": infer_market(m.selection, row.get("market_type") or ""),
                "backfill": True,
                "backfill_note": f"soft evidence match method={m.method} conf={m.confidence}",
                "schema_version": DECISION_SCHEMA_VERSION,
                "source": m.source,
            }
            for k in (
                "ev",
                "explore",
                "learning_stake_mult",
                "learning_ev_boost",
                "grade",
                "odds_band",
                "phase",
            ):
                if prev.get(k) is not None and prev.get(k) != "":
                    rec[k] = prev[k]
            append_decision(cfg, rec)
            append_evidence_link(
                cfg,
                {
                    "bet_id": m.bet_id,
                    "evidence_path": m.pack_path,
                    "match_method": m.method,
                    "confidence": m.confidence,
                    "p_model_at_link": m.p_model,
                    "backfill": True,
                },
            )
            decisions[m.bet_id] = rec
            written += 1

    by_method: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for m in candidates:
        by_method[m.method] = by_method.get(m.method, 0) + 1
        by_source[m.source or "(empty)"] = by_source.get(m.source or "(empty)", 0) + 1

    def _sample(xs: list[SoftMatch], n: int = 8) -> list[dict[str, Any]]:
        return [asdict(x) for x in xs[:n]]

    risk_notes = [
        "Exact/normalized matches: low FP risk (string identity).",
        "Slug matches: low–medium; soft-match v2 requires same sport + market family.",
        f"Token subset (conf={CONF_TOKEN}): gated by sport+market family; still excluded below min_conf={min_confidence}.",
        "Multiple packs per match (different markets) require selection alignment.",
        "Does not invent p_model; only copies values from evidence packs.",
    ]

    n_after = n_p_rows + (written if not dry_run else len(candidates))
    report = {
        "dry_run": dry_run,
        "min_confidence": min_confidence,
        "thresholds": {
            "exact": CONF_EXACT,
            "normalized": CONF_NORMALIZED,
            "slug": CONF_SLUG,
            "token_subset": CONF_TOKEN,
            "auto_write_min": min_confidence,
        },
        "inputs": {
            "n_bets": n_rows,
            "n_decisions": len(decisions),
            "n_evidence_packs_with_p_model": len(packs),
            "n_evidence_links": len(links),
        },
        "results": {
            "would_add_p_model": len(candidates),
            "borderline_not_written": len(borderline),
            "skipped_already_has_p_model": skipped_has_p,
            "skipped_no_match": skipped_no_match,
            "skipped_soft_gate_v2": skipped_soft_gate,
            "written": written if not dry_run else 0,
        },
        "by_method": by_method,
        "by_source": by_source,
        "soft_match_v2": {
            "enabled": True,
            "gate": "slug/token require same sport + market family (infer_market)",
            "identity_methods": ["exact", "normalized", "link_file"],
            "soft_methods": sorted(SOFT_METHODS),
        },
        "false_positive_risk": {
            "level": (
                "low"
                if candidates
                and all(m.method in ("exact", "normalized", "link_file") for m in candidates)
                else ("none" if not candidates else "low-medium")
            ),
            "notes": risk_notes
            + [
                "Soft-match v2: token/slug without sport+market agreement are rejected (not written).",
            ],
        },
        "samples_would_write": _sample(candidates, 12),
        "samples_borderline": _sample(borderline, 10),
        "paths": {
            "decisions": str(decisions_path(cfg)),
            "evidence_links": str(evidence_links_path(cfg)),
            "evidence_dir": str(path_from_config(cfg, "evidence")),
        },
        "reversibility": {
            "flag": "backfill: true + p_model_source=evidence_backfill",
            "undo_hint": (
                "Filter bet_decisions.jsonl / evidence_links.jsonl for "
                "backfill=true and p_model_source=evidence_backfill"
            ),
        },
        "coverage": {
            "rows_with_p_model_now": n_p_rows,
            "rows_total": n_rows,
            "pct_now": round(100.0 * n_p_rows / n_rows, 1) if n_rows else 0.0,
            "rows_with_p_model_after_if_applied": n_after,
            "pct_after_if_applied": round(100.0 * n_after / n_rows, 1) if n_rows else 0.0,
        },
        "ts": utc_now(),
    }
    return report


def write_audit_markdown(report: dict[str, Any], path: Path) -> None:
    c = report["coverage"]
    r = report["results"]
    lines = [
        f"# Evidence → p_model soft-match audit",
        "",
        f"**Generated:** {report.get('ts')}",
        f"**Mode:** {'DRY-RUN (no writes)' if report.get('dry_run') else 'WRITE'}",
        f"**Min confidence for auto-write:** {report.get('min_confidence')}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Ledger rows | {c['rows_total']} |",
        f"| Rows with p_model now | {c['rows_with_p_model_now']} ({c['pct_now']}%) |",
        f"| Evidence packs with p_model | {report['inputs']['n_evidence_packs_with_p_model']} |",
        f"| Existing evidence_links | {report['inputs']['n_evidence_links']} |",
        f"| **Would add p_model** | **{r['would_add_p_model']}** |",
        f"| Projected coverage if applied | {c['rows_with_p_model_after_if_applied']} ({c['pct_after_if_applied']}%) |",
        f"| Borderline (not written) | {r['borderline_not_written']} |",
        f"| Skipped (already has p_model) | {r['skipped_already_has_p_model']} |",
        f"| Skipped (no match) | {r['skipped_no_match']} |",
        f"| Written this run | {r['written']} |",
        "",
        "## Match methods (would-write)",
        "",
        "```json",
        json.dumps(report.get("by_method") or {}, indent=2),
        "```",
        "",
        "## By ledger source",
        "",
        "```json",
        json.dumps(report.get("by_source") or {}, indent=2),
        "```",
        "",
        "## False-positive risk",
        "",
        f"**Level:** {report['false_positive_risk']['level']}",
        "",
    ]
    for n in report["false_positive_risk"]["notes"]:
        lines.append(f"- {n}")
    lines.extend(
        [
            "",
            "## Sample matches (would write)",
            "",
        ]
    )
    for s in report.get("samples_would_write") or []:
        lines.append(
            f"- **{s['bet_id']}** conf={s['confidence']} method=`{s['method']}`  \n"
            f"  bet: `{s['match']}` / `{s['selection']}`  \n"
            f"  pack: `{s['pack_match']}` / `{s['pack_selection']}` → p={s['p_model']}  \n"
            f"  file: `{s['pack_path']}`"
        )
    lines.extend(["", "## Sample borderline (NOT written)", ""])
    for s in report.get("samples_borderline") or []:
        lines.append(
            f"- **{s['bet_id']}** conf={s['confidence']} method=`{s['method']}`  \n"
            f"  bet: `{s['match']}` / `{s['selection']}`  \n"
            f"  pack: `{s['pack_match']}` / `{s['pack_selection']}` → p={s['p_model']}"
        )
    lines.extend(
        [
            "",
            "## Thresholds",
            "",
            "```json",
            json.dumps(report.get("thresholds") or {}, indent=2),
            "```",
            "",
            "## Reversibility",
            "",
            f"- {report['reversibility']['flag']}",
            f"- Undo: {report['reversibility']['undo_hint']}",
            "",
            "## Recommendation",
            "",
            "Review samples above. If exact/normalized dominate and slug samples look correct,",
            "re-run without `--dry-run` to append decision + evidence_link rows only.",
            "",
            "**Does not modify `data/bets.csv`.**",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
