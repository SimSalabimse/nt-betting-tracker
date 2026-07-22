from __future__ import annotations

"""
Football match simulation for p_model support (optional research tool).

Model
-----
Independent Poisson scorelines with optional Dixon–Coles low-score correction
(rho). Inputs are expected goals (λ_home, λ_away), either entered directly or
derived from simple xG for/against + home advantage.

Philosophy
----------
- Output is a *suggested* p_model and failure modes for evidence packs.
- Never places bets, never bypasses haircut / EV / phase / risk.
- Garbage-in warnings are first-class: missing quality inputs → lower confidence.

Not a multi-sport simulator. Extend only after calibration proves value.
"""

import json
import math
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from nt.bets_io import utc_now
from nt.config import path_from_config
from nt.defaults import simulation_cfg
from nt.evidence import ev_after_haircut


def _fact(n: int) -> float:
    return float(math.factorial(n))


def poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam**k) / _fact(k)


def dixon_coles_tau(i: int, j: int, lam_h: float, lam_a: float, rho: float) -> float:
    """Dixon–Coles correction for low-scoring outcomes (0-0, 1-0, 0-1, 1-1)."""
    if i == 0 and j == 0:
        return 1.0 - lam_h * lam_a * rho
    if i == 0 and j == 1:
        return 1.0 + lam_h * rho
    if i == 1 and j == 0:
        return 1.0 + lam_a * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


@dataclass
class SimInputs:
    """Required-ish inputs for a transparent football sim."""

    match: str = ""
    home: str = ""
    away: str = ""
    # Direct expected goals (preferred if known)
    lambda_home: float | None = None
    lambda_away: float | None = None
    # Or xG building blocks
    home_xg_for: float | None = None
    home_xg_against: float | None = None
    away_xg_for: float | None = None
    away_xg_against: float | None = None
    league_avg_xg: float = 1.35
    home_advantage: float = 1.08
    # Soft multipliers (1.0 = neutral). Document why you changed them.
    form_home: float = 1.0
    form_away: float = 1.0
    motivation_home: float = 1.0
    motivation_away: float = 1.0
    rest_home: float = 1.0  # <1 if short rest
    rest_away: float = 1.0
    injury_home: float = 1.0  # <1 if key attackers out
    injury_away: float = 1.0
    # Dixon–Coles
    rho: float = -0.05
    max_goals: int = 10
    # Meta
    league: str = ""
    notes: str = ""
    source_quality: str = "medium"  # low | medium | high


@dataclass
class MarketProb:
    market: str
    selection_hint: str
    p_model: float
    implied_fair_odds: float
    notes: str = ""


@dataclass
class SimResult:
    match: str
    home: str
    away: str
    lambda_home: float
    lambda_away: float
    rho: float
    model: str
    markets: dict[str, float]
    market_rows: list[MarketProb]
    top_scores: list[dict[str, Any]]
    expected_goals_total: float
    p_btts: float
    confidence: str
    warnings: list[str]
    failure_modes: str
    summary: str
    evidence_snippet: dict[str, Any]
    inputs: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""

    def p(self, key: str) -> float | None:
        return self.markets.get(key)


def resolve_lambdas(inp: SimInputs, cfg: dict[str, Any] | None = None) -> tuple[float, float, list[str]]:
    """Derive λ_home, λ_away and quality warnings."""
    sc = simulation_cfg(cfg or {})
    warnings: list[str] = []
    league_avg = float(inp.league_avg_xg or sc.get("default_league_avg_xg", 1.35))
    home_adv = float(inp.home_advantage or sc.get("default_home_advantage", 1.08))

    if inp.lambda_home is not None and inp.lambda_away is not None:
        lh = float(inp.lambda_home)
        la = float(inp.lambda_away)
        if lh < 0.2 or la < 0.2 or lh > 4.5 or la > 4.5:
            warnings.append("lambda outside typical 0.2–4.5 range — double-check inputs")
    else:
        # Attack/defence strength style from xG
        hxg_f = inp.home_xg_for
        hxg_a = inp.home_xg_against
        axg_f = inp.away_xg_for
        axg_a = inp.away_xg_against
        missing = [n for n, v in [
            ("home_xg_for", hxg_f),
            ("home_xg_against", hxg_a),
            ("away_xg_for", axg_f),
            ("away_xg_against", axg_a),
        ] if v is None]
        if missing:
            # Fallback: if only for-rates given
            if hxg_f is not None and axg_f is not None and hxg_a is None and axg_a is None:
                warnings.append("only attack xG provided — using league_avg for defence (weaker model)")
                hxg_a = league_avg
                axg_a = league_avg
            else:
                raise ValueError(
                    "Need lambda_home & lambda_away OR home/away xG for+against. "
                    f"Missing: {missing}"
                )
        assert hxg_f is not None and hxg_a is not None and axg_f is not None and axg_a is not None
        # Expected home goals ~ home attack * away defence / league * HFA
        lh = (float(hxg_f) * float(axg_a) / league_avg) * home_adv
        la = (float(axg_f) * float(hxg_a) / league_avg)
        warnings.append("lambdas derived from xG for/against — verify sample sizes on FBref")

    # Soft multipliers
    lh *= float(inp.form_home) * float(inp.motivation_home) * float(inp.rest_home) * float(inp.injury_home)
    la *= float(inp.form_away) * float(inp.motivation_away) * float(inp.rest_away) * float(inp.injury_away)

    # Floor/ceil for numerical stability
    lh = max(0.05, min(5.0, lh))
    la = max(0.05, min(5.0, la))

    if inp.source_quality == "low":
        warnings.append("source_quality=low — treat p_model as exploratory only")
    if abs(float(inp.form_home) - 1.0) > 0.25 or abs(float(inp.form_away) - 1.0) > 0.25:
        warnings.append("large form multipliers — document justification in evidence")
    if abs(float(inp.injury_home) - 1.0) > 0.2 or abs(float(inp.injury_away) - 1.0) > 0.2:
        warnings.append("large injury multipliers — confirm lineups before placing")

    return lh, la, warnings


def score_matrix(
    lam_h: float,
    lam_a: float,
    *,
    rho: float = -0.05,
    max_goals: int = 10,
) -> list[list[float]]:
    """P(home_goals=i, away_goals=j) with optional Dixon–Coles tau."""
    raw: list[list[float]] = []
    total = 0.0
    for i in range(max_goals + 1):
        row: list[float] = []
        for j in range(max_goals + 1):
            p = poisson_pmf(i, lam_h) * poisson_pmf(j, lam_a)
            p *= dixon_coles_tau(i, j, lam_h, lam_a, rho)
            p = max(0.0, p)
            row.append(p)
            total += p
        raw.append(row)
    # Renormalize (DC can shift mass slightly)
    if total <= 0:
        raise ValueError("degenerate score matrix")
    return [[p / total for p in row] for row in raw]


def markets_from_matrix(mat: list[list[float]]) -> dict[str, float]:
    n = len(mat)
    p_home = p_draw = p_away = 0.0
    p_over_05 = p_over_15 = p_over_25 = p_over_35 = 0.0
    p_btts_y = 0.0
    p_home_or_draw = p_away_or_draw = 0.0

    for i in range(n):
        for j in range(n):
            p = mat[i][j]
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
            total_g = i + j
            if total_g >= 1:
                p_over_05 += p
            if total_g >= 2:
                p_over_15 += p
            if total_g >= 3:
                p_over_25 += p
            if total_g >= 4:
                p_over_35 += p
            if i >= 1 and j >= 1:
                p_btts_y += p
            if i >= j:
                p_home_or_draw += p
            if j >= i:
                p_away_or_draw += p

    # DNB: conditional on not draw
    p_not_draw = p_home + p_away
    p_dnb_home = (p_home / p_not_draw) if p_not_draw > 1e-12 else 0.5
    p_dnb_away = (p_away / p_not_draw) if p_not_draw > 1e-12 else 0.5

    return {
        "home_win": round(p_home, 6),
        "draw": round(p_draw, 6),
        "away_win": round(p_away, 6),
        "over_0.5": round(p_over_05, 6),
        "under_0.5": round(1.0 - p_over_05, 6),
        "over_1.5": round(p_over_15, 6),
        "under_1.5": round(1.0 - p_over_15, 6),
        "over_2.5": round(p_over_25, 6),
        "under_2.5": round(1.0 - p_over_25, 6),
        "over_3.5": round(p_over_35, 6),
        "under_3.5": round(1.0 - p_over_35, 6),
        "btts_yes": round(p_btts_y, 6),
        "btts_no": round(1.0 - p_btts_y, 6),
        "dnb_home": round(p_dnb_home, 6),
        "dnb_away": round(p_dnb_away, 6),
        "double_chance_1x": round(p_home_or_draw, 6),
        "double_chance_x2": round(p_away_or_draw, 6),
        "double_chance_12": round(p_home + p_away, 6),
    }


def top_scorelines(mat: list[list[float]], k: int = 8) -> list[dict[str, Any]]:
    scores: list[tuple[float, int, int]] = []
    for i, row in enumerate(mat):
        for j, p in enumerate(row):
            scores.append((p, i, j))
    scores.sort(reverse=True)
    return [{"score": f"{i}-{j}", "p": round(p, 5)} for p, i, j in scores[:k]]


def _confidence(inp: SimInputs, warnings: list[str]) -> str:
    if inp.source_quality == "low" or len(warnings) >= 3:
        return "low"
    if inp.source_quality == "high" and not any("only attack" in w for w in warnings):
        return "high"
    return "medium"


def _failure_modes(lam_h: float, lam_a: float, markets: dict[str, float]) -> str:
    bits = [
        f"Model λ=({lam_h:.2f},{lam_a:.2f}); variance high in knockout/cup.",
        "Red card / early goal flips script vs Poisson independence.",
        "xG sample noise; lineup late changes; weather/pitch.",
    ]
    if markets.get("under_2.5", 0) > 0.55:
        bits.append("Under lean: risk of open game if both chase.")
    if markets.get("over_2.5", 0) > 0.55:
        bits.append("Over lean: risk of cagey first half / parking bus.")
    if markets.get("btts_yes", 0) > 0.55:
        bits.append("BTTS yes: clean-sheet specialist or deep block fails model.")
    return " ".join(bits)


def _summary(inp: SimInputs, lam_h: float, lam_a: float, markets: dict[str, float], conf: str) -> str:
    home = inp.home or "Home"
    away = inp.away or "Away"
    return (
        f"Football Poisson/DC sim for {inp.match or f'{home} vs {away}'}: "
        f"λ_home={lam_h:.2f}, λ_away={lam_a:.2f}. "
        f"1X2 ≈ {markets['home_win']:.1%}/{markets['draw']:.1%}/{markets['away_win']:.1%}; "
        f"O2.5={markets['over_2.5']:.1%}, BTTS_Y={markets['btts_yes']:.1%}. "
        f"Confidence={conf}. NOT ground truth — feed evidence after human review."
    )


def simulate_match(inp: SimInputs, cfg: dict[str, Any] | None = None) -> SimResult:
    sc = simulation_cfg(cfg or {})
    if not sc.get("enabled", True):
        raise RuntimeError("simulation.football disabled in config (simulation.enabled=false)")

    rho = float(inp.rho if inp.rho is not None else sc.get("default_rho", -0.05))
    max_g = int(inp.max_goals or sc.get("max_goals", 10))
    lam_h, lam_a, warnings = resolve_lambdas(inp, cfg)
    mat = score_matrix(lam_h, lam_a, rho=rho, max_goals=max_g)
    markets = markets_from_matrix(mat)
    conf = _confidence(inp, warnings)

    home = inp.home or (inp.match.split(" vs ")[0].strip() if " vs " in (inp.match or "") else "Home")
    away = inp.away or (
        inp.match.split(" vs ")[1].strip() if " vs " in (inp.match or "") else "Away"
    )
    match = inp.match or f"{home} vs {away}"

    rows = [
        MarketProb("1X2", f"{home} to Win", markets["home_win"], round(1.0 / markets["home_win"], 3) if markets["home_win"] > 0 else 99.0),
        MarketProb("1X2", "Uavgjort", markets["draw"], round(1.0 / markets["draw"], 3) if markets["draw"] > 0 else 99.0),
        MarketProb("1X2", f"{away} to Win", markets["away_win"], round(1.0 / markets["away_win"], 3) if markets["away_win"] > 0 else 99.0),
        MarketProb("OU", "Over 2.5", markets["over_2.5"], round(1.0 / markets["over_2.5"], 3)),
        MarketProb("OU", "Under 2.5", markets["under_2.5"], round(1.0 / markets["under_2.5"], 3)),
        MarketProb("OU", "Over 1.5", markets["over_1.5"], round(1.0 / markets["over_1.5"], 3)),
        MarketProb("OU", "Under 3.5", markets["under_3.5"], round(1.0 / markets["under_3.5"], 3)),
        MarketProb("BTTS", "BTTS Ja", markets["btts_yes"], round(1.0 / markets["btts_yes"], 3)),
        MarketProb("BTTS", "BTTS Nei", markets["btts_no"], round(1.0 / markets["btts_no"], 3)),
        MarketProb("DNB", f"DNB {home}", markets["dnb_home"], round(1.0 / markets["dnb_home"], 3)),
        MarketProb("DNB", f"DNB {away}", markets["dnb_away"], round(1.0 / markets["dnb_away"], 3)),
    ]

    # Map selection hints to NT-style strings for evidence
    nt_map = {
        "home_win": f"{home} to Win",
        "draw": "Uavgjort",
        "away_win": f"{away} to Win",
        "over_2.5": "Totalt antall mål - Over/Under 2.5: Over 2.5",
        "under_2.5": "Totalt antall mål - Over/Under 2.5: Under 2.5",
        "over_1.5": "Totalt antall mål - Over/Under 1.5: Over 1.5",
        "under_1.5": "Totalt antall mål - Over/Under 1.5: Under 1.5",
        "over_3.5": "Totalt antall mål - Over/Under 3.5: Over 3.5",
        "under_3.5": "Totalt antall mål - Over/Under 3.5: Under 3.5",
        "btts_yes": "BTTS Ja",
        "btts_no": "BTTS Nei",
    }

    evidence_snippet = {
        "match": match,
        "model_name": "nt_football_poisson_dc",
        "model_version": "1.0",
        "sim_lambda_home": round(lam_h, 4),
        "sim_lambda_away": round(lam_a, 4),
        "sim_rho": rho,
        "sim_confidence": conf,
        "sim_markets": {k: markets[k] for k in (
            "home_win", "draw", "away_win", "over_2.5", "under_2.5", "btts_yes", "btts_no"
        )},
        "sim_warnings": warnings,
        "disclaimer": "Simulation is not ground truth. Human research still required.",
    }

    return SimResult(
        match=match,
        home=home,
        away=away,
        lambda_home=round(lam_h, 4),
        lambda_away=round(lam_a, 4),
        rho=rho,
        model="poisson_dixon_coles",
        markets=markets,
        market_rows=rows,
        top_scores=top_scorelines(mat),
        expected_goals_total=round(lam_h + lam_a, 4),
        p_btts=markets["btts_yes"],
        confidence=conf,
        warnings=warnings,
        failure_modes=_failure_modes(lam_h, lam_a, markets),
        summary=_summary(inp, lam_h, lam_a, markets, conf),
        evidence_snippet=evidence_snippet,
        inputs={
            "lambda_home_in": inp.lambda_home,
            "lambda_away_in": inp.lambda_away,
            "home_xg_for": inp.home_xg_for,
            "home_xg_against": inp.home_xg_against,
            "away_xg_for": inp.away_xg_for,
            "away_xg_against": inp.away_xg_against,
            "multipliers": {
                "form_home": inp.form_home,
                "form_away": inp.form_away,
                "motivation_home": inp.motivation_home,
                "motivation_away": inp.motivation_away,
                "rest_home": inp.rest_home,
                "rest_away": inp.rest_away,
                "injury_home": inp.injury_home,
                "injury_away": inp.injury_away,
            },
            "source_quality": inp.source_quality,
            "league": inp.league,
            "nt_selection_map": nt_map,
        },
        generated_at=utc_now(),
    )


def p_model_for_selection(result: SimResult, selection: str) -> float | None:
    """Map NT selection text to sim market probability."""
    s = (selection or "").lower()
    m = result.markets
    home_l = result.home.lower()
    away_l = result.away.lower()

    if "btts" in s or "begge lag" in s:
        if "nei" in s or "no" in s:
            return m["btts_no"]
        return m["btts_yes"]
    if "over 2.5" in s or ("over/under 2.5" in s and "over" in s.split(":")[-1]):
        return m["over_2.5"]
    if "under 2.5" in s or ("over/under 2.5" in s and "under" in s.split(":")[-1]):
        return m["under_2.5"]
    if "over 1.5" in s:
        return m["over_1.5"]
    if "under 1.5" in s:
        return m["under_1.5"]
    if "over 3.5" in s:
        return m["over_3.5"]
    if "under 3.5" in s:
        return m["under_3.5"]
    if s.strip() == "uavgjort" or s == "draw":
        return m["draw"]
    if "tilbakebetales" in s or "dnb" in s:
        if home_l and home_l.split()[0] in s:
            return m["dnb_home"]
        if away_l and away_l.split()[0] in s:
            return m["dnb_away"]
        if result.home.lower() in s:
            return m["dnb_home"]
        if result.away.lower() in s:
            return m["dnb_away"]
    if "to win" in s or s.startswith("vinner"):
        if home_l and any(t in s for t in home_l.replace(",", " ").split() if len(t) > 2):
            # prefer longer token match
            if home_l in s or home_l.split()[0] in s:
                return m["home_win"]
        if away_l and (away_l in s or any(t in s for t in away_l.replace(",", " ").split() if len(t) > 2)):
            return m["away_win"]
        # "Home to Win" pattern
        if result.home.lower() in s:
            return m["home_win"]
        if result.away.lower() in s:
            return m["away_win"]
    return None


def render_sim_markdown(result: SimResult, cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or {}
    haircut = float((cfg.get("selection") or {}).get("probability_haircut", 0.05))
    lines = [
        f"# Football simulation — {result.match}",
        "",
        f"**Model:** `{result.model}` · λ_home=**{result.lambda_home}** · λ_away=**{result.lambda_away}** · ρ={result.rho}",
        f"**Confidence:** {result.confidence} · Generated: {result.generated_at}",
        "",
        "> ⚠️ Simulation is **not** ground truth. Use as input to evidence + honest p_model. "
        "Engine haircut/EV/phase still apply.",
        "",
        "## Warnings",
    ]
    if result.warnings:
        for w in result.warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- (none)")

    lines.extend(
        [
            "",
            "## Market probabilities (raw model)",
            "",
            "| Market | p_model | Fair odds |",
            "|--------|---------|-----------|",
        ]
    )
    for row in result.market_rows:
        lines.append(f"| {row.selection_hint} | {row.p_model:.3f} | {row.implied_fair_odds:.2f} |")

    lines.extend(["", "## Top scorelines", ""])
    for sc in result.top_scores:
        lines.append(f"- {sc['score']}: {sc['p']:.1%}")

    lines.extend(
        [
            "",
            "## Suggested failure modes",
            "",
            result.failure_modes,
            "",
            "## Summary (paste into evidence)",
            "",
            result.summary,
            "",
            "## EV helper (after system haircut)",
            "",
            f"Haircut = {haircut:.0%} (from config). Example O2.5 vs odds 2.25:",
        ]
    )
    p_o = result.markets["over_2.5"]
    ev_ex = ev_after_haircut(p_o, 2.25, haircut)
    lines.append(f"- p_model={p_o:.3f} → EV@2.25 ≈ **{ev_ex:+.3f}** (still need grade B evidence)")
    lines.extend(
        [
            "",
            "## Next steps",
            "",
            "1. Review inputs and warnings",
            "2. Copy p_model for chosen selection into `evidence/*.json`",
            "3. Add real sources (FBref, Transfermarkt, …)",
            "4. `research ready` → `recommend`",
            "",
        ]
    )
    return "\n".join(lines)


def result_to_dict(result: SimResult) -> dict[str, Any]:
    d = asdict(result)
    d["market_rows"] = [asdict(m) for m in result.market_rows]
    return d


def write_evidence_from_sim(
    cfg: dict[str, Any],
    result: SimResult,
    *,
    selection: str,
    p_model: float | None = None,
    decimal_odds: float | None = None,
    filename: str | None = None,
) -> Path:
    """Write/merge an evidence pack seeded from simulation (still needs sources filled)."""
    p = p_model if p_model is not None else p_model_for_selection(result, selection)
    if p is None:
        raise ValueError(f"Could not map selection to sim market: {selection!r}")

    evidence_dir = path_from_config(cfg, "evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    if not filename:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in f"{result.match}_{selection}")[:70]
        filename = safe.lower() + ".json"
    path = evidence_dir / filename

    pack: dict[str, Any] = {
        "match": result.match,
        "selection": selection,
        "league": (result.inputs or {}).get("league") or "",
        "sport": "football",
        "p_model": round(float(p), 4),
        "summary": result.summary,
        "failure_modes": result.failure_modes,
        "model_name": "nt_football_poisson_dc",
        "model_version": "1.0",
        "sim": result.evidence_snippet,
        "confidence": {"low": 2, "medium": 3, "high": 4}.get(result.confidence, 3),
        "sources": [
            {
                "url": "https://fbref.com",
                "kind": "stats",
                "takeaway": "TODO: paste xG / form takeaway used for λ inputs",
            },
            {
                "url": "https://www.transfermarkt.com",
                "kind": "injury",
                "takeaway": "TODO: injuries/suspensions",
            },
            {
                "url": "https://www.sofascore.com",
                "kind": "lineup",
                "takeaway": "TODO: lineup confirmation",
            },
            {
                "url": "https://www.flashscore.com",
                "kind": "stats",
                "takeaway": "TODO: H2H / context",
            },
            {
                "url": "nt://simulate",
                "kind": "model",
                "takeaway": (
                    f"Poisson/DC λ=({result.lambda_home},{result.lambda_away}) "
                    f"p={float(p):.3f} conf={result.confidence}"
                ),
            },
            {
                "url": "https://www.soccerstats.com",
                "kind": "stats",
                "takeaway": "TODO: optional BTTS/OU tables",
            },
        ],
        "notes": (
            "Simulation-seeded pack. Replace TODO takeaways. "
            "Do not treat sim as sole evidence."
        ),
    }
    # HV v3: dual-write odds snapshot; mark inferred until human sources filled
    from nt.pack_freshness import apply_odds_snapshot_fields

    apply_odds_snapshot_fields(
        pack,
        float(decimal_odds) if decimal_odds is not None else None,
        stamp_researched_at=True,
        inferred=True if decimal_odds is not None else None,
    )

    path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_sim_input_file(path: Path) -> SimInputs:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        import yaml

        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("sim input must be a mapping")
    # allow nested "inputs" key
    if "inputs" in data and isinstance(data["inputs"], dict):
        data = {**data, **data["inputs"]}
    known = {f.name for f in fields(SimInputs)}
    kwargs = {k: v for k, v in data.items() if k in known}
    return SimInputs(**kwargs)


def save_sim_audit(cfg: dict[str, Any], result: SimResult) -> Path | None:
    """Append sim run to audit jsonl (optional transparency)."""
    sc = simulation_cfg(cfg)
    if not sc.get("audit_sims", True):
        return None
    path = path_from_config(cfg, "state_dir") / "sim_audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": result.generated_at or utc_now(),
        "match": result.match,
        "lambda_home": result.lambda_home,
        "lambda_away": result.lambda_away,
        "markets": {
            k: result.markets[k]
            for k in ("home_win", "draw", "away_win", "over_2.5", "under_2.5", "btts_yes")
        },
        "confidence": result.confidence,
        "warnings": result.warnings,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path
