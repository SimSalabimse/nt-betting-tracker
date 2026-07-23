#!/usr/bin/env python3
"""
Backfill predictability / variance_class / learning_weight for last N settled bets.

Best-effort from existing settlement_reviews + notes:
- late injury / red → one_off_*
- poor retro + process → research_process_miss + moderately/highly
- else unknown + weakly_predictable (weight ~0.18)

Rewrites settlement_reviews.jsonl (merge by bet_id, keep other rows).
Prints re-weight report: learning mults with vs without taxonomy weights.

Usage:
  python scripts/backfill_settlement_taxonomy.py
  python scripts/backfill_settlement_taxonomy.py --n 30 --report path.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.bets_io import is_performance_settled, load_bets, utc_now
from nt.config import load_config, path_from_config
from nt.learning import compute_learning, load_settlement_taxonomy_by_bet
from nt.settlement_review import settlement_reviews_path
from nt.settlement_taxonomy import (
    auto_classify_taxonomy,
    is_process_error_class,
    merge_taxonomy_into,
)


def _load_reviews(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _latest_review_by_bet(reviews: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by: dict[str, dict[str, Any]] = {}
    for r in reviews:
        bid = str(r.get("bet_id") or "").strip()
        if bid:
            by[bid] = r
    return by


def backfill(
    cfg: dict[str, Any],
    *,
    n: int = 30,
    dry_run: bool = False,
) -> dict[str, Any]:
    rows = load_bets(path_from_config(cfg, "bets"))
    settled = [r for r in rows if is_performance_settled(r.get("result"))]
    settled.sort(
        key=lambda r: (r.get("updated_at") or r.get("date") or r.get("created_at") or "")
    )
    target = settled[-n:] if n > 0 else settled
    target_ids = {str(r.get("bet_id") or "") for r in target if r.get("bet_id")}

    rev_path = settlement_reviews_path(cfg)
    all_reviews = _load_reviews(rev_path)
    latest = _latest_review_by_bet(all_reviews)

    classified: list[dict[str, Any]] = []
    class_counts: dict[str, int] = defaultdict(int)

    for bet in target:
        bid = str(bet.get("bet_id") or "")
        if not bid:
            continue
        prev = dict(latest.get(bid) or {})
        seed: dict[str, Any] = {
            "bet_id": bid,
            "notes": bet.get("notes") or prev.get("notes") or "",
            "key_events": prev.get("key_events"),
            "variance_tag": None,
            "research_quality_retro": prev.get("research_quality_retro"),
            "variance_class": prev.get("variance_class"),
            "predictability": prev.get("predictability"),
            "classification_notes": prev.get("classification_notes"),
        }
        # Recover feel: / research_retro: from notes
        notes = str(seed["notes"] or "")
        for part in notes.replace("|", ";").split(";"):
            p = part.strip()
            if p.startswith("feel:"):
                seed["variance_tag"] = p[5:].strip()
            if p.startswith("research_retro:"):
                seed["research_quality_retro"] = p[len("research_retro:") :].strip()
        if prev.get("legacy_label") and not seed.get("variance_class"):
            seed["variance_class"] = prev.get("legacy_label")
        if prev.get("variance_class") in (
            "skill",
            "variance",
            "process_error",
            "mixed",
            "neutral",
            "unknown",
            "model_error",
        ):
            # Force re-map legacy labels through auto_classify
            seed["variance_tag"] = seed.get("variance_tag") or prev.get("variance_class")
            seed["variance_class"] = None

        tax = auto_classify_taxonomy(seed, classified_by="backfill")
        class_counts[str(tax["variance_class"])] += 1

        # Build / update review row
        review = dict(prev) if prev else {
            "bet_id": bid,
            "match": bet.get("match"),
            "selection": bet.get("selection"),
            "result": bet.get("result"),
            "pl": float(bet.get("p_l_nok") or 0) if bet.get("p_l_nok") not in (None, "") else None,
            "odds": float(bet.get("decimal_odds") or 0) if bet.get("decimal_odds") else None,
            "factors": {
                "sport": (bet.get("sport") or "").lower() or "unknown",
                "grade": bet.get("research_grade") or "",
                "phase": bet.get("phase") or "",
            },
            "notes": bet.get("notes"),
        }
        review["ts"] = review.get("ts") or utc_now()
        review["backfilled_at"] = utc_now()
        if is_process_error_class(tax["variance_class"]):
            review["legacy_label"] = "process_error"
        elif tax["variance_class"] == "true_randomness":
            review["legacy_label"] = "variance"
        elif tax["variance_class"] == "systematic_script_form":
            review["legacy_label"] = "skill"
        else:
            review["legacy_label"] = review.get("legacy_label") or "unknown"
        merge_taxonomy_into(review, tax)
        review["variance_detail"] = tax.get("classification_notes")
        classified.append(review)
        latest[bid] = review

    # Rebuild reviews file: non-target rows keep last occurrence; targets replaced
    if not dry_run:
        kept: list[dict[str, Any]] = []
        seen_non_target: set[str] = set()
        # Preserve chronological order of original, swap target bet_ids with new tax
        for r in all_reviews:
            bid = str(r.get("bet_id") or "")
            if bid in target_ids:
                continue  # drop old; append updated later
            kept.append(r)
            if bid:
                seen_non_target.add(bid)
        # Append updated target reviews (stable order of target list)
        for rev in classified:
            kept.append(rev)
        rev_path.parent.mkdir(parents=True, exist_ok=True)
        with open(rev_path, "w", encoding="utf-8") as f:
            for r in kept:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Re-weight report: learning with taxonomy vs without
    rows_for_learn = load_bets(path_from_config(cfg, "bets"))

    # With weights (normal path — loads reviews)
    with_tax = compute_learning(rows_for_learn, cfg)

    # Without: temporarily point reviews path to empty
    import tempfile
    from copy import deepcopy

    cfg_no = deepcopy(cfg)
    paths = dict(cfg_no.get("paths") or {})
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td) / "settlement_reviews.jsonl"
        empty.write_text("", encoding="utf-8")
        paths["settlement_reviews_jsonl"] = str(empty)
        cfg_no["paths"] = paths
        without_tax = compute_learning(rows_for_learn, cfg_no)

    def _mult_map(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "stake_mult": float(v.get("stake_mult") or 1.0),
                "ev_boost": float(v.get("ev_boost") or 0.0),
                "roi_blended": float(v.get("roi_blended") or 0.0),
                "n": int(v.get("n") or 0),
                "status": v.get("status"),
            }
            for name, v in (payload.get(key) or {}).items()
        }

    deltas: list[dict[str, Any]] = []
    for kind in ("sports", "markets", "bands"):
        a = _mult_map(with_tax, kind)
        b = _mult_map(without_tax, kind)
        names = set(a) | set(b)
        for name in sorted(names):
            wa = a.get(name) or {"stake_mult": 1.0, "ev_boost": 0.0, "n": 0}
            wb = b.get(name) or {"stake_mult": 1.0, "ev_boost": 0.0, "n": 0}
            ds = round(float(wa["stake_mult"]) - float(wb["stake_mult"]), 4)
            de = round(float(wa["ev_boost"]) - float(wb["ev_boost"]), 5)
            if abs(ds) < 0.001 and abs(de) < 0.0005:
                continue
            deltas.append(
                {
                    "kind": kind.rstrip("s") if kind != "sports" else "sport",
                    "name": name,
                    "stake_with": wa["stake_mult"],
                    "stake_without": wb["stake_mult"],
                    "delta_stake": ds,
                    "ev_with": wa["ev_boost"],
                    "ev_without": wb["ev_boost"],
                    "delta_ev": de,
                    "n": wa.get("n") or wb.get("n"),
                }
            )
    deltas.sort(key=lambda x: abs(float(x["delta_stake"])), reverse=True)

    tax_loaded = load_settlement_taxonomy_by_bet(cfg)
    mean_lw = None
    weights = [
        float(v["learning_weight"])
        for v in tax_loaded.values()
        if v.get("learning_weight") is not None
    ]
    if weights:
        mean_lw = round(sum(weights) / len(weights), 4)

    return {
        "n_target": len(target),
        "n_classified": len(classified),
        "class_counts": dict(class_counts),
        "dry_run": dry_run,
        "reviews_path": str(rev_path),
        "mean_learning_weight": mean_lw,
        "n_taxonomy_total": len(tax_loaded),
        "mult_deltas": deltas,
        "classified": [
            {
                "bet_id": c.get("bet_id"),
                "match": (c.get("match") or "")[:48],
                "predictability": c.get("predictability"),
                "variance_class": c.get("variance_class"),
                "learning_weight": c.get("learning_weight"),
                "classification_notes": c.get("classification_notes"),
            }
            for c in classified
        ],
        "with_tax_summary": with_tax.get("summary"),
        "without_tax_summary": without_tax.get("summary"),
    }


def render_report(rep: dict[str, Any]) -> str:
    lines = [
        "# Settlement taxonomy re-weight report",
        "",
        f"Generated: **{utc_now()}**",
        "",
        f"- Target settled bets classified: **{rep.get('n_classified')}** / {rep.get('n_target')}",
        f"- Reviews path: `{rep.get('reviews_path')}`",
        f"- Dry-run: **{rep.get('dry_run')}**",
        f"- Taxonomy rows loaded: **{rep.get('n_taxonomy_total')}** · mean learning_weight **{rep.get('mean_learning_weight')}**",
        "",
        "## Class counts (this backfill batch)",
        "",
    ]
    for k, v in sorted((rep.get("class_counts") or {}).items(), key=lambda kv: -kv[1]):
        lines.append(f"- `{k}`: **{v}**")
    lines.extend(["", "## Per-bet taxonomy (batch)", ""])
    for c in rep.get("classified") or []:
        lines.append(
            f"- `{c.get('bet_id')}` {(c.get('match') or '')} · "
            f"**{c.get('variance_class')}** / {c.get('predictability')} · "
            f"w={c.get('learning_weight')} · {c.get('classification_notes')}"
        )
    lines.extend(
        [
            "",
            "## Multiplier deltas (with taxonomy weight − without)",
            "",
            "Positive delta_stake ⇒ taxonomy **raises** stake mult vs unweighted; "
            "negative ⇒ one-offs / low-weight losses were pulling mults down before.",
            "",
        ]
    )
    deltas = rep.get("mult_deltas") or []
    if not deltas:
        lines.append("_No material mult changes (thin sample or uniform weights)._")
    else:
        lines.append("| kind | name | stake w/ tax | stake w/o | Δ stake | Δ EV pp | n |")
        lines.append("|------|------|--------------|-----------|---------|---------|---|")
        for d in deltas[:40]:
            lines.append(
                f"| {d['kind']} | {d['name']} | {d['stake_with']:.3f} | {d['stake_without']:.3f} | "
                f"{d['delta_stake']:+.3f} | {float(d['delta_ev'])*100:+.2f} | {d.get('n')} |"
            )
    lines.extend(
        [
            "",
            "## What re-weighted learnings change",
            "",
            "- Sample influence in `compute_learning` is now `process_weight × learning_weight`.",
            "- `true_randomness` / one-offs (w≈0.05–0.10) barely move sport/market mults.",
            "- `research_process_miss` / `systematic_script_form` (w≈0.7–1.0) still drive the loop.",
            "- `temp_gate_raise` only emits when `learning_weight ≥ 0.5` (config).",
            "",
        ]
    )
    if deltas:
        top = deltas[0]
        lines.append(
            f"- Largest stake mult shift: **{top['kind']} `{top['name']}`** "
            f"{top['stake_without']:.3f} → {top['stake_with']:.3f} ({top['delta_stake']:+.3f})."
        )
    else:
        lines.append(
            "- No stake mult shifts above noise this run — taxonomy still stamped for future settles."
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=30, help="Last N settled bets (default 30)")
    ap.add_argument("--dry-run", action="store_true", help="Classify but do not write reviews")
    ap.add_argument(
        "--report",
        type=str,
        default="",
        help="Optional markdown report path",
    )
    args = ap.parse_args()
    cfg = load_config()
    rep = backfill(cfg, n=args.n, dry_run=args.dry_run)
    md = render_report(rep)
    print(md)
    if args.report:
        p = Path(args.report)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md, encoding="utf-8")
        print(f"\nWrote report: {p}", file=sys.stderr)
    # Compact JSON summary on stderr for agents
    summary = {
        "n_classified": rep["n_classified"],
        "class_counts": rep["class_counts"],
        "n_mult_deltas": len(rep.get("mult_deltas") or []),
        "mean_learning_weight": rep.get("mean_learning_weight"),
        "dry_run": rep.get("dry_run"),
    }
    print(json.dumps(summary, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
