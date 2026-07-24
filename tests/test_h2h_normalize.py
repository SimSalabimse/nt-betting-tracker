"""H2H / strength normalization — qualitative mixed strings are not positive."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence_hierarchy.h2h_normalize import normalize_h2h, normalize_strength


def test_mixed_competitive_not_positive():
    n = normalize_h2h("mixed_competitive")
    assert n.positive is False
    assert n.negative is False
    assert n.mixed is True
    assert n.polarity == "mixed"


def test_mixed_string_synonyms():
    for s in ("mixed", "competitive", "even", "neutral", "close"):
        n = normalize_h2h(s)
        assert n.positive is False, s
        assert n.polarity == "mixed", s


def test_positive_and_negative_strings():
    assert normalize_h2h("positive").positive is True
    assert normalize_h2h("negative").negative is True
    assert normalize_h2h("dominates").positive is True
    assert normalize_h2h("never beaten").negative is True


def test_numeric_edge():
    assert normalize_h2h(0.2).positive is True
    assert normalize_h2h(-0.3).negative is True
    assert normalize_h2h(0.0).mixed is True
    assert normalize_h2h("0.15").positive is True


def test_pack_h2h_mixed_competitive_smith_shape():
    pack = {
        "h2h": {
            "checked": True,
            "edge": "mixed_competitive",
            "summary": "Recent H2H competitive Price slight lead.",
        }
    }
    n = normalize_h2h(pack)
    assert n.checked is True
    assert n.positive is False
    assert n.negative is False
    assert n.mixed is True


def test_normalize_strength_strings():
    num, pol = normalize_strength("positive")
    assert pol == "positive"
    assert num is not None and num > 0
    num, pol = normalize_strength("mixed")
    assert pol == "mixed"
    assert num == 0.0
    num, pol = normalize_strength(-0.5)
    assert pol == "negative"
    assert num == -0.5
