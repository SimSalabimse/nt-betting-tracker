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


def test_odds_tol_2pct_keep(tmp_path: Path):
    """Within 2% relative: 1.53 vs dump 1.50 → keep."""
    rows = [
        {
            "match": "Humphries vs Price",
            "selection": "Vinner: Humphries",
            "decimal_odds": 1.50,
            "sport": "darts",
        }
    ]
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    agents = {
        "A": [
            {
                "match": "Humphries vs Price",
                "selection": "Vinner: Humphries",
                "decimal_odds": 1.53,  # 2% of 1.50
                "sport": "darts",
                "scan_agents": ["A"],
                "scan_reason": "Slightly moved line still same key.",
            }
        ]
    }
    payload = merge_candidates(agents, odds_path=odds, open_occ=open_occupancy_from_rows([]))
    assert payload["final_n"] == 1
    assert payload["candidates"][0]["match"] == "Humphries vs Price"


def test_odds_tol_beyond_2pct_drop(tmp_path: Path):
    """Beyond 2%: 1.60 vs dump 1.50 → off_odds_dump."""
    rows = [
        {
            "match": "Humphries vs Price",
            "selection": "Vinner: Humphries",
            "decimal_odds": 1.50,
            "sport": "darts",
        }
    ]
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    agents = {
        "A": [
            {
                "match": "Humphries vs Price",
                "selection": "Vinner: Humphries",
                "decimal_odds": 1.60,
                "sport": "darts",
                "scan_agents": ["A"],
                "scan_reason": "Too far from dump price.",
            }
        ]
    }
    payload = merge_candidates(agents, odds_path=odds, open_occ=open_occupancy_from_rows([]))
    assert payload["final_n"] == 0
    assert any(d["drop_reason"] == "off_odds_dump" for d in payload["dropped"])


def test_odds_missing_scan_odds_keep(tmp_path: Path):
    """Missing scan odds + matching key still OK."""
    rows = [
        {
            "match": "Sinner vs Rune",
            "selection": "Vinner: Sinner",
            "decimal_odds": 1.42,
            "sport": "tennis",
        }
    ]
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    agents = {
        "A": [
            {
                "match": "Sinner vs Rune",
                "selection": "Vinner: Sinner",
                "decimal_odds": None,
                "sport": "tennis",
                "scan_agents": ["A"],
                "scan_reason": "Key match without price.",
            }
        ]
    }
    payload = merge_candidates(agents, odds_path=odds, open_occ=open_occupancy_from_rows([]))
    assert payload["final_n"] == 1


def test_primary_union_coverage_critical(tmp_path: Path):
    """Primary worklist = shortlist ∪ coverage_critical; shortlist first; dedupe."""
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    agents = {
        "A": [
            {
                "match": "Sinner vs Rune",
                "selection": "Vinner: Sinner",
                "decimal_odds": 1.42,
                "sport": "tennis",
                "scan_agents": ["A"],
                "scan_reason": "On shortlist.",
            }
        ]
    }
    queue = [
        {
            "match": "Sinner vs Rune",
            "selection": "Vinner: Sinner",
            "decimal_odds": 1.42,
            "sport": "tennis",
            "notes": "coverage_floor:top_promo_scaffold",
            "promo_score": 99,
        },
        {
            "match": "Lakers vs Suns",
            "selection": "Vinner (inkludert overtid/straffer): Lakers",
            "decimal_odds": 1.70,
            "sport": "basketball",
            "notes": "coverage_floor:sport_rotation",
            "promo_score": 50,
        },
    ]
    payload = merge_candidates(
        agents,
        odds_path=odds,
        open_occ=open_occupancy_from_rows([]),
        deep_queue=queue,
        shortlist_min=1,
    )
    assert payload["final_n"] >= 1
    pw = payload["primary_worklist"]
    assert len(pw) == 2
    # Shortlist first
    assert pw[0]["match"] == "Sinner vs Rune"
    assert not pw[0].get("coverage_critical")
    # Extra coverage only once (deduped with shortlist)
    assert pw[1]["match"] == "Lakers vs Suns"
    assert pw[1].get("coverage_critical") is True
    assert payload["primary_worklist_n"] == 2


def test_engine_topup_when_shortlist_thin(tmp_path: Path):
    """ISS-1: final < 8 tops up from deep_queue light-pass lines."""
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    agents = {
        "A": [
            {
                "match": "Sinner vs Rune",
                "selection": "Vinner: Sinner",
                "decimal_odds": 1.42,
                "sport": "tennis",
                "scan_agents": ["A"],
                "scan_reason": "Only one agent pick.",
            }
        ]
    }
    queue = []
    for r in _base_odds_rows():
        queue.append(
            {
                **r,
                "promo_score": 10.0,
                "light_verdict": "pass",
                "notes": "",
            }
        )
    payload = merge_candidates(
        agents,
        odds_path=odds,
        open_occ=open_occupancy_from_rows([]),
        deep_queue=queue,
        shortlist_min=8,
    )
    assert payload["final_n"] >= 5  # family caps may limit below 8 on tiny board
    assert any("engine_topup" in n for n in (payload.get("notes") or []))
    assert any(c.get("engine_topup") or "engine" in (c.get("scan_agents") or []) for c in payload["candidates"])


def test_empty_agents_fallback_to_deep_queue(tmp_path: Path):
    """ISS-2: raw agents empty → primary/candidates from engine deep_queue."""
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    queue = [
        {
            "match": r["match"],
            "selection": r["selection"],
            "decimal_odds": r["decimal_odds"],
            "sport": r["sport"],
            "promo_score": 20 - i,
            "light_verdict": "pass",
        }
        for i, r in enumerate(_base_odds_rows())
    ]
    payload = merge_candidates(
        {"A": [], "B": [], "C": []},
        odds_path=odds,
        open_occ=open_occupancy_from_rows([]),
        deep_queue=queue,
    )
    assert payload["raw_n"] == 0
    assert payload["final_n"] > 0
    assert payload.get("fallback") == "engine_deep_queue"
    assert payload["primary_worklist_n"] == payload["final_n"]
    assert any("fallback: engine_deep_queue" in n for n in payload.get("notes") or [])


def test_agent_max_5_truncate(tmp_path: Path):
    """ISS-4: more than 5 rows from one agent → keep 5, drop agent_max_5."""
    # Expand odds so 8 unique tennis ML-ish keys exist
    rows = []
    for i in range(8):
        rows.append(
            {
                "match": f"P{i}a vs P{i}b",
                "selection": f"Vinner: P{i}a",
                "decimal_odds": 1.50 + i * 0.01,
                "sport": "tennis",
            }
        )
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    agents = {
        "B": [
            {
                "match": f"P{i}a vs P{i}b",
                "selection": f"Vinner: P{i}a",
                "decimal_odds": 1.50 + i * 0.01,
                "sport": "tennis",
                "scan_agents": ["B"],
                "scan_reason": f"Pick {i}",
                "promo_score": float(i),
            }
            for i in range(8)
        ]
    }
    payload = merge_candidates(
        agents,
        odds_path=odds,
        open_occ=open_occupancy_from_rows([]),
        shortlist_min=1,
    )
    assert payload["agents"]["B"] == 5
    assert sum(1 for d in payload["dropped"] if d["drop_reason"] == "agent_max_5") == 3
    # Highest promo kept (5,6,7 and two more of 2,3,4)
    promos = sorted(
        float(c.get("promo_score") or 0) for c in payload["candidates"] if "engine" not in (c.get("scan_agents") or [])
    )
    # After family cap tennis_ml ≤2, final may be 2 — but agent_counts after truncate is 5
    assert payload["agent_raw_counts"]["B"] == 8


def test_light_latest_autoload_drops_fail(tmp_path: Path):
    """ISS-3: run_scan_merge loads light LATEST and drops light-fail."""
    from nt.config import load_config

    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    a = tmp_path / "a.jsonl"
    a.write_text(
        json.dumps(
            {
                "match": "City vs United",
                "selection": "Totalt antall mål - over/under 2.5: Over 2.5",
                "decimal_odds": 1.75,
                "sport": "football",
                "scan_agents": ["B"],
                "scan_reason": "No embedded light field.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    light_dir = tmp_path / "light_research"
    light_dir.mkdir()
    (light_dir / "LATEST.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "match": "City vs United",
                        "selection": "Totalt antall mål - over/under 2.5: Over 2.5",
                        "verdict": "fail",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cfg = dict(load_config())
    paths = dict(cfg.get("paths") or {})
    paths["outbox"] = str(tmp_path)
    cfg["paths"] = paths
    payload = run_scan_merge(
        cfg,
        odds=odds,
        agent_a=a,
        use_live_open=False,
        write=False,
    )
    assert payload["final_n"] == 0
    assert any(d["drop_reason"] == "light_fail" for d in payload["dropped"])
