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
    _normalize_agent_id,
    discover_agent_files,
    is_long_tail,
    is_main_board,
    merge_candidates,
    open_occupancy_from_rows,
    parse_agent_file,
    render_shortlist_markdown,
    run_scan_merge,
)


def _write_odds_csv(path: Path, rows: list[dict]) -> Path:
    """Minimal CSV odds dump accepted by parse_odds_file."""
    lines = ["date,match,selection,decimal_odds,sport,market_type"]
    for r in rows:
        lines.append(
            ",".join(
                [
                    str(r.get("date") or "2026-07-25"),
                    str(r.get("match") or ""),
                    str(r.get("selection") or ""),
                    str(r.get("decimal_odds") or ""),
                    str(r.get("sport") or ""),
                    str(r.get("market_type") or ""),
                ]
            )
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
            "decimal_odds": 1.9,
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
            "decimal_odds": 1.7,
            "sport": "basketball",
        },
    ]


def test_dedupe_same_key(tmp_path: Path) -> None:
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
    payload = merge_candidates(
        agents, odds, open_occ=open_occupancy_from_rows([])
    )
    keys = [
        evidence_pair_key(r["match"], r["selection"])
        for r in payload["candidates"]
    ]
    assert keys.count(evidence_pair_key("Sinner vs Rune", "Vinner: Sinner")) == 1
    row = next(
        r
        for r in payload["candidates"]
        if r["match"] == "Sinner vs Rune"
    )
    assert set(row["scan_agents"]) == {"A", "C"}
    assert row["scan_agent"] == "A+C"


def test_family_triple_tennis_totals_keep_two(tmp_path: Path) -> None:
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    assert (
        market_family(
            sport="tennis", selection="Totalt antall games 22.5: Over 22.5"
        )
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
                "decimal_odds": 1.9,
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
    payload = merge_candidates(
        agents, odds, open_occ=open_occupancy_from_rows([])
    )
    fams = [r["market_family"] for r in payload["candidates"]]
    assert fams.count("tennis_totals") == 2
    drop_reasons = [d.get("drop_reason") for d in payload["dropped"]]
    assert "family_cap" in drop_reasons


def test_off_odds_dump_dropped(tmp_path: Path) -> None:
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    agents = {
        "A": [
            {
                "match": "Ghost vs Phantom",
                "selection": "Vinner: Ghost",
                "decimal_odds": 1.5,
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
    payload = merge_candidates(
        agents, odds, open_occ=open_occupancy_from_rows([])
    )
    matches = [r["match"] for r in payload["candidates"]]
    assert "Ghost vs Phantom" not in matches
    assert "Sinner vs Rune" in matches
    assert any(d.get("drop_reason") == "off_odds_dump" for d in payload["dropped"])


def test_light_fail_dropped(tmp_path: Path) -> None:
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
    payload = merge_candidates(
        agents, odds, open_occ=open_occupancy_from_rows([])
    )
    kept_matches = [r["match"] for r in payload["candidates"]]
    assert "City vs United" not in kept_matches
    assert "PlayerA vs PlayerB" in kept_matches
    assert any(d.get("drop_reason") == "light_fail" for d in payload["dropped"])


def test_empty_agent_file_tolerated(tmp_path: Path) -> None:
    empty = tmp_path / "scan_agent_a.jsonl"
    empty.write_text("", encoding="utf-8")
    missing = tmp_path / "does_not_exist.jsonl"
    assert parse_agent_file(empty, default_agent="A") == []
    assert parse_agent_file(missing, default_agent="A") == []

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
        odds,
        agent_a=empty,
        agent_b=b,
        agent_c=missing,
        use_live_open=False,
        write=False,
    )
    assert payload["final_n"] == 1
    assert payload["agents"]["A"] == 0
    assert payload["agents"]["B"] == 1
    assert "A" in payload.get("scan_agent_missing") or any(
        "scan_agent_missing" in str(n) for n in payload.get("notes") or []
    )


def test_open_family_full_deprioritize(tmp_path: Path) -> None:
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
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
    occ = open_occupancy_from_rows(
        live_rows, max_per_family=2, max_per_sport=4
    )
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
                "match": "PlayerC vs PlayerD",
                "selection": "Totalt antall games 21.5: Over 21.5",
                "decimal_odds": 1.9,
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
        ],
        "A": [
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
                "decimal_odds": 1.7,
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
        ],
        "C": [
            {
                "match": "Alcaraz vs Zverev",
                "selection": "Sett handikap: Zverev +3.5",
                "decimal_odds": 1.92,
                "sport": "tennis",
                "scan_agents": ["C"],
                "scan_reason": "HC alternative.",
                "promo_score": 5,
            }
        ],
    }
    payload = merge_candidates(
        agents, odds, open_occ=occ, shortlist_min=4
    )
    kept = payload["candidates"]
    open_full_drops = [
        d for d in payload["dropped"] if d.get("drop_reason") == "open_family_full"
    ]
    sports = {r["sport"] for r in kept}
    # Prefer alternatives over stacking more tennis_totals when open seats full
    assert open_full_drops or all(
        r["market_family"] != "tennis_totals" for r in kept
    ) or len([r for r in kept if r["market_family"] == "tennis_totals"]) <= 1, (
        f"expected open_family_full drops, got kept={kept} drops={payload['dropped']}"
    )
    assert "football" in sports or "darts" in sports or "basketball" in sports


def test_run_scan_merge_writes_artifacts(tmp_path: Path) -> None:
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
        odds,
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
    assert payload.get("json_path")
    assert Path(payload["json_path"]).is_file()


def test_odds_tol_2pct_keep(tmp_path: Path) -> None:
    """Within 2% relative: 1.53 vs dump 1.50 → keep."""
    rows = [
        {
            "match": "Humphries vs Price",
            "selection": "Vinner: Humphries",
            "decimal_odds": 1.5,
            "sport": "darts",
        }
    ]
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    agents = {
        "A": [
            {
                "match": "Humphries vs Price",
                "selection": "Vinner: Humphries",
                "decimal_odds": 1.53,
                "sport": "darts",
                "scan_agents": ["A"],
                "scan_reason": "Slightly moved line still same key.",
            }
        ]
    }
    payload = merge_candidates(
        agents, odds, open_occ=open_occupancy_from_rows([])
    )
    assert payload["final_n"] == 1
    assert payload["candidates"][0]["match"] == "Humphries vs Price"


def test_odds_tol_beyond_2pct_drop(tmp_path: Path) -> None:
    """Beyond 2%: 1.60 vs dump 1.50 → off_odds_dump."""
    rows = [
        {
            "match": "Humphries vs Price",
            "selection": "Vinner: Humphries",
            "decimal_odds": 1.5,
            "sport": "darts",
        }
    ]
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    agents = {
        "A": [
            {
                "match": "Humphries vs Price",
                "selection": "Vinner: Humphries",
                "decimal_odds": 1.6,
                "sport": "darts",
                "scan_agents": ["A"],
                "scan_reason": "Too far from dump price.",
            }
        ]
    }
    payload = merge_candidates(
        agents, odds, open_occ=open_occupancy_from_rows([])
    )
    assert payload["final_n"] == 0
    assert any(d.get("drop_reason") == "off_odds_dump" for d in payload["dropped"])


def test_odds_missing_scan_odds_keep(tmp_path: Path) -> None:
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
    payload = merge_candidates(
        agents, odds, open_occ=open_occupancy_from_rows([])
    )
    assert payload["final_n"] == 1


def test_primary_union_coverage_critical(tmp_path: Path) -> None:
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
            "decimal_odds": 1.7,
            "sport": "basketball",
            "notes": "coverage_floor:sport_rotation",
            "promo_score": 50,
        },
    ]
    payload = merge_candidates(
        agents,
        odds,
        open_occ=open_occupancy_from_rows([]),
        deep_queue=queue,
        shortlist_min=1,
    )
    assert payload["final_n"] == 1
    pw = payload["primary_worklist"]
    assert len(pw) >= 2
    assert pw[0]["match"] == "Sinner vs Rune"
    assert any(r.get("coverage_critical") for r in pw)
    assert payload["primary_worklist_n"] == len(pw)


def test_engine_topup_when_shortlist_thin(tmp_path: Path) -> None:
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
        row = dict(r)
        row.update({"promo_score": 10.0, "light_verdict": "pass", "notes": ""})
        queue.append(row)
    payload = merge_candidates(
        agents,
        odds,
        open_occ=open_occupancy_from_rows([]),
        deep_queue=queue,
        shortlist_min=8,
    )
    assert payload["final_n"] >= 5
    assert any("engine_topup" in str(n) for n in payload.get("notes") or []) or any(
        "ENGINE" in (c.get("scan_agents") or []) for c in payload["candidates"]
    )


def test_empty_agents_fallback_to_deep_queue(tmp_path: Path) -> None:
    """ISS-2: raw agents empty → primary/candidates from engine deep_queue."""
    odds = _write_odds_csv(tmp_path / "odds.csv", _base_odds_rows())
    queue = []
    for i, r in enumerate(_base_odds_rows()):
        row = dict(r)
        row.update({"promo_score": 10.0 - i, "light_verdict": "pass", "notes": ""})
        queue.append(row)
    payload = merge_candidates(
        {"A": [], "B": [], "C": []},
        odds,
        open_occ=open_occupancy_from_rows([]),
        deep_queue=queue,
    )
    assert payload["raw_n"] == 0
    assert payload["final_n"] > 0
    assert payload.get("fallback") == "engine_deep_queue"
    assert payload["primary_worklist_n"] > 0
    assert any("fallback" in str(n) for n in payload.get("notes") or [])


def test_agent_max_5_truncate(tmp_path: Path) -> None:
    """ISS-4: more than 5 rows from one agent → keep 5, drop agent_max_5."""
    rows = []
    for i in range(8):
        rows.append(
            {
                "match": f"P{i}a vs P{i}b",
                "selection": f"Vinner: P{i}a",
                "decimal_odds": 1.5 + i * 0.01,
                "sport": "tennis",
            }
        )
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    agents = {
        "B": [
            {
                **r,
                "scan_agents": ["B"],
                "scan_reason": f"Pick {i}",
                "promo_score": float(10 - i),
            }
            for i, r in enumerate(rows)
        ]
    }
    payload = merge_candidates(
        agents,
        odds,
        open_occ=open_occupancy_from_rows([]),
        shortlist_min=1,
    )
    assert payload["agents"]["B"] == 8 or payload["agent_raw_counts"]["B"] == 8
    assert sum(1 for d in payload["dropped"] if d.get("drop_reason") == "agent_max_5") == 3
    # After family/sport filters may keep ≤5 from agent
    assert payload["final_n"] <= 5
    assert payload["agent_raw_counts"]["B"] == 8


def test_light_latest_autoload_drops_fail(tmp_path: Path) -> None:
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
    light_dir.mkdir(parents=True, exist_ok=True)
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
    try:
        cfg = dict(load_config())
    except Exception:
        cfg = {"paths": {}}
    paths = dict(cfg.get("paths") or {})
    paths["outbox"] = str(tmp_path)
    cfg["paths"] = paths
    payload = run_scan_merge(
        cfg,
        odds,
        agent_a=a,
        use_live_open=False,
        write=False,
    )
    assert payload["final_n"] == 0
    assert any(d.get("drop_reason") == "light_fail" for d in payload["dropped"])


def test_agent_a_odds_band(tmp_path: Path) -> None:
    """Agent A-only picks outside [1.40, 1.90] are dropped."""
    rows = [
        {
            "match": "Long vs Shot",
            "selection": "Vinner: Long",
            "decimal_odds": 2.40,
            "sport": "tennis",
        },
        {
            "match": "Sinner vs Rune",
            "selection": "Vinner: Sinner",
            "decimal_odds": 1.42,
            "sport": "tennis",
        },
    ]
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    agents = {
        "A": [
            {
                "match": "Long vs Shot",
                "selection": "Vinner: Long",
                "decimal_odds": 2.40,
                "sport": "tennis",
                "scan_agents": ["A"],
                "scan_reason": "Dog ML outside A band.",
            },
            {
                "match": "Sinner vs Rune",
                "selection": "Vinner: Sinner",
                "decimal_odds": 1.42,
                "sport": "tennis",
                "scan_agents": ["A"],
                "scan_reason": "In-band favourite.",
            },
        ]
    }
    payload = merge_candidates(
        agents, odds, open_occ=open_occupancy_from_rows([])
    )
    matches = [r["match"] for r in payload["candidates"]]
    assert "Long vs Shot" not in matches
    assert "Sinner vs Rune" in matches
    assert any(d.get("drop_reason") == "agent_a_odds_band" for d in payload["dropped"])


def test_normalize_agent_id_includes_d() -> None:
    assert _normalize_agent_id("D") == "D"
    assert _normalize_agent_id("agent_d") == "D"
    assert _normalize_agent_id("scan_agent: D") == "D"
    assert _normalize_agent_id("B+D") in ("B", "D")  # first token path
    assert _normalize_agent_id("A") == "A"
    assert _normalize_agent_id("ENGINE") == "ENGINE"


def test_discover_agent_files_includes_d(tmp_path: Path) -> None:
    (tmp_path / "scan_agent_a_2026-07-27.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "scan_agent_b_2026-07-27.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "scan_agent_c_2026-07-27.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "scan_agent_d_2026-07-27.jsonl").write_text("{}\n", encoding="utf-8")
    found = discover_agent_files(tmp_path)
    assert set(found) == {"A", "B", "C", "D"}
    assert found["D"].name.startswith("scan_agent_d")


def test_agent_d_merge_and_markdown_header(tmp_path: Path) -> None:
    rows = _base_odds_rows() + [
        {
            "match": "City vs United",
            "selection": "Kampens 1. målscorer: Haaland",
            "decimal_odds": 3.20,
            "sport": "football",
        }
    ]
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    agents = {
        "A": [
            {
                "match": "Sinner vs Rune",
                "selection": "Vinner: Sinner",
                "decimal_odds": 1.42,
                "sport": "tennis",
                "scan_agents": ["A"],
                "scan_reason": "Fav ML.",
            }
        ],
        "B": [
            {
                "match": "City vs United",
                "selection": "Totalt antall mål - over/under 2.5: Over 2.5",
                "decimal_odds": 1.75,
                "sport": "football",
                "scan_agents": ["B"],
                "scan_reason": "Main total.",
            }
        ],
        "C": [
            {
                "match": "Alcaraz vs Zverev",
                "selection": "Sett handikap: Zverev +3.5",
                "decimal_odds": 1.92,
                "sport": "tennis",
                "scan_agents": ["C"],
                "scan_reason": "Matchup dog HC.",
            }
        ],
        "D": [
            {
                "match": "City vs United",
                "selection": "Kampens 1. målscorer: Haaland",
                "decimal_odds": 3.20,
                "sport": "football",
                "scan_agents": ["D"],
                "scan_reason": "Long-tail goalscorer prop.",
            }
        ],
    }
    payload = merge_candidates(
        agents,
        odds,
        open_occ=open_occupancy_from_rows([]),
        shortlist_min=1,
        agent_d_armed=True,
    )
    assert payload["agent_raw_counts"]["D"] == 1
    assert payload.get("agent_d_armed") is True
    assert any(
        "D" in (r.get("scan_agents") or []) for r in payload["candidates"]
    )
    md = render_shortlist_markdown(payload)
    assert "agent_d:" in md
    assert "D(" in md or "spawned" in md


def test_d_role_drift_soft_annotate_no_hard_drop(tmp_path: Path) -> None:
    """≥3 of D's kept rows main_board → process_miss note; never hard-drop."""
    # Distinct families so family-cap does not drop below 3 kept main rows.
    rows = [
        {
            "match": "Sinner vs Rune",
            "selection": "Vinner: Sinner",
            "decimal_odds": 1.42,
            "sport": "tennis",
        },
        {
            "match": "City vs United",
            "selection": "Totalt antall mål - over/under 2.5: Over 2.5",
            "decimal_odds": 1.75,
            "sport": "football",
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
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    agents = {
        "D": [
            {
                **r,
                "scan_agents": ["D"],
                "scan_reason": f"Drift main board {i}",
                "promo_score": float(10 - i),
            }
            for i, r in enumerate(rows)
        ]
    }
    payload = merge_candidates(
        agents,
        odds,
        open_occ=open_occupancy_from_rows([]),
        shortlist_min=1,
        agent_d_armed=True,
    )
    # D main-board rows kept (soft only) — never hard-drop for role drift
    assert payload["final_n"] >= 3
    assert not any(
        d.get("drop_reason") == "agent_d_role_drift" for d in payload["dropped"]
    )
    assert any(
        "process_miss: agent_d_role_drift" in str(n) for n in payload.get("notes") or []
    )


def test_b_yields_longtail_to_d_when_armed(tmp_path: Path) -> None:
    """When D-armed, long-tail family collision prefers D over B."""
    rows = [
        {
            "match": "City vs United",
            "selection": "Kampens 1. målscorer: Haaland",
            "decimal_odds": 3.2,
            "sport": "football",
        },
        {
            "match": "City vs United",
            "selection": "Kampens 1. målscorer: Foden",
            "decimal_odds": 5.0,
            "sport": "football",
        },
        {
            "match": "City vs United",
            "selection": "Kampens 1. målscorer: Alvarez",
            "decimal_odds": 6.0,
            "sport": "football",
        },
        {
            "match": "City vs United",
            "selection": "Spiller X scorer",
            "decimal_odds": 4.0,
            "sport": "football",
        },
    ]
    odds = _write_odds_csv(tmp_path / "odds.csv", rows)
    # Same market_family (player_props): 3 seats → cap 2. Prefer D's over B's.
    agents = {
        "B": [
            {
                "match": "City vs United",
                "selection": "Kampens 1. målscorer: Alvarez",
                "decimal_odds": 6.0,
                "sport": "football",
                "scan_agents": ["B"],
                "scan_reason": "B long-tail seat.",
                "promo_score": 100,  # high promo must still yield to D when armed
            },
            {
                "match": "City vs United",
                "selection": "Spiller X scorer",
                "decimal_odds": 4.0,
                "sport": "football",
                "scan_agents": ["B"],
                "scan_reason": "B second prop.",
                "promo_score": 99,
            },
        ],
        "D": [
            {
                "match": "City vs United",
                "selection": "Kampens 1. målscorer: Haaland",
                "decimal_odds": 3.2,
                "sport": "football",
                "scan_agents": ["D"],
                "scan_reason": "D owns deep props.",
                "promo_score": 1,
            },
            {
                "match": "City vs United",
                "selection": "Kampens 1. målscorer: Foden",
                "decimal_odds": 5.0,
                "sport": "football",
                "scan_agents": ["D"],
                "scan_reason": "D second prop.",
                "promo_score": 1,
            },
        ],
    }
    payload = merge_candidates(
        agents,
        odds,
        open_occ=open_occupancy_from_rows([]),
        shortlist_min=1,
        agent_d_armed=True,
    )
    kept = payload["candidates"]
    fams = [r["market_family"] for r in kept]
    assert fams.count("player_props") == 2
    kept_agents = [set(r.get("scan_agents") or []) for r in kept]
    assert any("D" in a for a in kept_agents)
    # Both kept player_props should be D-preferred (not pure B)
    prop_rows = [r for r in kept if r.get("market_family") == "player_props"]
    assert all("D" in (r.get("scan_agents") or []) for r in prop_rows)
    assert any(
        "b_yielded_longtail_to_d" in str(n) for n in payload.get("notes") or []
    ) or any(
        "b_yielded_longtail_to_d" in str(d.get("notes") or "")
        for d in payload.get("dropped") or []
    )


def test_run_scan_merge_agent_d_path(tmp_path: Path) -> None:
    odds = _write_odds_csv(
        tmp_path / "odds.csv",
        _base_odds_rows()
        + [
            {
                "match": "City vs United",
                "selection": "Kampens 1. målscorer: Haaland",
                "decimal_odds": 3.2,
                "sport": "football",
            }
        ],
    )
    d = tmp_path / "scan_agent_d_2026-07-27.jsonl"
    d.write_text(
        json.dumps(
            {
                "match": "City vs United",
                "selection": "Kampens 1. målscorer: Haaland",
                "decimal_odds": 3.2,
                "sport": "football",
                "scan_agents": ["D"],
                "scan_reason": "Long-tail from D file.",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    payload = run_scan_merge(
        None,
        odds,
        agent_d=d,
        use_live_open=False,
        write=False,
    )
    assert payload["agents"]["D"] == 1
    assert payload.get("agent_d_armed") is True
    assert any("D" in (r.get("scan_agents") or []) for r in payload["candidates"])
    assert "agent_d:" in (payload.get("markdown") or "")


def test_is_long_tail_and_main_board_helpers() -> None:
    assert is_long_tail("Kampens 1. målscorer: Haaland", "", "player_props")
    assert is_main_board(
        "Totalt antall mål - over/under 2.5: Over 2.5", "", "football_totals"
    )
    assert is_main_board("HUB: Barcelona SC", "HUB", "football_1x2")
    assert is_main_board("Vinner: Sinner", "", "tennis_ml")
    assert not is_long_tail("Vinner: Sinner", "", "tennis_ml")
