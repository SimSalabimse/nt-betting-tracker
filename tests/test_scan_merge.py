"""Unit tests for multi-agent scan-merge helper (Stage 1b)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.market_family import market_family
from nt.odds_common import evidence_pair_key
from nt.scan_merge import (
    merge_candidates,
    open_occupancy_from_rows,
    parse_agent_file,
    run_scan_merge,
)


def _write_odds_csv(path: Path, rows: list[dict]) -> Path:
    """Minimal CSV odds dump accepted by parse_odds_file."""
    lines = ["date,match,selection,decimal_odds,sport,market_type"]
    for r in rows:
        lines.append(
            f"{r.get('date', '2026-07-25')},"
            f"{r['match']},"
            f"{r['selection']},"
            f"{r['decimal_odds']},"
            f"{r.get('sport', '')},"
            f"{r.get('market_type', '')}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _base_odds_rows() -> list[dict]:
    return [
        {
            "match": "Sinner vs Rune",
            "selection": "Vinner: Sinner",
            "decimal_odds": 1.42,
            "sport": "tennis",
        },
        {
            "match": "PlayerA vs PlayerB",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "decimal_odds": 1.88,
            "sport": "tennis",
        },
        {
            "match": "PlayerC vs PlayerD",
            "selection": "Totalt antall games 21.5: Over 21.5",
            "decimal_odds": 1.90,
            "sport": "tennis",
        },
        {
            "match": "PlayerE vs PlayerF",
            "selection": "Totalt antall games 23.5: Under 23.5",
            "decimal_odds": 1.85,
            "sport": "tennis",
        },
        {
            "match": "City vs United",
            "selection": "Totalt antall mål - over/under 2.5: Over 2.5",
            "decimal_odds": 1.75,
            "sport": "football",
        },
        {
            "match": "Humphries vs Price",
            "selection": "Vinner: Humphries",
            "decimal_odds": 1.55,
            "sport": "darts",
        },
        {
            "match": "Alcaraz vs Zverev",
            "selection": "Sett handikap: Zverev +3.5",
            "decimal_odds": 1.92,
            "sport": "tennis",
        },
        {
            "match": "Lakers vs Suns",
            "selection": "Vinner (inkludert overtid/straffer): Lakers",
            "decimal_odds": 1.70,
            "sport": "basketball",
        },
    ]


def test_dedupe_same_key(tmp_path: Path):
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    agents = {
        "A": [
            {
                "match": "Sinner vs Rune",
                "selection": "Vinner: Sinner",
                "decimal_odds": 1.42,
                "sport": "tennis",
                "scan_agents": ["A"],
                "scan_reason": "Ranking gulf hard court.",
            }
        ],
        "C": [
            {
                "match": "Sinner vs Rune",
                "selection": "Vinner: Sinner",
                "decimal_odds": 1.42,
                "sport": "tennis",
                "scan_agents": ["C"],
                "scan_reason": "Also form lean short.",
            }
        ],
    }
    payload = merge_candidates(agents, odds_path=odds, open_occ=open_occupancy_from_rows([]))
    keys = [
        evidence_pair_key(c["match"], c["selection"]) for c in payload["candidates"]
    ]
    assert keys.count(evidence_pair_key("Sinner vs Rune", "Vinner: Sinner")) == 1
    row = next(c for c in payload["candidates"] if "Sinner" in c["match"])
    assert set(row["scan_agents"]) == {"A", "C"}
    assert row["scan_agent"] == "A+C"


def test_family_triple_tennis_totals_keep_two(tmp_path: Path):
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    # Confirm families map to tennis_totals
    assert (
        market_family("tennis", "Totalt antall games 22.5: Over 22.5")
        == "tennis_totals"
    )
    agents = {
        "B": [
            {
                "match": "PlayerA vs PlayerB",
                "selection": "Totalt antall games 22.5: Over 22.5",
                "decimal_odds": 1.88,
                "sport": "tennis",
                "scan_agents": ["B"],
                "scan_reason": "Hold rates support O22.5.",
                "promo_score": 10,
            },
            {
                "match": "PlayerC vs PlayerD",
                "selection": "Totalt antall games 21.5: Over 21.5",
                "decimal_odds": 1.90,
                "sport": "tennis",
                "scan_agents": ["B"],
                "scan_reason": "Natural total board.",
                "promo_score": 8,
            },
            {
                "match": "PlayerE vs PlayerF",
                "selection": "Totalt antall games 23.5: Under 23.5",
                "decimal_odds": 1.85,
                "sport": "tennis",
                "scan_agents": ["B"],
                "scan_reason": "Third tennis total clone.",
                "promo_score": 3,
            },
        ]
    }
    payload = merge_candidates(agents, odds_path=odds, open_occ=open_occupancy_from_rows([]))
    fams = [c["market_family"] for c in payload["candidates"]]
    assert fams.count("tennis_totals") == 2
    drop_reasons = [d["drop_reason"] for d in payload["dropped"]]
    assert "family_cap" in drop_reasons


def test_off_odds_dump_dropped(tmp_path: Path):
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    agents = {
        "A": [
            {
                "match": "Ghost vs Phantom",
                "selection": "Vinner: Ghost",
                "decimal_odds": 1.50,
                "sport": "tennis",
                "scan_agents": ["A"],
                "scan_reason": "Invented line not on dump.",
            },
            {
                "match": "Sinner vs Rune",
                "selection": "Vinner: Sinner",
                "decimal_odds": 1.42,
                "sport": "tennis",
                "scan_agents": ["A"],
                "scan_reason": "Real favourite.",
            },
        ]
    }
    payload = merge_candidates(agents, odds_path=odds, open_occ=open_occupancy_from_rows([]))
    matches = [c["match"] for c in payload["candidates"]]
    assert "Ghost vs Phantom" not in matches
    assert any(d["drop_reason"] == "off_odds_dump" for d in payload["dropped"])
    assert any("Sinner" in m for m in matches)


def test_light_fail_dropped(tmp_path: Path):
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    agents = {
        "B": [
            {
                "match": "City vs United",
                "selection": "Totalt antall mål - over/under 2.5: Over 2.5",
                "decimal_odds": 1.75,
                "sport": "football",
                "scan_agents": ["B"],
                "scan_reason": "Open midfield xG.",
                "light_verdict": "fail",
            },
            {
                "match": "PlayerA vs PlayerB",
                "selection": "Totalt antall games 22.5: Over 22.5",
                "decimal_odds": 1.88,
                "sport": "tennis",
                "scan_agents": ["B"],
                "scan_reason": "force_scan: operator override despite light fail.",
                "light_verdict": "fail",
            },
        ]
    }
    payload = merge_candidates(agents, odds_path=odds, open_occ=open_occupancy_from_rows([]))
    kept_matches = [c["match"] for c in payload["candidates"]]
    assert "City vs United" not in kept_matches
    assert any(d["drop_reason"] == "light_fail" for d in payload["dropped"])
    # force_scan keeps light-fail
    assert "PlayerA vs PlayerB" in kept_matches


def test_empty_agent_file_tolerated(tmp_path: Path):
    empty = tmp_path / "scan_agent_a.jsonl"
    empty.write_text("", encoding="utf-8")
    missing = tmp_path / "does_not_exist.jsonl"
    assert parse_agent_file(empty, default_agent="A") == []
    assert parse_agent_file(missing, default_agent="A") == []
    assert parse_agent_file(None, default_agent="A") == []

    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    b = tmp_path / "scan_agent_b.jsonl"
    b.write_text(
        json.dumps(
            {
                "match": "City vs United",
                "selection": "Totalt antall mål - over/under 2.5: Over 2.5",
                "decimal_odds": 1.75,
                "sport": "football",
                "scan_agents": ["B"],
                "scan_reason": "Only B present.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    payload = run_scan_merge(
        None,
        odds=odds,
        agent_a=empty,
        agent_b=b,
        agent_c=missing,
        use_live_open=False,
        write=False,
    )
    assert payload["final_n"] >= 1
    assert payload["agents"]["A"] == 0


def test_open_family_full_deprioritize(tmp_path: Path):
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    # Two open tennis_totals already fill family cap (max 2)
    live_rows = [
        {
            "match": "Open1 vs Open2",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Pending",
            "source": "live",
        },
        {
            "match": "Open3 vs Open4",
            "selection": "Totalt antall games 21.5: Under 21.5",
            "sport": "tennis",
            "result": "ConfirmedPlaced",
            "source": "live",
        },
    ]
    occ = open_occupancy_from_rows(live_rows, max_per_family=2, max_per_sport=2)
    assert occ["family_counts"].get("tennis_totals", 0) >= 2

    agents = {
        "B": [
            {
                "match": "PlayerA vs PlayerB",
                "selection": "Totalt antall games 22.5: Over 22.5",
                "decimal_odds": 1.88,
                "sport": "tennis",
                "scan_agents": ["B"],
                "scan_reason": "Would be third open-family research seat.",
                "promo_score": 20,
            },
            {
                "match": "City vs United",
                "selection": "Totalt antall mål - over/under 2.5: Over 2.5",
                "decimal_odds": 1.75,
                "sport": "football",
                "scan_agents": ["B"],
                "scan_reason": "Football total alternative.",
                "promo_score": 5,
            },
            {
                "match": "Humphries vs Price",
                "selection": "Vinner: Humphries",
                "decimal_odds": 1.55,
                "sport": "darts",
                "scan_agents": ["A"],
                "scan_reason": "Darts favourite alternative.",
                "promo_score": 5,
            },
            {
                "match": "Lakers vs Suns",
                "selection": "Vinner (inkludert overtid/straffer): Lakers",
                "decimal_odds": 1.70,
                "sport": "basketball",
                "scan_agents": ["A"],
                "scan_reason": "Basketball fav alternative.",
                "promo_score": 5,
            },
            {
                "match": "Sinner vs Rune",
                "selection": "Vinner: Sinner",
                "decimal_odds": 1.42,
                "sport": "tennis",
                "scan_agents": ["A"],
                "scan_reason": "Tennis ML not open-family-full.",
                "promo_score": 5,
            },
            {
                "match": "Alcaraz vs Zverev",
                "selection": "Sett handikap: Zverev +3.5",
                "decimal_odds": 1.92,
                "sport": "tennis",
                "scan_agents": ["C"],
                "scan_reason": "HC alternative.",
                "promo_score": 5,
            },
            {
                "match": "PlayerC vs PlayerD",
                "selection": "Totalt antall games 21.5: Over 21.5",
                "decimal_odds": 1.90,
                "sport": "tennis",
                "scan_agents": ["B"],
                "scan_reason": "Another tennis total open-full.",
                "promo_score": 15,
            },
            {
                "match": "PlayerE vs PlayerF",
                "selection": "Totalt antall games 23.5: Under 23.5",
                "decimal_odds": 1.85,
                "sport": "tennis",
                "scan_agents": ["B"],
                "scan_reason": "Third tennis total for family/open pressure.",
                "promo_score": 12,
            },
        ]
    }
    # Pad shortlist_min so open_full can be dropped (need enough alternatives ≥ 8)
    # We only have 8 candidates in agents; after family cap on tennis_totals (≤2)
    # and open drops we should prefer non-full families.
    payload = merge_candidates(
        agents,
        odds_path=odds,
        open_occ=occ,
        shortlist_min=4,  # lower min so open_full can soft-drop
    )
    kept = payload["candidates"]
    # Open-full tennis_totals should be dropped when alternatives exist
    open_full_drops = [
        d for d in payload["dropped"] if d.get("drop_reason") == "open_family_full"
    ]
    assert open_full_drops, f"expected open_family_full drops, got {payload['dropped']}"
    # Football / darts / basketball still present
    sports = {c["sport"] for c in kept}
    assert "football" in sports or "darts" in sports or "basketball" in sports


def test_run_scan_merge_writes_artifacts(tmp_path: Path):
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    a = tmp_path / "scan_agent_a.jsonl"
    a.write_text(
        json.dumps(
            {
                "match": "Humphries vs Price",
                "selection": "Vinner: Humphries",
                "decimal_odds": 1.55,
                "sport": "darts",
                "scan_agents": ["A"],
                "scan_reason": "Ranking + form gap.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out_md = tmp_path / "MULTI_AGENT_SHORTLIST.md"
    payload = run_scan_merge(
        None,
        odds=odds,
        agent_a=a,
        use_live_open=False,
        out=out_md,
        write=True,
    )
    assert out_md.is_file()
    text = out_md.read_text(encoding="utf-8")
    assert "MULTI_AGENT_SHORTLIST" in text
    assert "Primary worklist" in text
    assert payload["final_n"] == 1
    assert Path(payload["json_path"]).is_file()
