"""
Tests for scripts/soft_reset_data_first_500.py

Uses temp project dirs only — never mutates live data/.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.bets_io import BET_HEADER, load_bets
from nt.bankroll import compute_bankroll
from nt.capital_v2 import empty_segments

# Import soft-reset helpers from scripts/
sys.path.insert(0, str(ROOT / "scripts"))
from soft_reset_data_first_500 import (  # noqa: E402
    DEFAULT_SYSTEM_TAG,
    build_slim_test_cap,
    build_structural_lessons,
    run_soft_reset,
)


def _header_only_bets(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=BET_HEADER, lineterminator="\n").writeheader()


def _write_bet_row(path: Path, *, result: str = "Loss", stake: str = "10", pl: str = "-10") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.is_file() and path.stat().st_size > 20
    with path.open("a" if exists else "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BET_HEADER, lineterminator="\n")
        if not exists:
            w.writeheader()
        row = {k: "" for k in BET_HEADER}
        row.update(
            {
                "bet_id": "deadbeef0001",
                "date": "2026-07-25",
                "match": "A vs B",
                "selection": "A",
                "decimal_odds": "1.90",
                "stake_nok": stake,
                "result": result,
                "p_l_nok": pl,
                "payout_nok": "0",
                "sport": "tennis",
                "source": "test",
            }
        )
        w.writerow(row)


def _seed_project(tmp: Path, *, with_pending: bool = False, n_settled: int = 2) -> Path:
    """Minimal project tree for soft-reset tests."""
    data = tmp / "data"
    state = data / "state"
    evidence = tmp / "evidence"
    state.mkdir(parents=True)
    evidence.mkdir(parents=True)
    (evidence / "sport_cards").mkdir()
    (evidence / "sport_cards" / "tennis.yaml").write_text("sport: tennis\n", encoding="utf-8")
    (evidence / "templates").mkdir()
    (evidence / "pack_pre_reset.json").write_text(
        json.dumps({"match": "A vs B", "p_model": 0.55, "summary": "old pack"}),
        encoding="utf-8",
    )
    (evidence / "another_pack.json").write_text(
        json.dumps({"match": "C vs D", "p_model": 0.60}),
        encoding="utf-8",
    )

    bets = data / "bets.csv"
    _header_only_bets(bets)
    for i in range(n_settled):
        with bets.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=BET_HEADER, lineterminator="\n")
            row = {k: "" for k in BET_HEADER}
            row.update(
                {
                    "bet_id": f"settled{i:04d}",
                    "date": "2026-07-25",
                    "match": f"M{i}",
                    "selection": "X",
                    "decimal_odds": "1.80",
                    "stake_nok": "10",
                    "result": "Loss",
                    "p_l_nok": "-10",
                    "payout_nok": "0",
                    "sport": "football",
                    "source": "test",
                }
            )
            w.writerow(row)
    if with_pending:
        with bets.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=BET_HEADER, lineterminator="\n")
            row = {k: "" for k in BET_HEADER}
            row.update(
                {
                    "bet_id": "pending0001",
                    "date": "2026-07-26",
                    "match": "Open vs Risk",
                    "selection": "Open",
                    "decimal_odds": "2.00",
                    "stake_nok": "11",
                    "result": "Pending",
                    "p_l_nok": "0",
                    "payout_nok": "0",
                    "sport": "tennis",
                    "source": "test",
                }
            )
            w.writerow(row)

    # Stale capital segments (poisoned day realized P/L)
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-26")
    segs["day_snapshot"]["liquid_start_nok"] = 478.9
    segs["day_snapshot"]["realized_pl_nok"] = -30.0
    segs["week_snapshot"]["realized_pl_nok"] = -30.0
    (state / "capital_segments.json").write_text(
        json.dumps(segs, indent=2) + "\n", encoding="utf-8"
    )

    (state / "bankroll.json").write_text(
        json.dumps(
            {
                "baseline_nok": 500.0,
                "realized_pl_nok": -20.0,
                "equity_nok": 480.0,
                "pending_count": 1 if with_pending else 0,
                "settled_count": n_settled,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (state / "learning.json").write_text(
        json.dumps({"n_settled": n_settled, "sports": {"football": {"roi": -0.5, "n": n_settled}}}),
        encoding="utf-8",
    )
    (state / "learning_history.jsonl").write_text('{"n":1}\n', encoding="utf-8")
    (state / "calibration.jsonl").write_text('{"x":1}\n', encoding="utf-8")
    (state / "settlement_reviews.jsonl").write_text('{"y":1}\n', encoding="utf-8")
    (state / "learning_proposals.json").write_text('{"proposal": true}\n', encoding="utf-8")
    (state / "settlement_lessons.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "n_settled": 1,
                "bets": [{"bet_id": "x"}],
                "soft_awareness": [{"family": "football_other", "note": "noise"}],
            }
        ),
        encoding="utf-8",
    )
    (state / "feh_test_cap.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "enabled": True,
                "max_bets": 10,
                "max_stake_nok": 10.0,
                "n_placed": 3,
                "bet_ids": ["a", "b", "c"],
                "system_tag": "esr_v1",
                "excluded_bet_ids": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (state / "deep_queue.json").write_text('{"q": []}\n', encoding="utf-8")
    (state / "coverage_health.json").write_text('{"ok": false}\n', encoding="utf-8")
    (state / "bet_decisions.jsonl").write_text("{}\n", encoding="utf-8")
    (state / "phase.json").write_text('{"phase_id": "1A"}\n', encoding="utf-8")

    (tmp / "config.yaml").write_text(
        f"""
bankroll:
  baseline_nok: 500.0
  era_start: "2026-07-22"
  include_era_archive: false

selection:
  test_stake_cap:
    enabled: true
    max_bets: 10
    max_stake_nok: 10.0
    system_tag: esr_v1
    state_path: data/state/feh_test_cap.json

paths:
  bets: data/bets.csv
  state_dir: data/state
  evidence: evidence
  history: history
  status: data/state/status.md
  bankroll_md: data/state/current_bankroll.md

# form_continuity / ranking_gap must stay enabled (script must not wipe)
form_continuity:
  enabled: true
ranking_gap_hc:
  enabled: true
""".lstrip(),
        encoding="utf-8",
    )
    return tmp


def test_dry_run_does_not_write(tmp_path: Path):
    root = _seed_project(tmp_path / "proj")
    bets_before = (root / "data" / "bets.csv").read_text(encoding="utf-8")
    packs_before = sorted(p.name for p in (root / "evidence").glob("*.json"))
    learn_before = (root / "data" / "state" / "learning.json").read_text(encoding="utf-8")
    cap_before = (root / "data" / "state" / "feh_test_cap.json").read_text(encoding="utf-8")
    segs_before = (root / "data" / "state" / "capital_segments.json").read_text(encoding="utf-8")

    result = run_soft_reset(root, dry_run=True, confirm=False, era_start="2026-07-27")

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["n_bets"] == 2
    assert result["n_evidence_to_archive"] == 2
    # No mutations
    assert (root / "data" / "bets.csv").read_text(encoding="utf-8") == bets_before
    assert sorted(p.name for p in (root / "evidence").glob("*.json")) == packs_before
    assert (root / "data" / "state" / "learning.json").read_text(encoding="utf-8") == learn_before
    assert (root / "data" / "state" / "feh_test_cap.json").read_text(encoding="utf-8") == cap_before
    assert (root / "data" / "state" / "capital_segments.json").read_text(encoding="utf-8") == segs_before
    # No archive dir created
    archives = list((root / "history" / "archives").glob("soft_reset_*")) if (root / "history").exists() else []
    assert archives == []


def test_confirm_archives_bets_empty_ledger_equity_path(tmp_path: Path):
    root = _seed_project(tmp_path / "proj")
    result = run_soft_reset(
        root,
        dry_run=False,
        confirm=True,
        era_start="2026-07-27",
        system_tag="esr_data_v1",
        ts="20260727_120000",
    )
    assert result["ok"] is True
    assert result["aborted"] is False

    arch = root / "history" / "archives" / "soft_reset_20260727_120000"
    assert arch.is_dir()
    assert (arch / "bets.csv").is_file()
    assert (arch / "manifest.json").is_file()
    man = json.loads((arch / "manifest.json").read_text(encoding="utf-8"))
    assert man["reset_id"] == "soft_reset_2026-07-27T120000Z"
    assert man["system_tag"] == "esr_data_v1"
    assert man["n_bets"] == 2
    assert man["equity_before"] == 480.0
    assert man["n_evidence_archived"] == 2

    # Live ledger header-only
    rows = load_bets(root / "data" / "bets.csv")
    assert rows == []
    text = (root / "data" / "bets.csv").read_text(encoding="utf-8")
    assert "bet_id" in text.splitlines()[0]

    # Equity path: baseline + sum(settled P/L) on empty ledger = 500
    cfg = {
        "bankroll": {"baseline_nok": 500.0, "era_start": "2026-07-27"},
        "paths": {
            "bets": str(root / "data" / "bets.csv"),
            "state_dir": str(root / "data" / "state"),
            "bankroll_md": str(root / "data" / "state" / "current_bankroll.md"),
        },
    }
    br = compute_bankroll(cfg, bets_path=root / "data" / "bets.csv")
    assert br["equity_nok"] == 500.0
    assert br["realized_pl_nok"] == 0.0
    assert br["pending_count"] == 0


def test_aborts_when_pending(tmp_path: Path):
    root = _seed_project(tmp_path / "proj", with_pending=True)
    packs_before = sorted(p.name for p in (root / "evidence").glob("*.json"))
    bets_before = (root / "data" / "bets.csv").read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as ei:
        run_soft_reset(root, dry_run=False, confirm=True, era_start="2026-07-27")
    assert "pending" in str(ei.value).lower() or "ABORT" in str(ei.value)

    # No mutation on abort
    assert (root / "data" / "bets.csv").read_text(encoding="utf-8") == bets_before
    assert sorted(p.name for p in (root / "evidence").glob("*.json")) == packs_before

    # dry-run reports abort without raising when only dry-run path... actually confirm+pending raises
    r = run_soft_reset(root, dry_run=True, confirm=False, era_start="2026-07-27")
    assert r["aborted"] is True
    assert r["pending_count"] == 1


def test_moves_top_level_evidence_packs(tmp_path: Path):
    root = _seed_project(tmp_path / "proj")
    run_soft_reset(
        root,
        confirm=True,
        dry_run=False,
        era_start="2026-07-27",
        ts="20260727_130000",
    )
    # Top-level empty of json packs
    remaining = list((root / "evidence").glob("*.json"))
    assert remaining == []
    # sport_cards kept
    assert (root / "evidence" / "sport_cards" / "tennis.yaml").is_file()
    assert (root / "evidence" / "templates").is_dir()
    # Archived under soft_reset_*/evidence/
    arch_ev = root / "history" / "archives" / "soft_reset_20260727_130000" / "evidence"
    names = sorted(p.name for p in arch_ev.glob("*.json"))
    assert "pack_pre_reset.json" in names
    assert "another_pack.json" in names


def test_writes_slim_test_cap_esr_data_v1(tmp_path: Path):
    root = _seed_project(tmp_path / "proj")
    run_soft_reset(root, confirm=True, dry_run=False, era_start="2026-07-27")
    cap = json.loads((root / "data" / "state" / "feh_test_cap.json").read_text(encoding="utf-8"))
    assert set(cap.keys()) == {
        "schema_version",
        "enabled",
        "max_bets",
        "max_stake_nok",
        "n_placed",
        "bet_ids",
        "system_tag",
        "excluded_bet_ids",
    }
    assert "reset_id" not in cap
    assert cap["system_tag"] == DEFAULT_SYSTEM_TAG
    assert cap["n_placed"] == 0
    assert cap["bet_ids"] == []
    assert cap["max_bets"] == 10
    assert float(cap["max_stake_nok"]) == 10.0

    # config system_tag updated
    cfg_text = (root / "config.yaml").read_text(encoding="utf-8")
    assert "system_tag: esr_data_v1" in cfg_text
    assert 'era_start: "2026-07-27"' in cfg_text
    # form_continuity not wiped
    assert "form_continuity:" in cfg_text
    assert "enabled: true" in cfg_text


def test_capital_segments_empty_segments_shape(tmp_path: Path):
    root = _seed_project(tmp_path / "proj")
    run_soft_reset(root, confirm=True, dry_run=False, era_start="2026-07-27")
    segs = json.loads((root / "data" / "state" / "capital_segments.json").read_text(encoding="utf-8"))
    expected = empty_segments(baseline_nok=500.0, oslo_date="2026-07-27")
    assert segs["schema_version"] == expected["schema_version"]
    assert segs["secure_nok"] == 0.0
    assert segs["freeze"]["active"] is False
    assert segs["day_snapshot"]["realized_pl_nok"] == 0.0
    assert segs["day_snapshot"]["liquid_start_nok"] is None
    assert segs["day_snapshot"]["oslo_date"] == "2026-07-27"
    assert segs["week_snapshot"]["realized_pl_nok"] == 0.0
    assert segs["week_snapshot"]["liquid_start_nok"] is None
    assert float(segs["unit_hwm_reset_equity_nok"]) == 500.0
    # Poisoned values gone
    assert segs["day_snapshot"]["realized_pl_nok"] != -30.0


def test_settlement_and_structural_lessons(tmp_path: Path):
    root = _seed_project(tmp_path / "proj")
    run_soft_reset(
        root,
        confirm=True,
        dry_run=False,
        era_start="2026-07-27",
        ts="20260727_140000",
    )
    sl = json.loads((root / "data" / "state" / "settlement_lessons.json").read_text(encoding="utf-8"))
    assert sl["soft_awareness"] == []
    assert sl["bets"] == []
    assert sl["n_settled"] == 0

    st = json.loads((root / "data" / "state" / "structural_lessons.json").read_text(encoding="utf-8"))
    assert st["engine_loaded"] is False
    assert st["consumer"] == "agents_and_skills_only"
    ids = {x["lesson_id"] for x in st["lessons"]}
    assert "struct.form_continuity" in ids
    assert "struct.ranking_gap_hc" in ids
    assert "struct.tennis_totals_caution" in ids
    for les in st["lessons"]:
        assert les["counts_toward_test_cap"] is False
        assert les["counts_toward_edge_n_threshold"] is False

    # learning virgin
    learn = json.loads((root / "data" / "state" / "learning.json").read_text(encoding="utf-8"))
    assert learn["n_settled"] == 0
    assert learn.get("sports") == {}

    # deep_queue / coverage removed
    assert not (root / "data" / "state" / "deep_queue.json").exists()
    assert not (root / "data" / "state" / "coverage_health.json").exists()

    # calibration truncated
    assert (root / "data" / "state" / "calibration.jsonl").read_text(encoding="utf-8") == ""


def test_build_slim_and_structural_helpers():
    slim = build_slim_test_cap(system_tag="esr_data_v1")
    assert "reset_id" not in slim
    assert slim["n_placed"] == 0
    struct = build_structural_lessons(reset_id="soft_reset_test")
    assert struct["engine_loaded"] is False
