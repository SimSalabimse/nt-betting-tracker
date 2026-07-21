"""P0: full-delta learning accept requires n≥5 and conf≥0.35."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.settlement_review import auto_resolve_learning_proposals, learning_proposals_path


def _cfg(tmp: Path) -> dict:
    state = tmp / "state"
    state.mkdir(parents=True, exist_ok=True)
    (tmp / "data").mkdir(exist_ok=True)
    bets = tmp / "data" / "bets.csv"
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,payout_nok,"
        "research_grade,odds_band,sport,market_type,phase,notes,source,created_at,updated_at\n",
        encoding="utf-8",
    )
    learn = state / "learning.json"
    learn.write_text(
        json.dumps(
            {
                "sports": {
                    "tennis": {"stake_mult": 1.0, "ev_boost": 0.0, "n": 10, "status": "ok"}
                },
                "markets": {},
            }
        ),
        encoding="utf-8",
    )
    return {
        "paths": {
            "bets": str(bets),
            "state_dir": str(state),
            "learning_json": str(learn),
            "learning_proposals_json": str(state / "learning_proposals.json"),
            "outbox": str(tmp / "outbox"),
        },
        "learning": {"enabled": True, "auto_apply_proposals": True, "min_sample": 12},
        "bankroll": {"baseline_nok": 500},
    }


def _write_pending(cfg: dict, *, n: int, conf: float, d_stake: float = 0.05) -> str:
    path = learning_proposals_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    pid = f"sport:tennis:test-{n}-{conf}"
    payload = {
        "proposals": [
            {
                "id": pid,
                "kind": "sport",
                "name": "tennis",
                "status": "pending",
                "current": {"stake_mult": 1.0, "ev_boost": 0.0, "n": n},
                "proposed": {"stake_mult": round(1.0 + d_stake, 3), "ev_boost": 0.01},
                "layers": {"confidence": conf},
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return pid


def test_full_delta_accept_when_n_and_conf_ok(tmp_path: Path):
    cfg = _cfg(tmp_path)
    pid = _write_pending(cfg, n=5, conf=0.40, d_stake=0.05)
    out = auto_resolve_learning_proposals(cfg)
    assert pid in out["accepted"]
    assert pid not in out["modified"]


def test_soft_modify_when_n_below_5(tmp_path: Path):
    cfg = _cfg(tmp_path)
    pid = _write_pending(cfg, n=2, conf=0.50, d_stake=0.05)
    out = auto_resolve_learning_proposals(cfg)
    assert pid in out["modified"]
    assert pid not in out["accepted"]


def test_soft_modify_when_conf_below_035(tmp_path: Path):
    cfg = _cfg(tmp_path)
    pid = _write_pending(cfg, n=10, conf=0.20, d_stake=0.05)
    out = auto_resolve_learning_proposals(cfg)
    assert pid in out["modified"]
    assert pid not in out["accepted"]


def test_zero_delta_rejected(tmp_path: Path):
    cfg = _cfg(tmp_path)
    path = learning_proposals_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    pid = "sport:tennis:zero"
    path.write_text(
        json.dumps(
            {
                "proposals": [
                    {
                        "id": pid,
                        "kind": "sport",
                        "name": "tennis",
                        "status": "pending",
                        "current": {"stake_mult": 1.0, "ev_boost": 0.0, "n": 10},
                        "proposed": {"stake_mult": 1.0, "ev_boost": 0.0},
                        "layers": {"confidence": 0.9},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out = auto_resolve_learning_proposals(cfg)
    assert pid in out["rejected"]
