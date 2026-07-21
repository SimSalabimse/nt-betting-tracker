"""Phase 4: evidence soft-attach + odds_common keys + prune script dry-run."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.odds_common import evidence_pair_key, normalize_selection_key
from nt.odds_parse import Candidate, attach_evidence


def test_normalize_selection_vinner_vs_to_win():
    a = normalize_selection_key("Vinner: Merida, Daniel")
    b = normalize_selection_key("Merida, Daniel to Win")
    assert a == b


def test_attach_evidence_soft_match(tmp_path: Path):
    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir()
    pack = {
        "match": "Burruchaga, Roman Andres vs Merida, Daniel",
        "selection": "Vinner: Merida, Daniel",
        "sport": "tennis",
        "p_model": 0.66,
        "summary": "soft attach test pack",
        "failure_modes": "upset",
        "sources": [{"url": "https://example.com", "takeaway": "form"}],
    }
    (ev_dir / "merida_ml.json").write_text(
        json.dumps(pack, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    c = Candidate(
        date="2026-07-20",
        match="Burruchaga, Roman Andres vs Merida, Daniel",
        selection="Merida, Daniel to Win",  # spelling variant
        decimal_odds=1.55,
        sport="tennis",
    )
    attach_evidence([c], ev_dir)
    assert c.evidence is not None
    assert c.p_model == pytest.approx(0.66)


def test_evidence_pair_key_stable():
    k1 = evidence_pair_key("A - B", "Vinner: A")
    k2 = evidence_pair_key("A vs B", "A to Win")
    assert k1[0] == k2[0]
    assert k1[1] == k2[1]


def test_prune_api_raw_dry_run():
    import importlib.util
    import os
    import tempfile
    import time

    spec = importlib.util.spec_from_file_location(
        "prune_api_raw",
        ROOT / "scripts" / "prune_api_raw.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "old.json").write_text("{}", encoding="utf-8")
        old = time.time() - 10 * 86400
        os.utime(root / "old.json", (old, old))
        rc = mod.main(["--root", str(root), "--days", "7"])
        assert rc == 0
        assert (root / "old.json").is_file()  # dry-run keeps it
