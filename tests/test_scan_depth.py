"""Unit tests for scan-depth + Agent D spawn predicate (PR3)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.scan_merge import (
    DEFAULT_AGENT_D_MIN_LINES,
    agent_d_min_lines_from_cfg,
    match_line_counts,
    run_scan_depth,
    should_spawn_agent_d,
)


def _write_odds_csv(path: Path, rows: list[dict]) -> Path:
    lines = ["date,match,selection,decimal_odds,sport,market_type"]
    for r in rows:
        lines.append(
            ",".join(
                [
                    str(r.get("date") or "2026-07-25"),
                    str(r.get("match") or ""),
                    str(r.get("selection") or ""),
                    str(r.get("decimal_odds") or "1.80"),
                    str(r.get("sport") or "football"),
                    str(r.get("market_type") or ""),
                ]
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _rows_for_match(match: str, n: int, *, sport: str = "football") -> list[dict]:
    rows = []
    for i in range(n):
        rows.append(
            {
                "match": match,
                "selection": f"Sel {i}: Over {i}.5",
                "decimal_odds": 1.50 + (i % 40) * 0.01,
                "sport": sport,
            }
        )
    return rows


def test_default_min_lines_is_41() -> None:
    assert DEFAULT_AGENT_D_MIN_LINES == 41
    assert agent_d_min_lines_from_cfg(None) == 41
    assert agent_d_min_lines_from_cfg({"research": {}}) == 41
    assert (
        agent_d_min_lines_from_cfg(
            {"research": {"adaptive_scan_agent_d_min_lines": 41}}
        )
        == 41
    )


def test_should_spawn_agent_d_n40_false_n41_true() -> None:
    """Normative: n=40 → false, n=41 → true (never reuse high_volume n>=40)."""
    counts40 = {"per_match": {"Match A": 40, "Match B": 10}}
    counts41 = {"per_match": {"Match A": 41, "Match B": 10}}
    assert should_spawn_agent_d(counts40, min_lines=41) is False
    assert should_spawn_agent_d(counts41, min_lines=41) is True
    # Default min_lines is 41
    assert should_spawn_agent_d(counts40) is False
    assert should_spawn_agent_d(counts41) is True


def test_should_spawn_not_high_volume_bool() -> None:
    """Must use n >= cfg only; market-scan high_volume (n>=40) is NOT spawn_d."""
    # Exactly the high_volume threshold must still be false for default D min.
    assert should_spawn_agent_d({"per_match": {"X": 40}}) is False
    assert should_spawn_agent_d({"per_match": {"X": 40}}, min_lines=40) is True


def test_match_line_counts_per_match(tmp_path: Path) -> None:
    rows = _rows_for_match("Frankrike vs Spania", 41)
    rows += _rows_for_match("Thin vs Game", 5)
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    counts = match_line_counts(odds)
    assert counts["per_match"]["Frankrike vs Spania"] == 41
    assert counts["per_match"]["Thin vs Game"] == 5
    assert counts["max_lines_per_match"] == 41
    assert counts["total_lines"] == 46
    assert counts["match_n"] == 2
    assert should_spawn_agent_d(counts) is True


def test_match_line_counts_n40_no_spawn(tmp_path: Path) -> None:
    rows = _rows_for_match("Big vs Board", 40)
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    counts = match_line_counts(odds)
    assert counts["max_lines_per_match"] == 40
    assert should_spawn_agent_d(counts) is False
    depth = run_scan_depth(None, odds)
    assert depth["spawn_agent_d"] is False
    assert "skipped" in str(depth.get("agent_d") or "")
    assert depth["min_lines"] == 41


def test_run_scan_depth_spawn_true(tmp_path: Path) -> None:
    rows = _rows_for_match("Frankrike vs Spania", 41)
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    depth = run_scan_depth({"research": {"adaptive_scan_agent_d_min_lines": 41}}, odds)
    assert depth["spawn_agent_d"] is True
    assert "Frankrike vs Spania" in depth["matches_over_threshold"]
    assert "spawned" in str(depth.get("agent_d") or "")


def test_run_scan_depth_respects_cfg_min_lines(tmp_path: Path) -> None:
    rows = _rows_for_match("M", 25)
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    depth = run_scan_depth(
        {"research": {"adaptive_scan_agent_d_min_lines": 20}}, odds
    )
    assert depth["min_lines"] == 20
    assert depth["spawn_agent_d"] is True
    depth_hi = run_scan_depth(None, odds, min_lines=50)
    assert depth_hi["spawn_agent_d"] is False
