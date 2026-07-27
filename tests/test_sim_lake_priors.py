"""Optional lake-backed λ priors for football sim (data_platform.sim_features)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.sim_football import SimInputs, simulate_match, try_lake_lambda_priors


def _cfg_sim_features_on() -> dict[str, Any]:
    return {
        "data_platform": {
            "enabled": True,
            "sim_features": True,
            "lake_root": None,
            "allow_raw_sql": False,
        },
        "simulation": {"enabled": True},
    }


def _cfg_default_off() -> dict[str, Any]:
    return {
        "data_platform": {
            "enabled": False,
            "sim_features": False,
        },
        "simulation": {"enabled": True},
    }


def _mock_client_success(
    *,
    lambda_home: float = 1.72,
    lambda_away: float = 1.05,
) -> MagicMock:
    client = MagicMock()
    client.suggest_lambdas.return_value = {
        "api_version": "0.1",
        "ok": True,
        "match": "TeamA vs TeamB",
        "home": "TeamA",
        "away": "TeamB",
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "league_avg_xg": 1.35,
        "home_advantage": 1.08,
        "source_quality": "medium",
        "confidence": "medium",
        "warnings": ["goals_based_proxy_not_xg", "not_oddsen_clv"],
        "sim_inputs_compat": {
            "lambda_home": lambda_home,
            "lambda_away": lambda_away,
            "league_avg_xg": 1.35,
            "home_advantage": 1.08,
        },
        "n_home": 10,
        "n_away": 10,
    }
    return client


def _mock_client_thin() -> MagicMock:
    client = MagicMock()
    client.suggest_lambdas.return_value = {
        "api_version": "0.1",
        "ok": True,
        "lambda_home": None,
        "lambda_away": None,
        "league_avg_xg": 1.35,
        "home_advantage": 1.08,
        "source_quality": "low",
        "confidence": "low",
        "warnings": ["goals_based_proxy_not_xg", "not_oddsen_clv", "thin_sample"],
        "sim_inputs_compat": {
            "lambda_home": None,
            "lambda_away": None,
            "league_avg_xg": 1.35,
            "home_advantage": 1.08,
        },
        "n_home": 2,
        "n_away": 1,
    }
    return client


def test_default_off_does_not_call_client():
    """sim_features false → no lake call even if a client is injected."""
    client = _mock_client_success()
    inp = SimInputs(home="TeamA", away="TeamB", match="TeamA vs TeamB")
    out, warnings, meta = try_lake_lambda_priors(inp, _cfg_default_off(), data_client=client)
    client.suggest_lambdas.assert_not_called()
    assert meta is None
    assert warnings == []
    assert out.lambda_home is None
    assert out.lambda_away is None


def test_enabled_without_sim_features_does_not_call():
    client = _mock_client_success()
    cfg = {
        "data_platform": {"enabled": True, "sim_features": False},
        "simulation": {"enabled": True},
    }
    inp = SimInputs(home="TeamA", away="TeamB")
    _, warnings, meta = try_lake_lambda_priors(inp, cfg, data_client=client)
    client.suggest_lambdas.assert_not_called()
    assert meta is None
    assert warnings == []


def test_sim_features_applies_lambdas_and_goals_based_proxy_warning():
    client = _mock_client_success(lambda_home=1.72, lambda_away=1.05)
    inp = SimInputs(home="TeamA", away="TeamB", league="E0")
    result = simulate_match(inp, _cfg_sim_features_on(), data_client=client)
    client.suggest_lambdas.assert_called_once()
    call_kw = client.suggest_lambdas.call_args
    assert call_kw.args[0] == "TeamA"
    assert call_kw.args[1] == "TeamB"
    assert call_kw.kwargs.get("league") == "E0"
    assert abs(result.lambda_home - 1.72) < 1e-6
    assert abs(result.lambda_away - 1.05) < 1e-6
    joined = " ".join(result.warnings)
    assert "goals_based_proxy" in joined
    assert "lake_lambda_prior" in joined
    assert result.inputs.get("lake_lambda_prior") is True
    assert "lake_lambda_prior" in result.evidence_snippet


def test_explicit_lambdas_not_overridden():
    client = _mock_client_success(lambda_home=9.9, lambda_away=9.9)
    inp = SimInputs(
        home="TeamA",
        away="TeamB",
        lambda_home=1.5,
        lambda_away=1.2,
    )
    result = simulate_match(inp, _cfg_sim_features_on(), data_client=client)
    client.suggest_lambdas.assert_not_called()
    assert abs(result.lambda_home - 1.5) < 1e-6
    assert abs(result.lambda_away - 1.2) < 1e-6
    assert not any("goals_based_proxy" in w for w in result.warnings)
    assert result.inputs.get("lake_lambda_prior") is False


def test_thin_lake_sample_does_not_invent_lambdas():
    client = _mock_client_thin()
    inp = SimInputs(home="TeamA", away="TeamB", league="E0")
    with pytest.raises(ValueError, match=r"lambda|Missing"):
        simulate_match(inp, _cfg_sim_features_on(), data_client=client)
    client.suggest_lambdas.assert_called_once()
    # try_lake path still surfaces proxy warning before resolve fails
    out, warnings, meta = try_lake_lambda_priors(
        SimInputs(home="TeamA", away="TeamB", league="E0"),
        _cfg_sim_features_on(),
        data_client=client,
    )
    assert meta is not None
    assert out.lambda_home is None
    assert out.lambda_away is None
    assert any("goals_based_proxy" in w for w in warnings)
    assert any("thin_or_null" in w for w in warnings)


def test_simulate_match_never_auto_writes_evidence(tmp_path, monkeypatch):
    """simulate_match itself does not write evidence packs (CLI --write-evidence only)."""
    client = _mock_client_success()
    written: list[Path] = []

    def _boom(*_a, **_k):  # if someone wires auto-write, fail loudly
        written.append(Path("should_not_happen"))
        raise AssertionError("write_evidence_from_sim must not run inside simulate_match")

    import nt.sim_football as sf

    monkeypatch.setattr(sf, "write_evidence_from_sim", _boom)
    result = simulate_match(
        SimInputs(home="TeamA", away="TeamB"),
        _cfg_sim_features_on(),
        data_client=client,
    )
    assert result.lambda_home > 0
    assert written == []


def test_live_config_sim_features_default_off():
    from nt.config import load_config
    from nt.defaults import data_platform_cfg

    dp = data_platform_cfg(load_config())
    assert dp["sim_features"] is False
    assert dp["enabled"] is False
