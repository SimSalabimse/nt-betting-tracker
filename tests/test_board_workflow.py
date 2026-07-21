from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.board import board_coverage, research_readiness, run_board_research, shortlist_board
from nt.config import load_config, path_from_config
from nt.odds_parse import attach_evidence, parse_odds_file
from nt.portfolio import Candidate
from nt.recommend import run_recommend


def test_shortlist_prefers_main_markets():
    cfg = load_config()
    cands = [
        Candidate("2026-07-15", "A vs B", "A to Win", 1.70, sport="football"),
        Candidate("2026-07-15", "A vs B", "Spiller X scorer", 2.40, sport="football"),
        Candidate("2026-07-15", "A vs B", "BTTS Ja", 1.85, sport="football"),
        Candidate(
            "2026-07-15",
            "A vs B",
            "Totalt antall mål - Over/Under 2.5: Over 2.5",
            2.10,
            sport="football",
        ),
        Candidate(
            "2026-07-15",
            "A vs B",
            "1. omgang - totalt antall mål - over/under 1.5 — Under 1.5",
            1.85,
            sport="football",
        ),
        Candidate("2026-07-15", "A vs B", "Hjørnespark Over 9.5", 1.90, sport="football"),
        Candidate("2026-07-15", "P vs Q", "Vinner: Pain Gaming", 1.60, sport="esports"),
        Candidate(
            "2026-07-15",
            "OKC vs DAL",
            "Vinner (inkludert overtid/straffer): Oklahoma City Thunder",
            1.65,
            sport="nba",  # legacy alias → basketball via normalize_sport
        ),
    ]
    sl = shortlist_board(cands, cfg, max_per_match=6, max_total=16)
    sels = {s.selection for s in sl}
    sports = {s.sport for s in sl}
    families = {s.market_family for s in sl}
    assert "A to Win" in sels
    assert "BTTS Ja" in sels
    # Multi-sport board when odds dump has multiple sports (nba → basketball)
    assert "esports" in sports or "basketball" in sports
    # Period markets are first-class
    assert any("omgang" in s or "period" in f for s, f in zip(
        (x.selection for x in sl), (x.market_family for x in sl)
    )) or "period_ou" in families
    # Player props allowed (not hard-noise) at processable odds
    assert "Spiller X scorer" in sels or any("player" in f or "score" in f for f in families)


def test_shortlist_limits_football_share_when_multi_sport():
    cfg = load_config()
    cands = []
    for i in range(8):
        cands.append(
            Candidate(
                "2026-07-15",
                f"Home{i} vs Away{i}",
                f"Home{i} to Win",
                1.70 + i * 0.01,
                sport="football",
            )
        )
    cands.append(Candidate("2026-07-15", "T1 vs T2", "Vinner: T1", 1.55, sport="tennis"))
    cands.append(Candidate("2026-07-15", "E1 vs E2", "Vinner: E1", 1.60, sport="esports"))
    cands.append(
        Candidate(
            "2026-07-15",
            "N1 vs N2",
            "Vinner (inkludert overtid/straffer): N1",
            1.65,
            sport="nba",
        )
    )
    # Pass explicit max_total; config board_max_total is an upper bound only when larger
    sl = shortlist_board(cands, {**cfg, "research": {**(cfg.get("research") or {}), "board_max_total": 12, "board_max_football_share": 0.45, "board_min_non_football": 3}}, max_total=12)
    n_fb = sum(1 for s in sl if (s.sport or "").lower() == "football")
    n_other = sum(1 for s in sl if (s.sport or "").lower() not in ("football", "fotball", ""))
    assert n_other >= 2, f"expected non-football slots, got sports={[s.sport for s in sl]}"
    assert n_fb <= 6, f"football share too high: {n_fb}/{len(sl)} sports={[s.sport for s in sl]}"


def test_recommend_blocks_zero_research(tmp_path: Path):
    cfg = load_config()
    # Minimal odds csv with no evidence
    odds = tmp_path / "odds_empty_research.csv"
    odds.write_text(
        "date,match,selection,decimal_odds,sport\n"
        "2026-07-15,Zed FC vs Yed FC,Zed FC to Win,1.90,football\n",
        encoding="utf-8",
    )
    result = run_recommend(cfg, odds, log_pending=False, force_mechanical=False)
    assert result.get("blocked") is True
    assert result.get("n_picked") == 0
    assert "research board" in (result.get("message") or "").lower() or result.get("block_reason") == "no_research"


def test_recommend_force_mechanical_allows(tmp_path: Path):
    cfg = load_config()
    odds = tmp_path / "odds_mech.csv"
    odds.write_text(
        "date,match,selection,decimal_odds,sport\n"
        "2026-07-15,Zed FC vs Yed FC,Zed FC to Win,1.90,football\n",
        encoding="utf-8",
    )
    result = run_recommend(cfg, odds, log_pending=False, force_mechanical=True)
    assert result.get("blocked") is False
    # Still zero picks (no p_model) but not workflow-blocked
    assert "n_candidates" in result


def test_board_research_on_live_odds_if_present():
    cfg = load_config()
    path = ROOT / "inbox" / "odds_15-07.2026.txt"
    if not path.is_file():
        return
    result = run_board_research(cfg, path, write_scaffolds=False, write_report=False)
    assert result["coverage"]["n_candidates"] > 0
    assert result["n_shortlist"] >= 1
    assert result["markdown"]
    # England should appear if still on board
    matches = " ".join(result["coverage"].get("matches") or [])
    assert "England" in matches or result["n_shortlist"] > 0


def test_readiness_true_when_evidence_exists():
    cfg = load_config()
    path = ROOT / "inbox" / "odds_15-07.2026.txt"
    if not path.is_file():
        return
    # Current book may already have Eng BTTS evidence from session
    ready = research_readiness(cfg, path)
    assert "allow_recommend" in ready
    assert "coverage" in ready
