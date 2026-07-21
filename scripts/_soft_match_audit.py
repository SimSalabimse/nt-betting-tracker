"""One-shot soft-match exploration (dry-run only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.forensic import audit_evidence_pmodel, write_audit_markdown


def main() -> int:
    cfg = load_config()
    out = ROOT / "outbox"
    out.mkdir(exist_ok=True)

    r60 = audit_evidence_pmodel(cfg, min_confidence=0.60, dry_run=True)
    write_audit_markdown(r60, out / "AUDIT_evidence_pmodel_soft_token.md")
    (out / "AUDIT_evidence_pmodel_soft_token.json").write_text(
        json.dumps(r60, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print("=== min_confidence=0.60 + soft-match v2 DRY-RUN ===")
    print("would_add:", r60["results"]["would_add_p_model"])
    print("by_method:", r60.get("by_method"))
    print("skipped_soft_gate_v2:", r60["results"].get("skipped_soft_gate_v2"))
    print("risk:", r60["false_positive_risk"]["level"])
    print("v2:", r60.get("soft_match_v2"))
    print(
        "coverage now→after:",
        r60["coverage"]["pct_now"],
        "→",
        r60["coverage"]["pct_after_if_applied"],
    )
    for s in r60.get("samples_would_write") or []:
        print(
            f"  {s['bet_id']} conf={s['confidence']} method={s['method']}\n"
            f"    bet: {s['match'][:60]} / {s['selection'][:40]}\n"
            f"    pack: {s['pack_match'][:60]} / {s['pack_selection'][:40]} p={s['p_model']}"
        )

    r85 = audit_evidence_pmodel(cfg, min_confidence=0.85, dry_run=True)
    write_audit_markdown(r85, out / "AUDIT_evidence_pmodel.md")
    (out / "AUDIT_evidence_pmodel.json").write_text(
        json.dumps(r85, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print("=== restored default min=0.85 DRY-RUN ===")
    print(
        "would_add:",
        r85["results"]["would_add_p_model"],
        "borderline:",
        r85["results"]["borderline_not_written"],
    )
    for s in r85.get("samples_borderline") or []:
        print(
            f"  borderline {s['bet_id']} conf={s['confidence']} method={s['method']}\n"
            f"    bet: {s['match'][:60]} / {s['selection'][:40]}\n"
            f"    pack: {s['pack_match'][:60]} / {s['pack_selection'][:40]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
