"""ESR deep_research pack → form_continuity mapping fixtures (PR4).

Golden strong-flip pack (gate-safe S1 + structural why_flip, no weak idioms)
maps to ≥2 strong flip signals. Weak-phrase pack fails S2 and soft-rejects
when used as an opposite-side flip after a successful heavy-fav HC.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.form_continuity import (
    _blob_has_weak_phrase,
    _count_strong_flip_signals,
    build_evidence_snapshot,
    form_continuity_penalty,
)
from nt.research import write_deep_research_pack

FIXTURES = Path(__file__).resolve().parent / "fixtures"
STRONG_PATH = FIXTURES / "deep_research_strong_flip.json"
WEAK_PATH = FIXTURES / "deep_research_weak_flip.json"

MATCH = "Milwaukee Brewers vs Colorado Rockies"
PRIOR_SEL = (
    "Handikap 2-veis -1.5 (inkludert ekstra innings): Milwaukee Brewers -1.5"
)
PRIOR_ODDS = 1.79


def _load_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_pack(payload: dict, tmp_path: Path, filename: str) -> dict:
    cfg = load_config()
    cfg = {
        **cfg,
        "paths": {**(cfg.get("paths") or {}), "evidence": str(tmp_path / "evidence")},
    }
    res = write_deep_research_pack(cfg, payload, filename=filename)
    assert res["ok"] is True, res.get("errors")
    assert res["pack"] is not None
    return res["pack"]


def _enabled_fc_cfg(**overrides):
    base = {
        "enabled": True,
        "live_ledger_only": True,
        "anchor_scan_limit": 30,
        "max_hours": 48,
        "max_games": 2,
        "heavy_fav_max_odds": 2.10,
        "include_pending_anchors": True,
        "base_penalty": 0.035,
        "pending_penalty": 0.015,
        "weak_extra_penalty": 0.025,
        "convincing_win_mult": 1.25,
        "strong_flip_min_ev": 0.06,
        "weak_flip_action": "soft_reject",
        "heavy_line_by_sport": {
            "baseball": 1.5,
            "basketball": 5.5,
            "football": 1.5,
            "ice_hockey": 1.5,
            "tennis": 2.5,
            "darts": 2.5,
            "esports": 1.5,
            "default": 1.5,
        },
    }
    base.update(overrides)
    return base


def _brewers_win_row(*, hours_ago: float = 8.0) -> dict:
    now = datetime.now(timezone.utc)
    ts = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d")
    return {
        "bet_id": "brewers-win-mapping-1",
        "match": MATCH,
        "selection": PRIOR_SEL,
        "sport": "baseball",
        "market_type": "Handikap 2-veis",
        "market_family": "baseball_handicap",
        "result": "Win",
        "decimal_odds": PRIOR_ODDS,
        "odds": PRIOR_ODDS,
        "updated_at": ts,
        "created_at": ts,
        "date": day,
        "notes": "",
        "source": "live",
    }


# ---------------------------------------------------------------------------
# Fixtures exist + helper can materialize packs
# ---------------------------------------------------------------------------
def test_fixture_files_exist():
    assert STRONG_PATH.is_file(), f"missing {STRONG_PATH}"
    assert WEAK_PATH.is_file(), f"missing {WEAK_PATH}"


def test_strong_pack_via_helper_maps_to_ge2_strong_signals(tmp_path: Path):
    payload = _load_payload(STRONG_PATH)
    pack = _write_pack(payload, tmp_path, "strong_flip.json")

    # Gate-safe S1 path: availability stays predicted; lineup_status + notes drive S1.
    assert pack["availability_status"] == "predicted"
    assert pack["lineup_status"] == "changed"
    assert "injury" in str(pack.get("lineup_notes") or "").lower() or "injury" in str(
        pack.get("availability_notes") or ""
    ).lower() or "lineup change" in str(pack.get("notes") or "").lower()

    # No weak idioms in S2 primary surfaces.
    why = str((pack.get("form_continuity") or {}).get("why_flip") or "")
    one = str((pack.get("opposite_side_check") or {}).get("one_liner") or "")
    summary = str(pack.get("summary") or "")
    for blob in (why, one, summary):
        assert not _blob_has_weak_phrase(blob), f"unexpected weak phrase in: {blob[:80]!r}"

    snap = build_evidence_snapshot(pack, "B")
    assert snap["injury_or_lineup_break"] is True
    assert len(str(snap.get("why_flip") or "").strip()) >= 40
    assert not _blob_has_weak_phrase(str(snap.get("why_flip") or ""))
    # Primary mapping: form_continuity.why_flip → snap.why_flip
    assert why[:40] in str(snap["why_flip"])

    n_strong, strong_ids = _count_strong_flip_signals(
        base_ev=0.07,
        grade="B",
        evidence_snapshot=snap,
        notes=str(pack.get("notes") or ""),
        strong_flip_min_ev=0.06,
    )
    assert n_strong >= 2, f"expected ≥2 strong signals, got {n_strong}: {strong_ids}"
    # Design strong-flip claims S1 + S2 + S4 (S3 also possible with EV+grade).
    assert "S1_injury_lineup" in strong_ids
    assert "S2_why_flip" in strong_ids
    assert "S4_structural" in strong_ids


def test_strong_pack_escape_soft_reject_on_flip(tmp_path: Path):
    """Strong pack evidence → demote only (no soft_reject) after heavy-fav win."""
    payload = _load_payload(STRONG_PATH)
    pack = _write_pack(payload, tmp_path, "strong_flip_pen.json")
    snap = build_evidence_snapshot(pack, "B")
    prior = _brewers_win_row(hours_ago=6.0)
    cand = {
        "match": pack["match"],
        "selection": pack["selection"],
        "sport": pack.get("sport") or "baseball",
        "market_type": "Handikap 2-veis",
        "market_family": pack.get("market_family") or "baseball_handicap",
        "decimal_odds": float(pack.get("decimal_odds_ref") or 1.85),
        "grade": "B",
        "base_ev": 0.07,
        "notes": str(pack.get("notes") or ""),
    }
    pen, reason, meta = form_continuity_penalty(
        cand,
        [prior],
        _enabled_fc_cfg(),
        base_ev=0.07,
        grade="B",
        notes=str(pack.get("notes") or ""),
        evidence_snapshot=snap,
    )
    assert meta.get("flip_detected") is True
    assert meta.get("strong_flip_evidence") is True
    assert meta.get("soft_reject") is False
    assert pen > 0.0
    assert reason.startswith("form_continuity:")
    assert len(meta.get("strong_signals") or []) >= 2


def test_weak_pack_fails_s2_and_soft_rejects(tmp_path: Path):
    payload = _load_payload(WEAK_PATH)
    pack = _write_pack(payload, tmp_path, "weak_flip.json")

    why = str((pack.get("form_continuity") or {}).get("why_flip") or "")
    assert _blob_has_weak_phrase(why), "weak fixture why_flip must trip weak-phrase ban"
    assert _blob_has_weak_phrase(str(pack.get("summary") or ""))

    snap = build_evidence_snapshot(pack, "B")
    # S2: why_flip present but weak-phrase-only → not counted as S2
    n_strong, strong_ids = _count_strong_flip_signals(
        base_ev=0.02,
        grade="B",
        evidence_snapshot=snap,
        notes=str(pack.get("notes") or ""),
        strong_flip_min_ev=0.06,
    )
    assert "S2_why_flip" not in strong_ids
    assert n_strong < 2, f"weak pack must not reach ≥2 strong signals: {strong_ids}"
    # No gate-safe S1: lineup not changed/uncertain and no injury tokens in S1 fields
    assert snap.get("injury_or_lineup_break") is False

    prior = _brewers_win_row(hours_ago=6.0)
    cand = {
        "match": pack["match"],
        "selection": pack["selection"],
        "sport": pack.get("sport") or "baseball",
        "market_type": "Handikap 2-veis",
        "market_family": pack.get("market_family") or "baseball_handicap",
        "decimal_odds": float(pack.get("decimal_odds_ref") or 1.85),
        "grade": "B",
        "base_ev": 0.02,
        "notes": str(pack.get("notes") or ""),
    }
    pen, reason, meta = form_continuity_penalty(
        cand,
        [prior],
        _enabled_fc_cfg(),
        base_ev=0.02,
        grade="B",
        notes=str(pack.get("notes") or ""),
        evidence_snapshot=snap,
    )
    assert meta.get("flip_detected") is True
    assert meta.get("soft_reject") is True
    assert meta.get("weak_evidence") is True
    assert meta.get("strong_flip_evidence") is False
    assert meta.get("has_weak_phrase") is True
    assert reason.startswith("form_continuity:")
    assert "rejected" in reason
    assert pen > 0.0


def test_snapshot_field_mapping_from_strong_fixture(tmp_path: Path):
    """build_evidence_snapshot field map from design G3 contract."""
    pack = _write_pack(_load_payload(STRONG_PATH), tmp_path, "strong_map.json")
    snap = build_evidence_snapshot(pack, "B")
    assert str(pack.get("summary") or "")[:40] in snap["summary"]
    assert str((pack.get("form_continuity") or {}).get("why_flip") or "")[:40] in snap[
        "why_flip"
    ]
    assert snap["higher_ranked_side"] == "favourite"
    assert snap["ranking_confidence"] == pytest.approx(0.8)
    assert snap["signals_rank_primary"] is True
    assert isinstance(snap.get("opposite_side_check"), dict)
    assert snap["opposite_side_check"].get("evaluated") is True
    assert snap["grade"] == "B"
