"""PR3 ESR: cutover defaults — FEH place-owning off, band/tiers fail-open to ESR."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.evidence_hierarchy.score import place_uses_saef
from nt.light_research import tiers_cfg
from nt.odds_confidence import odds_confidence_cfg


def test_place_uses_saef_false_under_cutover_config():
    """Production config kill-switch: place_uses_saef must be False under ESR."""
    cfg = load_config()
    assert place_uses_saef(cfg) is False
    ev = (cfg.get("selection") or {}).get("evidence") or {}
    assert ev.get("shadow_mode") is True
    assert (ev.get("forced_hierarchy") or {}).get("enabled") is False


def test_place_uses_saef_false_when_keys_missing():
    """Missing evidence keys → fail-safe off (triple gate defaults)."""
    assert place_uses_saef({}) is False
    assert place_uses_saef({"selection": {}}) is False
    assert place_uses_saef({"selection": {"evidence": {"enabled": True}}}) is False
    # shadow default True + fh.enabled default False
    assert (
        place_uses_saef(
            {
                "selection": {
                    "evidence": {
                        "enabled": True,
                        "shadow_mode": False,
                        "forced_hierarchy": {"enabled": False},
                    }
                }
            }
        )
        is False
    )


def test_place_uses_saef_true_only_with_explicit_feh_fixture():
    """FEH unit tests inject place-owning; production does not."""
    cfg = {
        "selection": {
            "evidence": {
                "enabled": True,
                "shadow_mode": False,
                "forced_hierarchy": {"enabled": True},
            }
        }
    }
    assert place_uses_saef(cfg) is True


def test_odds_confidence_cfg_esr_defaults():
    """Empty/missing odds_confidence → ESR floors (Band A B/2%/4, UD reject off)."""
    oc = odds_confidence_cfg({})
    assert oc["enabled"] is True
    assert float(oc["usable_lo"]) == 1.40
    assert float(oc["usable_hi"]) == 2.50
    assert oc["underdog_hc_negative_h2h_reject"] is False
    assert float(oc["soft_missing_matchup_stake_mult"]) == 0.85

    band_a = oc["bands"]["A"]
    assert str(band_a["min_grade"]).upper() == "B"
    assert float(band_a["min_ev"]) == 0.02
    assert int(band_a["min_sources"]) == 4
    assert float(band_a["stake_mult"]) == 0.95
    assert band_a.get("require_h2h_or_rank_form") is True

    band_d = oc["bands"]["D"]
    assert float(band_d["hi"]) == 2.50
    assert band_d.get("underdog_hc_require_matchup") is False


def test_odds_confidence_cfg_yaml_cutover_aligns():
    """Live config.yaml odds_confidence matches ESR usable_hi / UD flag."""
    cfg = load_config()
    oc = odds_confidence_cfg(cfg)
    assert float(oc["usable_hi"]) == 2.50
    assert oc["underdog_hc_negative_h2h_reject"] is False
    assert str(oc["bands"]["A"]["min_grade"]).upper() == "B"
    assert int(oc["bands"]["A"]["min_sources"]) == 4


def test_tiers_cfg_esr_defaults():
    """Empty tiers → composition off, preferred boost 0, short_main pen 0."""
    t = tiers_cfg({})
    assert float(t["deep_min_preferred_share"]) == 0.0
    assert float(t["deep_max_short_main_share"]) == 1.0
    assert float(t["promo_preferred_boost"]) == 0.0
    assert float(t["promo_short_main_penalty"]) == 0.0
    assert float(t["promo_mid_band_boost"]) == 8.0
    assert float(t["promo_short_chalk_penalty"]) == -12.0
    assert float(t["preferred_odds_lo"]) == 1.40
    assert float(t["preferred_odds_hi"]) == 2.80
    assert float(t["short_chalk_odds"]) == 1.50
    assert t.get("promo_require_signal_for_family_boost") is True
    assert float(t["promo_mid_band_lo"]) == 1.85
    assert float(t["promo_mid_band_hi"]) == 2.40


def test_tiers_cfg_yaml_cutover_composition_off():
    cfg = load_config()
    t = tiers_cfg(cfg)
    assert float(t["deep_min_preferred_share"]) == 0.0
    assert float(t["deep_max_short_main_share"]) >= 1.0 - 1e-9
