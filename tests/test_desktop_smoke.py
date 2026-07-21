from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from desktop.services.state_service import StateService, is_valid_project_root
from desktop.views.analytics import build_analytics
from desktop.views.bets import BetsView
from desktop.views.book import BookView
from desktop.views.dashboard import build_dashboard
from desktop.views.lab import LabView
from desktop.views.learnings import build_learnings
from desktop.views.risk_phase import build_risk_phase
from nt.decisions import load_decisions, score_outcome, score_process
from nt.learning import load_learning_history


class _FakePage:
    def update(self):
        pass

    def run_task(self, *a, **k):
        pass


def test_project_root_valid():
    assert is_valid_project_root(ROOT)


def test_state_matches_cli_equity():
    svc = StateService(ROOT)
    st = svc.reload(write_state=True)
    b = st.bankroll
    assert abs(float(b["equity_nok"]) - (float(b["baseline_nok"]) + float(b["realized_pl_nok"]))) < 0.02
    assert st.phase["phase_id"] in ("1A", "1B", "2", "3", "4", "5")
    assert len(st.rows) >= 1
    assert not st.errors
    assert st.equity_curve
    assert abs(st.equity_curve[-1]["equity"] - float(b["equity_nok"])) < 0.02
    assert isinstance(st.learning, dict)
    assert isinstance(st.decisions, dict)
    assert isinstance(st.learning_history, list)


def test_views_build():
    svc = StateService(ROOT)
    st = svc.reload(write_state=False)
    page = _FakePage()
    assert build_dashboard(st) is not None
    assert build_analytics(st) is not None
    assert build_learnings(st) is not None
    assert build_risk_phase(st) is not None
    book = BookView(svc, page)
    assert book.build(st) is not None
    lab = LabView()
    assert lab.build(st) is not None
    from desktop.views.desk import DeskView

    desk = DeskView(svc, page)
    assert desk.build() is not None


def test_bets_list_not_empty():
    svc = StateService(ROOT)
    svc.reload(write_state=False)
    page = _FakePage()
    bv = BetsView(svc, page)
    bv.build(svc.state)
    assert len(bv.list_col.controls) > 0
    assert "bets" in (bv.count.value or "") or "showing" in (bv.count.value or "")


def test_forensic_drill_bet_ids():
    """Chart/table drill resolves grain via group_stats_with_ids → bet_ids."""
    svc = StateService(ROOT)
    svc.reload(write_state=False)
    ids = svc.drill_forensic("sport", "football", "Sport: football")
    assert len(ids) > 0
    assert svc.state.forensic_label.startswith("Sport")
    filtered = svc.filtered_rows(bet_ids=ids)
    assert len(filtered) == len(ids)
    assert all(r.get("sport") == "football" for r in filtered)
    svc.clear_forensic()
    assert svc.state.forensic_bet_ids is None

    book = BookView(svc, _FakePage())
    book.drill("sport", "football", "Sport: football")
    assert book._tab == 1  # Tickets
    assert svc.state.forensic_bet_ids


def test_decisions_and_process_scores():
    cfg = StateService(ROOT).reload(write_state=False).cfg
    decs = load_decisions(cfg)
    row = {"result": "Win", "p_l_nok": "10", "research_grade": "B", "source": "recommend"}
    p = score_process(None, row)
    o = score_outcome(row, None)
    assert p["score"]
    assert o["score"]
    if decs:
        bid, d = next(iter(decs.items()))
        p2 = score_process(d, {**row, "bet_id": bid})
        assert p2["label"]


def test_learning_history_loadable():
    svc = StateService(ROOT)
    st = svc.reload(write_state=False)
    hist = load_learning_history(st.cfg, limit=20)
    assert isinstance(hist, list)


def test_ops_helpers():
    svc = StateService(ROOT)
    svc.reload(write_state=False)
    assert isinstance(svc.inbox_odds_files(), list)
    assert isinstance(svc.inbox_results_files(), list)
    assert isinstance(svc.latest_rejects_text(), str)
    assert isinstance(svc.latest_receipt_text(), str)
