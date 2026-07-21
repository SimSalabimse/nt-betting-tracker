"""P0: phase peak uses settlement calendar day (shared with capital_v2)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.capital_v2 import peak_equity_settlement
from nt.phase import _peak_equity


def test_phase_peak_matches_capital_v2_settlement_day():
    # Win booked on match date 2026-07-10 but settled (updated_at) 2026-07-12
    rows = [
        {
            "result": "Win",
            "p_l_nok": "20",
            "date": "2026-07-10",
            "updated_at": "2026-07-12T10:00:00Z",
            "created_at": "2026-07-10T12:00:00Z",
        },
        {
            "result": "Pending",
            "p_l_nok": "0",
            "date": "2026-07-11",
            "updated_at": "2026-07-11T08:00:00Z",
        },
    ]
    baseline = 500.0
    assert _peak_equity(rows, baseline) == peak_equity_settlement(rows, baseline)
    # Settlement-day curve should see +20 on 2026-07-12 (Oslo), not invent match-day peak alone
    assert _peak_equity(rows, baseline) == 520.0


def test_phase_peak_ignores_pending():
    rows = [
        {
            "result": "Pending",
            "p_l_nok": "0",
            "date": "2026-07-10",
            "updated_at": "2026-07-10T12:00:00Z",
        }
    ]
    assert _peak_equity(rows, 500.0) == 500.0
