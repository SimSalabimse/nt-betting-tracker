#!/usr/bin/env python3
"""
Backfill predictability / variance_class / learning_weight for last N settled bets.

Best-effort from existing settlement_reviews + notes:
- late injury / red → one_off_*
- poor retro + process → research_process_miss + moderately/highly
- else unknown + weakly_predictable (weight ~0.18)

SAFE DEFAULT (CRITICAL):
  Writes **proposed** rows to ``data/state/settlement_reviews_backfill.jsonl`` only.
  Does **NOT** mutate live ``settlement_reviews.jsonl`` unless ``--apply`` is passed.

  Operator must review the proposed file / re-weight report, then re-run with
  ``--apply`` (or invoke ``/learning-rootcause --apply``) to merge into live reviews.

Usage:
  python scripts/backfill_settlement_taxonomy.py              # proposed path only
  python scripts/backfill_settlement_taxonomy.py --n 30
  python scripts/backfill_settlement_taxonomy.py --dry-run     # classify, no write
  python scripts/backfill_settlement_taxonomy.py --apply      # write live after review
  python scripts/backfill_settlement_taxonomy.py --report path.md
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


def proposed_backfill_path(cfg: dict[str, Any]) -> Path:
    """Proposed (non-live) backfill output — never the live reviews path."""
    paths = cfg.get("paths") or {}
    if paths.get("settlement_reviews_backfill_jsonl"):
        return path_from_config(cfg, "settlement_reviews_backfill_jsonl")
    try:
        state = path_from_config(cfg, "state_dir")
    except Exception:
        state = Path("data/state")
    return Path(state) / "settlement_reviews_backfill.jsonl"


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
    apply: bool = False,
) -> dict[str, Any]:
    """
    Classify last N settled bets.

    Write modes:
      - default: write proposed ``settlement_reviews_backfill.jsonl`` only
      - apply=True: merge into live ``settlement_reviews.jsonl``
      - dry_run=True: classify only, no write
    """
    rows = load_bets(path_from_config(cfg, "bets"))
    settled = [r for r in rows if is_performance_settled(r.get("result"))]
    settled.sort(
        key=lambda r: (r.get("updated_at") or r.get("date") or r.get("created_at") or "")
    )
    target = settled[-n:] if n > 0 else settled
    target_ids = {str(r.get("bet_id") or "") for r in target if r.get("bet_id")}

    rev_path = settlement_reviews_path(cfg)
    proposed_path = proposed_backfill_path(cfg)
    all_reviews = _load_reviews(rev_path)
    latest = _latest_review_by_bet(all_reviews)

    classified: list[dict[str, Any]] = []
    class_counts: dict[str, int] = defaultdict(int)
    before_sample: list[dict[str, Any]] = []

    for bet in target:
        bid = str(bet.get("bet_id") or "")
        if not bid:
            continue
        prev = dict(latest.get(bid) or {})
        before_sample.append(
            {
                "bet_id": bid,
                "predictability": prev.get("predictability"),
                "variance_class": prev.get("variance_class"),
                "learning_weight": prev.get("learning_weight"),
            }
        )
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

    write_mode = "none"
    written_path: Path | None = None

    if dry_run:
        write_mode = "dry_run"
    elif apply:
        # LIVE write — only with explicit --apply
        write_mode = "live"
        written_path = rev_path
        kept: list[dict[str, Any]] = []
        for r in all_reviews:
            bid = str(r.get("bet_id") or "")
            if bid in target_ids:
                continue  # drop old; append updated later
            kept.append(r)
        for rev in classified:
            kept.append(rev)
        rev_path.parent.mkdir(parents=True, exist_ok=True)
        with open(rev_path, "w", encoding="utf-8") as f:
            for r in kept:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        # Also refresh proposed mirror for audit
        proposed_path.parent.mkdir(parents=True, exist_ok=True)
        with open(proposed_path, "w", encoding="utf-8") as f:
            for rev in classified:
                f.write(json.dumps(rev, ensure_ascii=False) + "\n")
    else:
        # DEFAULT: proposed path only — never touch live reviews
        write_mode = "proposed"
        written_path = proposed_path
        proposed_path.parent.mkdir(parents=True, exist_ok=True)
        with open(proposed_path, "w", encoding="utf-8") as f:
            for rev in classified:
                f.write(json.dumps(rev, ensure_ascii=False) + "\n")

    # Re-weight report: learning with taxonomy vs without
    # When only proposed was written, compute "with" from proposed overlay
    rows_for_learn = load_bets(path_from_config(cfg, "bets"))

    from copy import deepcopy
    import tempfile

    if write_mode == "proposed" and classified:
        # Temporary live-like reviews for with_tax: merge proposed over live in temp
        cfg_with = deepcopy(cfg)
        with tempfile.TemporaryDirectory() as td:
            tmp_rev = Path(td) / "settlement_reviews.jsonl"
            merged = [r for r in all_reviews if str(r.get("bet_id") or "") not in target_ids]
            merged.extend(classified)
            with open(tmp_rev, "w", encoding="utf-8") as f:
                for r in merged:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            paths_w = dict(cfg_with.get("paths") or {})
            paths_w["settlement_reviews_jsonl"] = str(tmp_rev)
            cfg_with["paths"] = paths_w
            with_tax = compute_learning(rows_for_learn, cfg_with)
    else:
        with_tax = compute_learning(rows_for_learn, cfg)

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

    # Mean learning_weight of this batch (after)
    weights_after = [
        float(c["learning_weight"])
        for c in classified
        if c.get("learning_weight") is not None
    ]
    mean_lw = round(sum(weights_after) / len(weights_after), 4) if weights_after else None
    weights_before = [
        float(b["learning_weight"])
        for b in before_sample
        if b.get("learning_weight") is not None
    ]
    mean_lw_before = (
        round(sum(weights_before) / len(weights_before), 4) if weights_before else None
    )

    tax_loaded = load_settlement_taxonomy_by_bet(cfg) if write_mode == "live" else {}

    return {
        "n_target": len(target),
        "n_classified": len(classified),
        "class_counts": dict(class_counts),
        "dry_run": dry_run,
        "apply": apply,
        "write_mode": write_mode,
        "reviews_path": str(rev_path),
        "proposed_path": str(proposed_path),
        "written_path": str(written_path) if written_path else None,
        "mean_learning_weight": mean_lw,
        "mean_learning_weight_before": mean_lw_before,
        "n_taxonomy_total": len(tax_loaded) if write_mode == "live" else len(classified),
        "mult_deltas": deltas,
        "before": before_sample,
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
    mode = rep.get("write_mode") or ("dry_run" if rep.get("dry_run") else "proposed")
    lines = [
        "# Settlement taxonomy re-weight report",
        "",
        f"Generated: **{utc_now()}**",
        "",
        f"- Target settled bets classified: **{rep.get('n_classified')}** / {rep.get('n_target')}",
        f"- Write mode: **{mode}**",
        f"- Live reviews path: `{rep.get('reviews_path')}`",
        f"- Proposed path: `{rep.get('proposed_path')}`",
        f"- Written path: `{rep.get('written_path') or 'none'}`",
        f"- Dry-run: **{rep.get('dry_run')}** · Apply live: **{rep.get('apply')}**",
        f"- Mean learning_weight before → after: **{rep.get('mean_learning_weight_before')}** → **{rep.get('mean_learning_weight')}**",
        f"- Taxonomy rows (batch / live load): **{rep.get('n_taxonomy_total')}**",
        "",
    ]
    if mode == "proposed":
        lines.extend(
            [
                "> **SAFE DEFAULT:** only the proposed file was written.",
                "> Live `settlement_reviews.jsonl` was **not** mutated.",
                "> After review, re-run with `--apply` (or `/learning-rootcause --apply`).",
                "",
            ]
        )
    elif mode == "live":
        lines.extend(
            [
                "> **APPLIED:** live `settlement_reviews.jsonl` was rewritten for target bets.",
                "",
            ]
        )
    lines.extend(
        [
            "## Class counts (this backfill batch)",
            "",
        ]
    )
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
            "## Safe apply",
            "",
            "```bash",
            "# Review proposed first (default):",
            "python scripts/backfill_settlement_taxonomy.py --n 30",
            "# After review — mutate live reviews:",
            "python scripts/backfill_settlement_taxonomy.py --n 30 --apply",
            "```",
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
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify only — write nothing (no proposed, no live)",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="CRITICAL: merge into live settlement_reviews.jsonl (default writes proposed only)",
    )
    ap.add_argument(
        "--report",
        type=str,
        default="",
        help="Optional markdown report path",
    )
    args = ap.parse_args()
    if args.apply and args.dry_run:
        print("Cannot combine --apply and --dry-run", file=sys.stderr)
        return 2
    cfg = load_config()
    rep = backfill(cfg, n=args.n, dry_run=args.dry_run, apply=args.apply)
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
        "mean_learning_weight_before": rep.get("mean_learning_weight_before"),
        "dry_run": rep.get("dry_run"),
        "apply": rep.get("apply"),
        "write_mode": rep.get("write_mode"),
        "proposed_path": rep.get("proposed_path"),
        "written_path": rep.get("written_path"),
    }
    print(json.dumps(summary, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
