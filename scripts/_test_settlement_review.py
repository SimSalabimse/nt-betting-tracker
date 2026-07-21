"""Quick smoke test for settlement review (run: python scripts/_test_settlement_review.py)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.settlement_review import analyze_settled_batch
from nt.fetchers import evaluate_selection_from_score


def main() -> None:
    assert evaluate_selection_from_score("Over 2.5", "H", "A", 2, 1)["outcome"] == "win"
    assert evaluate_selection_from_score("Under 2.5", "H", "A", 0, 0)["outcome"] == "win"

    cfg = load_config()
    empty = analyze_settled_batch(cfg, [], rows=[])
    assert empty["summary"]["n"] == 0

    rows = [
        {
            "bet_id": "test1",
            "match": "A vs B",
            "selection": "Over 2.5",
            "result": "Loss",
            "p_l_nok": "-10",
            "decimal_odds": "1.7",
            "sport": "football",
            "market_type": "totals",
            "odds_band": "1.5-1.8",
            "research_grade": "B",
            "phase": "1A",
            "stake_nok": "10",
        }
    ]
    items = [
        {
            "bet_id": "test1",
            "result": "Loss",
            "score": "0-0",
            "variance_tag": "process_error",
            "research_quality_retro": "poor",
        }
    ]
    rep = analyze_settled_batch(cfg, items, rows=rows)
    assert rep["summary"]["n"] == 1
    assert rep["reviews"][0]["variance_class"] == "process_error"
    print("settlement_review smoke OK", rep["summary"])
    print("proposals", len(rep.get("proposals") or []))


if __name__ == "__main__":
    main()
