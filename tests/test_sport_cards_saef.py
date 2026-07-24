"""Sport Research Cards + SAEF grade path (PR1 restore + shadow)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import grade_evidence
from nt.evidence_hierarchy import (
    ensure_sport_card,
    list_onboarded_sports,
    load_sport_card,
    score_evidence,
)
from nt.evidence_hierarchy.h2h_normalize import normalize_h2h
from nt.evidence_hierarchy.score import place_uses_saef
from nt.research import list_sources, scaffold_evidence

# Expected .py modules under evidence_hierarchy (no pyc-only ship)
_REQUIRED_HIERARCHY_PY = (
    "__init__.py",
    "types.py",
    "normalize.py",
    "h2h_normalize.py",
    "cards.py",
    "score.py",
    "checklist.py",
    "side_select.py",
    "anti_soft_underdog.py",
    "feh.py",
)


def _cfg(**ev_over):
    # SAEF place unit tests: enabled + not shadow + forced_hierarchy (triple gate)
    evidence = {
        "enabled": True,
        "shadow_mode": False,
        "auto_onboard_cards": True,
        "strict_band_cd": True,
        "min_takeaway_chars": 24,
        "min_quality_sources_floor": 3,
        "min_quality_sources_b": 4,
        "min_E_grade_b": 0.55,
        "forced_hierarchy": {"enabled": True},
    }
    evidence.update(ev_over)
    return {
        "selection": {
            "probability_haircut": 0.03,
            "high_odds_threshold": 2.5,
            "high_odds_min_grade": "A",
            "grade_a_require_uncertainty": True,
            "min_research_sources": {"default": 6, "grade_A": 10, "high_odds": 12},
            "evidence": evidence,
        },
        "research": {"gates": {"enabled": True}},
        "paths": {"evidence": str(ROOT / "evidence")},
    }


def _soft_ud_pack() -> dict:
    """Soft underdog HC mid-band pack that passes research gates (legacy placeable)."""
    sources = _quality_sources(6, "flashscore.com")
    sources.append(
        {
            "name": "PDC",
            "url": "https://www.pdc.tv/event/soft-ud-fixture",
            "takeaway": (
                "No withdrawals; both players listed active for the session "
                "with no injury or fitness flags on the board."
            ),
            "kind": "injury",
        }
    )
    return {
        "sport": "darts",
        "selection": "Legs handikap +2.5: Underdog Player +2.5",
        "summary": (
            "Mid-odds underdog explore look at attractive price with enough "
            "text for a transparent core reason."
        ),
        "failure_modes": "favourite whitewash in a one-sided thrashing.",
        "p_model": 0.55,
        "sources": sources,
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "h2h": {"checked": False, "edge": None, "summary": ""},
        "signals": {},
        "availability_status": "stable_guess",
        "availability_notes": (
            "Both players listed active on PDC board; no WD or injury flags; "
            "fitness assumed full for ranking event."
        ),
        "context_risk": "low",
    }


def _quality_sources(n: int = 6, domain: str = "hltv.org") -> list[dict]:
    return [
        {
            "name": f"src{i}",
            "url": f"https://{domain}/p/{i}",
            "takeaway": (
                f"Detailed takeaway number {i} with enough characters for quality "
                f"source counting and multi-domain checks."
            ),
        }
        for i in range(n)
    ]


def test_hierarchy_package_has_sources_not_pyc_only():
    pkg = ROOT / "nt" / "evidence_hierarchy"
    for name in _REQUIRED_HIERARCHY_PY:
        assert (pkg / name).is_file(), f"missing source {name}"
    # import smoke
    import nt.evidence_hierarchy as eh
    import nt.evidence_hierarchy.cards as cards
    import nt.evidence_hierarchy.h2h_normalize as h2h
    import nt.evidence_hierarchy.score as score

    assert eh.score_evidence is score.score_evidence
    assert h2h.normalize_h2h("mixed_competitive").positive is False
    assert cards.load_sport_card("darts") is not None


def test_main_sport_cards_exist_and_onboarded():
    for sport in (
        "football",
        "tennis",
        "darts",
        "snooker",
        "baseball",
        "basketball",
        "esports",
    ):
        card = load_sport_card(sport)
        assert card is not None, sport
        assert card.onboarded is True, sport
        assert card.schema_version == 1, sport
    onboarded = list_onboarded_sports()
    assert "football" in onboarded
    assert "darts" in onboarded


def test_darts_stable_ids_and_aliases():
    card = load_sport_card("darts")
    assert card is not None
    ids = card.stable_factor_ids()
    assert "checkout_scoring" in ids
    assert "ranking_seed" in ids
    assert "avg_checkout" not in ids  # alias only, not primary id
    assert "ranking_strength" not in ids
    assert card.signal_id_aliases.get("avg_checkout") == "checkout_scoring"
    assert card.signal_id_aliases.get("ranking_strength") == "ranking_seed"
    assert card.resolve_signal_id("avg_checkout") == "checkout_scoring"
    assert card.resolve_signal_id("ranking_seed") == "ranking_seed"


def test_smith_pack_signals_map_to_card_slots():
    """Live Smith pack factor ids map onto darts card without silent drop."""
    pack_path = (
        ROOT
        / "evidence"
        / "smith_ross_vs_price_gerwyn_runde_handikap_2_5_smith_ross_2_5.json"
    )
    if not pack_path.is_file():
        # Minimal fixture matching live pack signal ids
        pack = {
            "sport": "darts",
            "signals": {
                "h2h_matchup": {"filled": True, "strength": "mixed"},
                "recent_form": {"filled": True, "strength": "positive"},
                "checkout_scoring": {"filled": True, "strength": "positive"},
                "ranking_seed": {"filled": True, "strength": "negative"},
                "format_stage": {"filled": True, "strength": "positive"},
            },
            "h2h": {"checked": True, "edge": "mixed_competitive", "summary": "competitive"},
        }
    else:
        pack = json.loads(pack_path.read_text(encoding="utf-8"))

    card = load_sport_card("darts")
    assert card is not None
    mapping = card.map_pack_signals(pack.get("signals") or {})
    filled = [
        sid
        for sid, sig in (pack.get("signals") or {}).items()
        if isinstance(sig, dict) and sig.get("filled")
    ]
    assert filled, "expected filled signals"
    for sid in filled:
        assert mapping.get(sid), f"signal {sid} not mapped to a card slot"
        assert mapping[sid] in card.stable_factor_ids()

    # Score uses aliases too (avg_checkout → checkout_scoring)
    sc = score_evidence(
        pack,
        sport="darts",
        selection=str(pack.get("selection") or "Runde handikap +2.5"),
        odds=1.85,
        card=card,
    )
    assert "checkout_scoring" in sc.filled_slots or any(
        f.get("id") == "checkout_scoring" and f.get("filled") for f in sc.factors
    )
    h2h = normalize_h2h(pack)
    assert h2h.positive is False


def test_shadow_mode_does_not_own_place():
    """PR1: production-like shadow keeps legacy place; soft dogs still placeable."""
    # Production-like: shadow on, forced_hierarchy off
    cfg_shadow = _cfg(
        shadow_mode=True,
        enabled=True,
        forced_hierarchy={"enabled": False},
    )
    assert place_uses_saef(cfg_shadow) is False
    # Flipping shadow alone still must not own place without forced_hierarchy
    cfg_shadow_off_only = _cfg(
        shadow_mode=False,
        enabled=True,
        forced_hierarchy={"enabled": False},
    )
    assert place_uses_saef(cfg_shadow_off_only) is False

    pack = _soft_ud_pack()
    grade_shadow, issues_shadow = grade_evidence(
        pack, cfg_shadow, 1.90, selection=pack["selection"], sport="darts"
    )
    # Legacy path grades B/C (soft dog still placeable) while SAEF audits
    assert grade_shadow in ("A", "B", "C"), (grade_shadow, issues_shadow)
    assert any("saef" in i.lower() for i in issues_shadow)

    # Same pack under place-owning triple gate → SAEF F (no matchup)
    cfg_own = _cfg(shadow_mode=False, forced_hierarchy={"enabled": True})
    assert place_uses_saef(cfg_own) is True
    grade_own, issues_own = grade_evidence(
        pack, cfg_own, 1.90, selection=pack["selection"], sport="darts"
    )
    assert grade_own == "F", (grade_own, issues_own)
    assert any("saef:HR_NO_MATCHUP_UD" in i or "HR_NO_MATCHUP" in i for i in issues_own)


def test_list_sources_esports_not_football():
    srcs = list_sources("esports")
    names = " ".join(s.get("name", "") for s in srcs).lower()
    assert "hltv" in names or "liquipedia" in names
    assert "fbref" not in names


def test_list_sources_darts_not_football():
    srcs = list_sources("darts")
    blob = " ".join(s.get("url", "") for s in srcs).lower()
    assert "fbref" not in blob
    assert "pdc" in blob or "darts" in blob or "flashscore" in blob


def test_weak_underdog_hc_rejected_mid_band():
    """Soft underdog HC @1.90 without H2H → Grade F under SAEF place ownership."""
    cfg = _cfg(shadow_mode=False, forced_hierarchy={"enabled": True})
    pack = _soft_ud_pack()
    grade, issues = grade_evidence(
        pack,
        cfg,
        1.90,
        selection=pack["selection"],
        sport="darts",
    )
    assert grade == "F", (grade, issues)
    assert any("saef:HR_NO_MATCHUP" in i or "HR_NO_MATCHUP" in i for i in issues)


def test_negative_h2h_underdog_hard_reject():
    cfg = _cfg(shadow_mode=False, forced_hierarchy={"enabled": True})
    pack = {
        "sport": "tennis",
        "selection": "Game handikap +3.5: Dog Player +3.5",
        "summary": "Underdog HC with clear form notes but terrible H2H history.",
        "failure_modes": "never covers",
        "p_model": 0.54,
        "sources": _quality_sources(6, "tennisexplorer.com"),
        "h2h": {"checked": True, "edge": -0.3, "summary": "never beaten this opponent 0-5"},
        "signals": {
            "surface_h2h": {
                "filled": True,
                "strength": -0.5,
                "note": "Never beaten opponent on this surface; 0-5 H2H negative.",
            },
            "serve_return": {
                "filled": True,
                "strength": 0.6,
                "note": "Serve holds well enough on hard courts this month.",
            },
            "fitness_fatigue": {
                "filled": True,
                "strength": 0.5,
                "note": "Both players rested after early exits last week.",
            },
        },
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
    }
    grade, issues = grade_evidence(
        pack, cfg, 1.95, selection=pack["selection"], sport="tennis"
    )
    assert grade == "F"
    assert any("HR_NEG_H2H" in i or "saef:HR_NEG" in i for i in issues)


def test_quality_mid_band_can_reach_grade_b():
    cfg = _cfg(
        shadow_mode=False,
        forced_hierarchy={
            "enabled": True,
            "require_checklist": True,
            "anti_soft_underdog": True,
            "allow_soft_ud_grade_c": False,
            "side_first": True,
        },
    )
    # Favourite ML (short) — anti-soft N/A; complete FEH checklist for place-owning
    pack = {
        "sport": "darts",
        "selection": "Vinner: Strong Player",
        "summary": (
            "Clear core: superior 3-dart average and positive H2H support this ML "
            "at mid odds; market slightly long on form spike."
        ),
        "failure_modes": "nerves on TV stage",
        "p_model": 0.58,
        "sources": _quality_sources(6, "dartsorakel.com"),
        "h2h": {
            "checked": True,
            "edge": 0.15,
            "summary": "Leads H2H 4-1 in last meetings with higher averages.",
        },
        "signals": {
            # stable ids (worktree SSOT)
            "checkout_scoring": {
                "filled": True,
                "strength": 0.8,
                "note": "Averaging 98+ last five with 40% checkout — clear form edge.",
            },
            "h2h_matchup": {
                "filled": True,
                "strength": 0.7,
                "note": "H2H 4-1 last meetings; dominates on legs average.",
            },
            "recent_form": {
                "filled": True,
                "strength": 0.7,
                "note": "Won last four ranking events legs at high average.",
            },
            "format_stage": {
                "filled": True,
                "strength": 0.5,
                "note": "BO11 suits higher average player historically.",
            },
            "ranking_seed": {
                "filled": True,
                "strength": 0.6,
                "note": "Seed gap supports favourite ML at this price.",
            },
        },
        "script_lean": "dominant_favorite",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "context_risk": "low",
        "availability_status": "stable_guess",
        "availability_notes": "No injury flags; full field expected on PDC ranking event.",
        "feh_checklist": {
            "schema_version": 1,
            "higher_ranked_side": "favourite",
            "ranking_confidence": 0.8,
            "better_form_side": "favourite",
            "form_confidence": 0.7,
            "h2h_verdict": "positive",
            "h2h_summary": "Leads H2H 4-1 in last meetings with higher averages.",
            "natural_markets": ["none"],
            "natural_market_hint": "none",
            "underdog_supported_by_evidence": False,
            "underdog_support_reason": (
                "Not an underdog pick; favourite ML supported by rank and H2H."
            ),
            "why_this_side_not_opposite": (
                "Ranking, form and positive H2H all support Strong Player favourite "
                "ML rather than the underdog opposite side."
            ),
            "strongest_positive": "H2H 4-1 and 98+ average form edge clear.",
            "strongest_negative": "TV stage nerves can compress averages briefly.",
            "primary_factors_used": [
                "h2h_matchup",
                "checkout_scoring",
                "recent_form",
            ],
        },
    }
    # Odds < soft_ud_lo → anti-soft ML dog gate does not apply
    grade, issues = grade_evidence(
        pack, cfg, 1.55, selection=pack["selection"], sport="darts"
    )
    assert grade in ("A", "B"), (grade, issues[:8])


def test_saef_alias_signals_fill_stable_slots():
    """Packs using SAEF-era avg_checkout / ranking_strength still fill darts slots."""
    card = load_sport_card("darts")
    pack = {
        "summary": "Alias migration pack with averages and ranking notes long enough.",
        "sources": _quality_sources(5, "dartsorakel.com"),
        "h2h": {"checked": True, "edge": 0.1, "summary": "H2H leads 3-1 recently."},
        "signals": {
            "avg_checkout": {
                "filled": True,
                "strength": 0.8,
                "note": "98 average last five; checkout form clear edge for selection.",
            },
            "ranking_strength": {
                "filled": True,
                "strength": 0.6,
                "note": "Higher seed; ranking gap supports ML favourite.",
            },
            "h2h_matchup": {
                "filled": True,
                "strength": 0.6,
                "note": "H2H 3-1 last four meetings favour selection side.",
            },
            "recent_form": {
                "filled": True,
                "strength": 0.7,
                "note": "Won last three TV matches at elevated average.",
            },
        },
    }
    sc = score_evidence(
        pack, sport="darts", selection="Vinner: A", odds=1.95, card=card
    )
    assert "checkout_scoring" in sc.filled_slots
    assert "ranking_seed" in sc.filled_slots or "h2h_matchup" in sc.filled_slots


def test_new_sport_auto_card(tmp_path: Path):
    """Unknown sport: scaffold/ensure may write; grade uses in-memory quarantine only."""
    cfg = _cfg(shadow_mode=False, forced_hierarchy={"enabled": True})
    cfg["selection"]["evidence"]["sport_cards_dir"] = str(tmp_path / "cards")
    from nt.evidence_hierarchy.cards import ensure_sport_card, sport_card_path
    from nt.evidence_hierarchy.score import score_evidence

    # Explicit onboard write (scaffold path) still works
    card, created = ensure_sport_card("curling", cfg, auto_create=True)
    assert created is True
    assert card is not None
    assert card.onboarded is False
    path = sport_card_path("curling", cfg)
    assert path.is_file()

    # score_evidence must not write for a different unknown sport
    other_dir = tmp_path / "cards"
    before = {p.name for p in other_dir.glob("*.yaml")}
    sc = score_evidence(
        {
            "summary": "In-memory quarantine score for unmapped sport only.",
            "sources": _quality_sources(4, "flashscore.com"),
            "h2h": {"checked": True, "edge": 0.1, "summary": "H2H leads 2-1 recently."},
        },
        sport="kabaddi",
        selection="Team A to Win",
        odds=1.95,
        cfg=cfg,
    )
    after = {p.name for p in other_dir.glob("*.yaml")}
    assert after == before, "score_evidence must not write sport cards"
    assert sc.onboarded is False
    assert "HR_SPORT_UNKNOWN" in sc.hard_rejects

    pack = {
        "sport": "curling",
        "summary": "Some summary text that is long enough for core reason check.",
        "failure_modes": "ice conditions",
        "p_model": 0.55,
        "sources": _quality_sources(5, "flashscore.com"),
        "h2h": {"checked": True, "edge": 0.1, "summary": "H2H leads 2-1 recently."},
    }
    grade, issues = grade_evidence(
        pack, cfg, 1.95, selection="Team A to Win", sport="curling"
    )
    assert grade in ("F", "C")
    assert any("SPORT_UNKNOWN" in i or "saef:HR_SPORT" in i for i in issues) or grade == "F"


def test_scaffold_emits_signals_and_h2h(tmp_path: Path):
    cfg = {
        "paths": {"evidence": str(tmp_path)},
        "selection": {"evidence": {"auto_onboard_cards": True}},
    }
    out = scaffold_evidence(
        cfg,
        match="A vs B",
        selection="Vinner: A",
        sport="esports",
        p_model=None,
        write=False,
    )
    pack = out["pack"]
    assert pack["sport"] == "esports"
    assert "h2h" in pack
    assert pack["h2h"].get("checked") is False
    assert isinstance(pack.get("signals"), dict)
    assert pack["signals"], "expected signal stubs from sport card"
    urls = " ".join(s.get("url", "") for s in pack["sources"]).lower()
    assert "fbref" not in urls


def test_score_evidence_pure():
    card = load_sport_card("football")
    assert card
    pack = {
        "summary": "xG form edge with confirmed lineup and positive H2H for home ML.",
        "sources": _quality_sources(5, "fbref.com"),
        "h2h": {"checked": True, "edge": 0.1, "summary": "H2H 3-1 last meetings home."},
        "signals": {
            "xg_form": {
                "filled": True,
                "strength": 0.8,
                "note": "xG form last 8 matches clearly above opponent average.",
            },
            "availability": {
                "filled": True,
                "strength": 0.7,
                "note": "Full strength XI expected; no key absences reported.",
            },
            "h2h_matchup": {
                "filled": True,
                "strength": 0.6,
                "note": "H2H 3-1 last four home meetings favour selection.",
            },
        },
        "script_lean": "one_sided",
        "selection_vs_script": "agree",
    }
    sc = score_evidence(
        pack, sport="football", selection="Home to Win", odds=1.95, card=card
    )
    assert sc.E > 0.3
    assert sc.quality_source_count >= 4
