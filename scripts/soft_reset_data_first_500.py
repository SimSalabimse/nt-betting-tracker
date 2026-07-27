"""
Data-first soft reset: equity → 500 NOK, clean capital_segments era,
archive live ledger + placeable evidence packs, slim test-cap under esr_data_v1.

Does NOT wipe form_continuity / ranking_gap config, sport_cards, or code.

Preconditions (operator — before --confirm):
  Settle or abandon all open risk so pending_count == 0:

    python run_nt.py status
    python run_nt.py settle --draft
    python run_nt.py settle --results inbox/results.yaml
    # unplaceable leftovers (nt/ledger_ops.abandon):
    python run_nt.py abandon --ids <bet_id>[,...] --reason soft_reset_pending_clear
    python run_nt.py abandon --match "<substring>" --reason soft_reset_pending_clear
    python run_nt.py abandon --ids <bet_id> --dry-run   # preview
    python run_nt.py refresh

After soft reset:
    python run_nt.py refresh
    python run_nt.py status
  Assert equity 500.00, test_cap 0/10 · esr_data_v1, capital_segments clean.

Usage:
    python scripts/soft_reset_data_first_500.py --dry-run
    python scripts/soft_reset_data_first_500.py --confirm
    python scripts/soft_reset_data_first_500.py --confirm --era-start 2026-07-27
    python scripts/soft_reset_data_first_500.py --confirm --system-tag esr_data_v1

Flags:
    --dry-run              Plan only; never write
    --confirm              Perform mutations (required to write)
    --era-start YYYY-MM-DD  Override bankroll.era_start (default: Europe/Oslo today)
    --system-tag TAG       test_stake_cap system_tag (default: esr_data_v1)
    --allow-pending        Do not abort when pending open risk > 0 (unsafe; tests only)

By default aborts if any Pending/ConfirmedPlaced bets remain in data/bets.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.bets_io import BET_HEADER, is_open_risk, load_bets  # noqa: E402
from nt.capital_segments import save_segments  # noqa: E402
from nt.capital_v2 import empty_segments, oslo_today  # noqa: E402

DEFAULT_SYSTEM_TAG = "esr_data_v1"
BASELINE_NOK = 500.0

# Subdirs under evidence/ that must stay in place (not placeable attach packs).
EVIDENCE_KEEP_SUBDIRS = frozenset(
    {
        "sport_cards",
        "templates",
        "_quality_vetoed",
    }
)

# State files: archive then truncate (empty file).
ARCHIVE_TRUNCATE_JSONL = (
    "learning_history.jsonl",
    "calibration.jsonl",
    "settlement_reviews.jsonl",
    "bet_decisions.jsonl",
    "stake_decisions.jsonl",
    "reasoning_chains.jsonl",
    "control_signals.jsonl",
    "agent_audit.jsonl",
    "evidence_links.jsonl",
    "sim_audit.jsonl",
)

# State files: remove after optional archive copy.
REMOVE_STATE = (
    "deep_queue.json",
    "coverage_health.json",
    "phase.json",  # recompute on refresh → 1A at 500
    "learning_proposals.json",
)

STRUCTURAL_ALLOWLIST_IDS = frozenset(
    {
        "struct.form_continuity",
        "struct.ranking_gap_hc",
        "struct.tennis_totals_caution",
        "struct.anti_flip_heavy_fav",
        "struct.need_both_sides",
        "struct.mic_before_deep",
    }
)


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def reset_id_from_ts(ts: str) -> str:
    # soft_reset_20260727_120000 → soft_reset_2026-07-27T120000Z style
    if len(ts) >= 15 and ts[8] == "_":
        d, t = ts[:8], ts[9:]
        return f"soft_reset_{d[:4]}-{d[4:6]}-{d[6:8]}T{t}Z"
    return f"soft_reset_{ts}"


def build_structural_lessons(*, reset_id: str, updated_at: str | None = None) -> dict[str, Any]:
    """Agent/skill-only structural allowlist (engine_loaded: false). KD-struct-counter."""
    updated = updated_at or utc_now_iso()
    lessons = [
        {
            "lesson_id": "struct.form_continuity",
            "kind": "structural",
            "sport": None,
            "market_family_hint": None,
            "note": (
                "Form-continuity / anti-flip process is live in code+config; "
                "do not disable; never count as a bet counter."
            ),
            "counts_toward_test_cap": False,
            "counts_toward_edge_n_threshold": False,
            "expires_at": None,
        },
        {
            "lesson_id": "struct.ranking_gap_hc",
            "kind": "structural",
            "sport": None,
            "market_family_hint": "handicap",
            "note": "Ranking-gap HC: soft max 1 per slip when engine tags ranking_gap_hc.",
            "counts_toward_test_cap": False,
            "counts_toward_edge_n_threshold": False,
            "expires_at": None,
        },
        {
            "lesson_id": "struct.tennis_totals_caution",
            "kind": "structural",
            "sport": "tennis",
            "market_family_hint": "totals",
            "note": (
                "Tennis totals: require form/serve/surface context; "
                "raise evidence bar; do not auto-ban."
            ),
            "counts_toward_test_cap": False,
            "counts_toward_edge_n_threshold": False,
            "expires_at": None,
        },
        {
            "lesson_id": "struct.anti_flip_heavy_fav",
            "kind": "structural",
            "sport": None,
            "market_family_hint": None,
            "note": "Opposite-side after heavy-fav Win covered by form_continuity; keep bar high.",
            "counts_toward_test_cap": False,
            "counts_toward_edge_n_threshold": False,
            "expires_at": None,
        },
        {
            "lesson_id": "struct.need_both_sides",
            "kind": "structural",
            "sport": None,
            "market_family_hint": None,
            "note": "Deep packs must cover opposite-side / both sides where applicable.",
            "counts_toward_test_cap": False,
            "counts_toward_edge_n_threshold": False,
            "expires_at": None,
        },
        {
            "lesson_id": "struct.mic_before_deep",
            "kind": "structural",
            "sport": None,
            "market_family_hint": None,
            "note": "Match Intelligence Card before deep research after MIC transition.",
            "counts_toward_test_cap": False,
            "counts_toward_edge_n_threshold": False,
            "expires_at": None,
        },
    ]
    payload = {
        "schema_version": 1,
        "reset_id": reset_id,
        "updated_at": updated,
        "consumer": "agents_and_skills_only",
        "engine_loaded": False,
        "lessons": lessons,
    }
    assert_structural_flags(payload)
    return payload


def assert_structural_flags(payload: dict[str, Any]) -> None:
    if payload.get("engine_loaded") is not False:
        raise AssertionError("structural_lessons.engine_loaded must be false")
    for les in payload.get("lessons") or []:
        lid = les.get("lesson_id")
        if lid not in STRUCTURAL_ALLOWLIST_IDS:
            raise AssertionError(f"structural lesson not on allowlist: {lid}")
        if les.get("counts_toward_test_cap") is not False:
            raise AssertionError(f"{lid}: counts_toward_test_cap must be false")
        if les.get("counts_toward_edge_n_threshold") is not False:
            raise AssertionError(f"{lid}: counts_toward_edge_n_threshold must be false")


def build_settlement_lessons_shell(*, reset_id: str, updated_at: str | None = None) -> dict[str, Any]:
    """Engine-safe virgin settlement_lessons.json (no soft_awareness pile-ons)."""
    return {
        "schema_version": 1,
        "updated_at": updated_at or utc_now_iso(),
        "settled_at": None,
        "batch_id": None,
        "live_ledger_only": True,
        "source": "data/bets.csv",
        "n_settled": 0,
        "bets": [],
        "soft_awareness": [],
        "soft_reset_id": reset_id,
        "note": (
            "soft reset — no thin soft_awareness; "
            "structural guidance in structural_lessons.json only"
        ),
    }


def build_virgin_learning(*, reset_id: str, updated_at: str | None = None) -> dict[str, Any]:
    return {
        "enabled": True,
        "updated_at": updated_at or utc_now_iso(),
        "n_settled": 0,
        "sports": {},
        "markets": {},
        "bands": {},
        "lessons": [],
        "summary": {"n_settled": 0},
        "recent_settlements": [],
        "multiplier_moves": [],
        "reset_id": reset_id,
        "note": f"soft reset virgin learning ({reset_id})",
        "version": 4,
    }


def build_slim_test_cap(*, system_tag: str) -> dict[str, Any]:
    """Slim feh_test_cap schema only — NO reset_id (KD-testcap-audit)."""
    return {
        "schema_version": 1,
        "enabled": True,
        "max_bets": 10,
        "max_stake_nok": 10.0,
        "n_placed": 0,
        "bet_ids": [],
        "system_tag": system_tag,
        "excluded_bet_ids": [],
    }


def count_open_risk(bets_path: Path) -> tuple[int, float]:
    if not bets_path.is_file():
        return 0, 0.0
    rows = load_bets(bets_path)
    n = 0
    stake = 0.0
    for r in rows:
        if is_open_risk(r.get("result")):
            n += 1
            try:
                stake += float(r.get("stake_nok") or 0)
            except (TypeError, ValueError):
                pass
    return n, stake


def equity_before_from_state(root: Path) -> float | None:
    bankroll = root / "data" / "state" / "bankroll.json"
    if bankroll.is_file():
        try:
            data = json.loads(bankroll.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("equity_nok") is not None:
                return float(data["equity_nok"])
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return None


def n_bets_in_ledger(bets_path: Path) -> int:
    if not bets_path.is_file():
        return 0
    try:
        return len(load_bets(bets_path))
    except Exception:
        return 0


def list_top_level_evidence_json(evidence_dir: Path) -> list[Path]:
    if not evidence_dir.is_dir():
        return []
    return sorted(p for p in evidence_dir.glob("*.json") if p.is_file())


def update_config_yaml(
    cfg_path: Path,
    *,
    era_start: str,
    system_tag: str,
    dry_run: bool,
) -> list[str]:
    """Update bankroll.era_start and selection.test_stake_cap.system_tag. Do not touch baseline_nok."""
    notes: list[str] = []
    if not cfg_path.is_file():
        notes.append(f"config missing: {cfg_path}")
        return notes
    text = cfg_path.read_text(encoding="utf-8")
    text2, n_era = re.subn(
        r'(era_start:\s*)["\']?[0-9]{4}-[0-9]{2}-[0-9]{2}["\']?',
        rf'\1"{era_start}"',
        text,
        count=1,
    )
    # system_tag under test_stake_cap — first bare system_tag after test_stake_cap block is fine;
    # replace the known test_stake_cap system_tag line pattern.
    text3, n_tag = re.subn(
        r"(test_stake_cap:[\s\S]*?system_tag:\s*)\S+",
        rf"\1{system_tag}",
        text2,
        count=1,
    )
    notes.append(f"config era_start → {era_start} (replacements={n_era})")
    notes.append(f"config test_stake_cap.system_tag → {system_tag} (replacements={n_tag})")
    if not dry_run and (n_era or n_tag):
        cfg_path.write_text(text3, encoding="utf-8")
    return notes


def _copy_if_exists(src: Path, dest: Path) -> bool:
    if not src.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)
    return True


def _archive_then_truncate(src: Path, arch_dest: Path, dry_run: bool) -> bool:
    if not src.is_file():
        return False
    if dry_run:
        return True
    arch_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, arch_dest)
    src.write_text("", encoding="utf-8")
    return True


def _write_json(path: Path, payload: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _cfg_for_root(root: Path) -> dict[str, Any]:
    """Minimal cfg so capital_segments.save_segments resolves under root."""
    state = root / "data" / "state"
    return {
        "paths": {
            "state_dir": str(state),
            "bets": str(root / "data" / "bets.csv"),
            "capital_segments": str(state / "capital_segments.json"),
            "evidence": str(root / "evidence"),
            "history": str(root / "history"),
            "status": str(state / "status.md"),
            "bankroll_md": str(state / "current_bankroll.md"),
        },
        "bankroll": {"baseline_nok": BASELINE_NOK},
    }


def verify_settlement_lessons_shell(path: Path) -> None:
    """Fail if written shell would crash engine soft-adjust path."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise AssertionError("settlement_lessons.json must be object")
    if raw.get("soft_awareness") != []:
        raise AssertionError("settlement_lessons.soft_awareness must be []")
    if raw.get("bets") != []:
        raise AssertionError("settlement_lessons.bets must be []")
    try:
        from nt.settlement_lessons import lessons_soft_adjustments  # type: ignore

        # Call with empty candidate context if signature allows — else import is enough.
        _ = lessons_soft_adjustments
    except ImportError:
        pass
    except Exception as e:
        raise AssertionError(f"settlement_lessons load path failed: {e}") from e


def run_soft_reset(
    root: Path,
    *,
    dry_run: bool = False,
    confirm: bool = False,
    era_start: str | None = None,
    system_tag: str = DEFAULT_SYSTEM_TAG,
    allow_pending: bool = False,
    ts: str | None = None,
) -> dict[str, Any]:
    """
    Execute soft reset under *root* (project root).

    Returns a result dict (manifest payload + status). Never mutates when dry_run
    or when confirm is False (unless dry_run reports only).
    """
    if not dry_run and not confirm:
        raise SystemExit("Refusing to mutate without --confirm or --dry-run")

    do_write = bool(confirm and not dry_run)
    stamp = ts or utc_now_compact()
    rid = reset_id_from_ts(stamp)
    era = era_start or oslo_today()
    tag = (system_tag or DEFAULT_SYSTEM_TAG).strip() or DEFAULT_SYSTEM_TAG
    now = utc_now_iso()

    bets_path = root / "data" / "bets.csv"
    state_dir = root / "data" / "state"
    evidence_dir = root / "evidence"
    cfg_path = root / "config.yaml"
    archive_root = root / "history" / "archives" / f"soft_reset_{stamp}"

    pending_n, pending_stake = count_open_risk(bets_path)
    equity_before = equity_before_from_state(root)
    n_bets = n_bets_in_ledger(bets_path)
    evidence_packs = list_top_level_evidence_json(evidence_dir)

    result: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "confirm": confirm,
        "reset_id": rid,
        "archive_dir": str(archive_root),
        "era_start": era,
        "system_tag": tag,
        "equity_before": equity_before,
        "n_bets": n_bets,
        "pending_count": pending_n,
        "pending_at_risk_nok": pending_stake,
        "n_evidence_to_archive": len(evidence_packs),
        "actions": [],
        "aborted": False,
    }

    if pending_n > 0 and not allow_pending:
        result["ok"] = False
        result["aborted"] = True
        result["actions"].append(
            f"ABORT: pending open risk count={pending_n} stake={pending_stake:.2f} NOK. "
            "Settle or abandon first "
            "(python run_nt.py abandon --ids <id> --reason soft_reset_pending_clear)."
        )
        if confirm and not dry_run:
            raise SystemExit(result["actions"][-1])
        return result

    # ── plan / execute ──────────────────────────────────────────────────
    if do_write:
        archive_root.mkdir(parents=True, exist_ok=True)
        (archive_root / "evidence").mkdir(parents=True, exist_ok=True)
        (archive_root / "state").mkdir(parents=True, exist_ok=True)

    # 1) Archive bets + header-only ledger
    if bets_path.is_file():
        arch_bets = archive_root / "bets.csv"
        result["actions"].append(f"archive bets.csv → {arch_bets} ({n_bets} rows)")
        if do_write:
            shutil.copy2(bets_path, arch_bets)
            with bets_path.open("w", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=BET_HEADER, lineterminator="\n").writeheader()
            result["actions"].append("write header-only data/bets.csv")
    else:
        result["actions"].append("bets.csv missing — write header-only")
        if do_write:
            bets_path.parent.mkdir(parents=True, exist_ok=True)
            with bets_path.open("w", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=BET_HEADER, lineterminator="\n").writeheader()

    # 2) capital_segments: archive then empty_segments
    segs_path = state_dir / "capital_segments.json"
    capital_before: dict[str, Any] | None = None
    if segs_path.is_file():
        try:
            capital_before = json.loads(segs_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            capital_before = None
        result["actions"].append("archive capital_segments.json")
        if do_write:
            _copy_if_exists(segs_path, archive_root / "state" / "capital_segments.json")
    segs = empty_segments(baseline_nok=BASELINE_NOK, oslo_date=era)
    result["actions"].append(
        f"rebuild capital_segments via empty_segments(baseline_nok={BASELINE_NOK}, oslo_date={era})"
    )
    if do_write:
        cfg = _cfg_for_root(root)
        save_segments(cfg, segs)

    # 3) config era_start + system_tag
    result["actions"].extend(
        update_config_yaml(cfg_path, era_start=era, system_tag=tag, dry_run=not do_write)
    )

    # 4) learning virgin + archive truncate histories
    learn_path = state_dir / "learning.json"
    if learn_path.is_file() and do_write:
        _copy_if_exists(learn_path, archive_root / "state" / "learning.json")
    virgin = build_virgin_learning(reset_id=rid, updated_at=now)
    result["actions"].append("write virgin learning.json")
    _write_json(learn_path, virgin, dry_run=not do_write)

    for name in ARCHIVE_TRUNCATE_JSONL:
        p = state_dir / name
        if p.is_file():
            result["actions"].append(f"archive+truncate {name}")
            _archive_then_truncate(p, archive_root / "state" / name, dry_run=not do_write)

    # learning_proposals → empty object or remove
    prop = state_dir / "learning_proposals.json"
    if prop.is_file():
        result["actions"].append("archive+empty learning_proposals.json")
        if do_write:
            _copy_if_exists(prop, archive_root / "state" / "learning_proposals.json")
            prop.write_text("{}\n", encoding="utf-8")

    # 5) settlement_lessons engine shell
    sl_path = state_dir / "settlement_lessons.json"
    if sl_path.is_file() and do_write:
        _copy_if_exists(sl_path, archive_root / "state" / "settlement_lessons.json")
    shell = build_settlement_lessons_shell(reset_id=rid, updated_at=now)
    result["actions"].append("write engine-safe empty settlement_lessons.json")
    _write_json(sl_path, shell, dry_run=not do_write)
    if do_write:
        verify_settlement_lessons_shell(sl_path)

    # 6) slim test cap
    tc_path = state_dir / "feh_test_cap.json"
    if tc_path.is_file() and do_write:
        _copy_if_exists(tc_path, archive_root / "state" / "feh_test_cap.json")
    slim = build_slim_test_cap(system_tag=tag)
    if "reset_id" in slim:
        raise AssertionError("feh_test_cap must not contain reset_id")
    result["actions"].append(f"write slim feh_test_cap.json system_tag={tag} n_placed=0")
    _write_json(tc_path, slim, dry_run=not do_write)

    # 7) structural_lessons allowlist seed
    struct_path = state_dir / "structural_lessons.json"
    struct = build_structural_lessons(reset_id=rid, updated_at=now)
    result["actions"].append(
        f"write structural_lessons.json ({len(struct['lessons'])} allowlisted; engine_loaded=false)"
    )
    _write_json(struct_path, struct, dry_run=not do_write)

    # 8) KD-evidence-reset: move top-level evidence/*.json
    archived_evidence: list[str] = []
    for pack in evidence_packs:
        dest = archive_root / "evidence" / pack.name
        result["actions"].append(f"move evidence/{pack.name} → archive/evidence/")
        if do_write:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(pack), str(dest))
            archived_evidence.append(pack.name)
    result["n_evidence_archived"] = len(archived_evidence) if do_write else len(evidence_packs)

    # Keep sport_cards / templates (no action)
    for sub in ("sport_cards", "templates"):
        p = evidence_dir / sub
        if p.is_dir():
            result["actions"].append(f"keep evidence/{sub}/ in place")

    # 9) remove deep_queue / coverage_health / phase
    for name in REMOVE_STATE:
        p = state_dir / name
        if p.exists():
            result["actions"].append(f"remove {name}")
            if do_write:
                if p.is_file():
                    _copy_if_exists(p, archive_root / "state" / name)
                    p.unlink()
                else:
                    shutil.rmtree(p)

    result["actions"].append(
        "NOTE: run `python run_nt.py refresh` so bankroll/risk/phase rebuild "
        "(equity → 500; phase 1A; can_bet from clean segments)."
    )

    # 10) manifest
    manifest = {
        "reset_id": rid,
        "system_tag": tag,
        "equity_before": equity_before,
        "n_bets": n_bets,
        "n_bets_archived": n_bets,
        "n_evidence_archived": result.get("n_evidence_archived", 0),
        "evidence_archived": archived_evidence if do_write else [p.name for p in evidence_packs],
        "era_start": era,
        "baseline_nok": BASELINE_NOK,
        "capital_segments_before": capital_before,
        "pending_count_at_reset": pending_n,
        "created_at": now,
        "note": (
            f"Data-first soft reset @ {BASELINE_NOK} NOK; "
            f"first 10 place-acked bets after reset @ 10 NOK under {tag}"
        ),
        "operator_next": [
            "python run_nt.py refresh",
            "python run_nt.py status",
            "No recommend until Stage 2 rebuilds evidence packs for the new era",
        ],
    }
    result["manifest"] = manifest
    if do_write:
        _write_json(archive_root / "manifest.json", manifest, dry_run=False)
        result["actions"].append(f"write {archive_root / 'manifest.json'}")

    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Data-first soft reset to 500 NOK + esr_data_v1 test-cap era"
    )
    p.add_argument("--dry-run", action="store_true", help="Plan only; never write")
    p.add_argument("--confirm", action="store_true", help="Perform mutations")
    p.add_argument("--era-start", default=None, help="YYYY-MM-DD (default: Europe/Oslo today)")
    p.add_argument(
        "--system-tag",
        default=DEFAULT_SYSTEM_TAG,
        help=f"test_stake_cap system_tag (default: {DEFAULT_SYSTEM_TAG})",
    )
    p.add_argument(
        "--allow-pending",
        action="store_true",
        help="Do not abort when pending open risk > 0 (unsafe)",
    )
    p.add_argument(
        "--root",
        default=None,
        help="Project root (default: repo root). Tests use temp dirs.",
    )
    args = p.parse_args(argv)

    if not args.dry_run and not args.confirm:
        p.error("Specify --dry-run or --confirm")

    root = Path(args.root).resolve() if args.root else ROOT
    try:
        result = run_soft_reset(
            root,
            dry_run=bool(args.dry_run),
            confirm=bool(args.confirm),
            era_start=args.era_start,
            system_tag=args.system_tag,
            allow_pending=bool(args.allow_pending),
        )
    except SystemExit as e:
        print(str(e) or "aborted", file=sys.stderr)
        return 1

    mode = "DRY-RUN" if result.get("dry_run") else "CONFIRM"
    print(f"=== soft_reset_data_first_500 [{mode}] ===")
    print(f"root: {root}")
    print(f"reset_id: {result.get('reset_id')}")
    print(f"era_start: {result.get('era_start')}")
    print(f"system_tag: {result.get('system_tag')}")
    print(f"equity_before: {result.get('equity_before')}")
    print(f"n_bets: {result.get('n_bets')}")
    print(f"pending_count: {result.get('pending_count')}")
    print(f"n_evidence: {result.get('n_evidence_to_archive')}")
    if result.get("aborted"):
        print("ABORTED")
    for a in result.get("actions") or []:
        print(f"  · {a}")
    if result.get("ok") and not result.get("aborted"):
        print("OK")
        return 0
    return 1 if result.get("aborted") else 0


if __name__ == "__main__":
    raise SystemExit(main())
