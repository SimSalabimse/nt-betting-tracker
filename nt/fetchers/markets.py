from __future__ import annotations

"""
Map final scores → bet outcomes for common markets across sports.
"""

import re
from typing import Any

from nt.fetchers.base import MatchResult, SelectionVerdict
from nt.fetchers.names import name_match_score, norm_name


def evaluate_selection_from_score(
    selection: str,
    home: str,
    away: str,
    home_goals: int | float,
    away_goals: int | float,
    *,
    market_type: str = "",
    sport: str = "football",
) -> dict[str, Any]:
    """Legacy-compatible dict API used by tests / scripts."""
    result = MatchResult(
        home=home,
        away=away,
        home_score=home_goals,
        away_score=away_goals,
        score_text=f"{home_goals}-{away_goals}",
        finished=True,
        match_confidence=1.0,
        source="direct",
    )
    v = evaluate_for_sport(sport, selection, result, market_type=market_type)
    return v.to_dict()


def evaluate_for_sport(
    sport: str,
    selection: str,
    result: MatchResult,
    *,
    market_type: str = "",
) -> SelectionVerdict:
    s = (sport or "football").lower()
    if s in ("tennis", "tns"):
        return evaluate_tennis_selection(selection, result, market_type=market_type)
    if s in ("basketball", "nba", "wnba", "bsk"):
        return evaluate_basketball_selection(selection, result, market_type=market_type)
    if s in ("handball", "hbl"):
        return evaluate_football_like_selection(
            selection, result, market_type=market_type, sport_label="handball"
        )
    if s in ("darts", "dar"):
        return evaluate_match_winner_only(selection, result)
    # football / soccer / default goal sports
    return evaluate_football_like_selection(
        selection, result, market_type=market_type, sport_label="football"
    )


def evaluate_football_like_selection(
    selection: str,
    result: MatchResult,
    *,
    market_type: str = "",
    sport_label: str = "football",
) -> SelectionVerdict:
    home = result.home
    away = result.away
    if result.home_score is None or result.away_score is None:
        return SelectionVerdict(None, 0.0, "Missing numeric score")
    home_goals = float(result.home_score)
    away_goals = float(result.away_score)
    # Prefer ints for goals
    hg, ag = int(home_goals), int(away_goals)

    sel = (selection or "").strip()
    sel_l = sel.lower()
    total = hg + ag
    mt = (market_type or "").lower()

    # Totals O/U
    m_ou = re.search(r"(over|under)\s*(\d+(?:[.,]\d+)?)", sel_l)
    if not m_ou:
        m_ou = re.search(r"\b(o|u)\s*(\d+(?:[.,]\d+)?)", sel_l)
    if m_ou or "over/under" in sel_l or "totalt" in sel_l or "o/u" in sel_l:
        line = None
        side = None
        if m_ou:
            side = "over" if m_ou.group(1).startswith("o") else "under"
            line = float(m_ou.group(2).replace(",", "."))
        else:
            m2 = re.search(r"(\d+(?:[.,]\d+)?)", sel_l)
            if m2:
                line = float(m2.group(1).replace(",", "."))
            if "over" in sel_l:
                side = "over"
            elif "under" in sel_l:
                side = "under"
        if side and line is not None:
            if abs(total - line) < 1e-9:
                outcome = "push"
            elif side == "over":
                outcome = "win" if total > line else "loss"
            else:
                outcome = "win" if total < line else "loss"
            return SelectionVerdict(
                outcome,
                0.92,
                f"Score {hg}-{ag} total={total} vs {side} {line}",
            )

    # BTTS
    if "btts" in sel_l or "begge lag" in sel_l or "both teams" in sel_l:
        btts = hg > 0 and ag > 0
        wants_yes = True
        if "nei" in sel_l or re.search(r"\bno\b", sel_l) or "ingen" in sel_l:
            wants_yes = False
        if "ja" in sel_l or "yes" in sel_l:
            wants_yes = True
        outcome = "win" if (btts == wants_yes) else "loss"
        return SelectionVerdict(
            outcome,
            0.9,
            f"BTTS actual={btts} wanted_yes={wants_yes} ({hg}-{ag})",
        )

    # Double chance / DNB light
    if "dnb" in sel_l or "tilbakebetales" in sel_l or "draw no bet" in sel_l:
        side = _side_from_selection(sel, home, away)
        if hg == ag:
            return SelectionVerdict("push", 0.88, f"DNB push draw {hg}-{ag}")
        if side == "home":
            return SelectionVerdict(
                "win" if hg > ag else "loss", 0.88, f"DNB home ({hg}-{ag})"
            )
        if side == "away":
            return SelectionVerdict(
                "win" if ag > hg else "loss", 0.88, f"DNB away ({hg}-{ag})"
            )

    # Handicap
    if "handikap" in sel_l or "handicap" in sel_l or re.search(r"[+-]\d", sel):
        m_hc = re.search(r"([+-]?\d+(?:[.,]\d+)?)\s*$", sel.replace("−", "-"))
        line = float(m_hc.group(1).replace(",", ".")) if m_hc else None
        side = _side_from_selection(sel, home, away)
        if side and line is not None:
            # 3-way style integer lines common on NT
            if side == "home":
                margin = hg - ag
                adj = margin + line  # home -1 → line=-1; need margin>=2 for win if 3-way
                # Asian-like continuous: adj > 0 win, 0 push, <0 loss
                # For integer 3-way -1: win by 2+ = win, win by 1 = push-ish
                if abs(line - int(line)) < 1e-9 and abs(line) >= 1:
                    # 3-way interpretation for whole numbers
                    if line < 0:
                        need = int(abs(line)) + 0  # -1 needs margin >= 2 for pure win
                        # standard 3-way: home -1 wins if margin >= 2; margin==1 is HC draw
                        thr = int(abs(round(line))) + 1 if line == -1 else int(abs(round(line)))
                        # simpler: apply line to home score
                        if margin > abs(line):
                            outcome = "win"
                        elif margin == abs(line) and line == -1:
                            outcome = "push"
                        elif margin == abs(line):
                            outcome = "push"
                        else:
                            outcome = "loss"
                    else:
                        # home +1
                        if margin + line > 0:
                            outcome = "win"
                        elif margin + line == 0:
                            outcome = "push"
                        else:
                            outcome = "loss"
                else:
                    if adj > 0:
                        outcome = "win"
                    elif adj == 0:
                        outcome = "push"
                    else:
                        outcome = "loss"
                return SelectionVerdict(
                    outcome,
                    0.75,
                    f"HC line {line} home margin {margin} ({hg}-{ag})",
                )
            if side == "away":
                margin = ag - hg
                if margin > abs(line) if line < 0 else margin + line > 0:
                    outcome = "win"
                elif (line < 0 and margin == abs(line)) or (line > 0 and margin + line == 0):
                    outcome = "push"
                else:
                    outcome = "loss"
                return SelectionVerdict(
                    outcome,
                    0.7,
                    f"HC away margin {margin} ({hg}-{ag})",
                )

    # Draw
    if "uavgjort" in sel_l or re.search(r"\bdraw\b", sel_l) or sel_l.strip() in ("x", "1x2 x"):
        outcome = "win" if hg == ag else "loss"
        return SelectionVerdict(outcome, 0.88, f"Draw market vs {hg}-{ag}")

    # Moneyline / Vinner
    if (
        "to win" in sel_l
        or "vinner" in sel_l
        or "hub" in mt
        or name_match_score(home, sel) >= 0.4
        or name_match_score(away, sel) >= 0.4
    ):
        if hg > ag:
            winner = "home"
        elif ag > hg:
            winner = "away"
        else:
            winner = "draw"
        side = _side_from_selection(sel, home, away)
        if side == "home":
            outcome = "win" if winner == "home" else "loss"
            return SelectionVerdict(
                outcome, 0.85, f"{home} ML vs {hg}-{ag} (winner={winner})"
            )
        if side == "away":
            outcome = "win" if winner == "away" else "loss"
            return SelectionVerdict(
                outcome, 0.85, f"{away} ML vs {hg}-{ag} (winner={winner})"
            )
        return SelectionVerdict(None, 0.0, "Could not map ML side from selection")

    return SelectionVerdict(
        None, 0.0, f"Market not auto-mappable for {sport_label} from score alone"
    )


def evaluate_tennis_selection(
    selection: str,
    result: MatchResult,
    *,
    market_type: str = "",
) -> SelectionVerdict:
    """Tennis: primarily match winner; optional set totals if set scores present."""
    home, away = result.home, result.away
    sel = (selection or "").strip()
    sel_l = sel.lower()

    # Winner
    side = _side_from_selection(sel, home, away)
    hs, aws = result.home_score, result.away_score

    # Set-based winner if scores are sets won
    if hs is not None and aws is not None:
        try:
            hsi, asi = int(hs), int(aws)
        except (TypeError, ValueError):
            hsi, asi = None, None
        if hsi is not None and ("vinner" in sel_l or "to win" in sel_l or "winner" in sel_l or side):
            if side == "home":
                outcome = "win" if hsi > asi else "loss"
                return SelectionVerdict(
                    outcome, 0.9, f"Tennis sets {hsi}-{asi} · pick {home}"
                )
            if side == "away":
                outcome = "win" if asi > hsi else "loss"
                return SelectionVerdict(
                    outcome, 0.9, f"Tennis sets {hsi}-{asi} · pick {away}"
                )
            # infer from selection name only
            if name_match_score(home, sel) >= name_match_score(away, sel):
                outcome = "win" if hsi > asi else "loss"
                return SelectionVerdict(outcome, 0.82, f"Tennis sets {hsi}-{asi} (home pick)")
            outcome = "win" if asi > hsi else "loss"
            return SelectionVerdict(outcome, 0.82, f"Tennis sets {hsi}-{asi} (away pick)")

        # Totals sets O/U 2.5
        m_ou = re.search(r"(over|under)\s*(\d+(?:[.,]\d+)?)", sel_l)
        if m_ou and hsi is not None:
            total = hsi + asi
            side_ou = "over" if m_ou.group(1).startswith("o") else "under"
            line = float(m_ou.group(2).replace(",", "."))
            if side_ou == "over":
                outcome = "win" if total > line else "loss"
            else:
                outcome = "win" if total < line else "loss"
            return SelectionVerdict(
                outcome, 0.85, f"Sets total {total} vs {side_ou} {line}"
            )

    # Winner without scores — use extras winner flag
    winner_name = (result.extras or {}).get("winner")
    if winner_name:
        if name_match_score(str(winner_name), home) >= 0.5:
            wside = "home"
        elif name_match_score(str(winner_name), away) >= 0.5:
            wside = "away"
        else:
            wside = None
        side = side or _side_from_selection(sel, home, away)
        if side and wside:
            outcome = "win" if side == wside else "loss"
            return SelectionVerdict(
                outcome, 0.8, f"Winner reported: {winner_name}"
            )

    return SelectionVerdict(None, 0.0, "Tennis market not mappable from available data")


def evaluate_basketball_selection(
    selection: str,
    result: MatchResult,
    *,
    market_type: str = "",
) -> SelectionVerdict:
    """Basketball ML, totals, spread."""
    if result.home_score is None or result.away_score is None:
        return SelectionVerdict(None, 0.0, "Missing basketball score")
    hg, ag = float(result.home_score), float(result.away_score)
    home, away = result.home, result.away
    sel = (selection or "").strip()
    sel_l = sel.lower()
    total = hg + ag

    m_ou = re.search(r"(over|under)\s*(\d+(?:[.,]\d+)?)", sel_l)
    if m_ou or "totalt" in sel_l or "over/under" in sel_l:
        if m_ou:
            side = "over" if m_ou.group(1).startswith("o") else "under"
            line = float(m_ou.group(2).replace(",", "."))
        else:
            m2 = re.search(r"(\d+(?:[.,]\d+)?)", sel_l)
            line = float(m2.group(1).replace(",", ".")) if m2 else None
            side = "over" if "over" in sel_l else "under" if "under" in sel_l else None
        if side and line is not None:
            if abs(total - line) < 1e-6:
                outcome = "push"
            elif side == "over":
                outcome = "win" if total > line else "loss"
            else:
                outcome = "win" if total < line else "loss"
            return SelectionVerdict(
                outcome, 0.9, f"BB total {total:.0f} vs {side} {line}"
            )

    # Spread / handicap
    m_hc = re.search(r"([+-]\d+(?:[.,]\d+)?)", sel.replace("−", "-"))
    if m_hc and ("handikap" in sel_l or "handicap" in sel_l or "spread" in sel_l or "±" in sel or True):
        line = float(m_hc.group(1).replace(",", "."))
        side = _side_from_selection(sel, home, away)
        if side == "home":
            adj = (hg - ag) + line
            outcome = "win" if adj > 0 else "push" if adj == 0 else "loss"
            return SelectionVerdict(outcome, 0.82, f"Home spread {line} margin {hg-ag:.0f}")
        if side == "away":
            adj = (ag - hg) + abs(line) if line < 0 else (ag - hg) + line
            # cleaner: away +X means away gets points
            if line > 0:
                adj = (ag + line) - hg
            else:
                adj = ag - (hg + abs(line))
            outcome = "win" if adj > 0 else "push" if adj == 0 else "loss"
            return SelectionVerdict(outcome, 0.8, f"Away spread line {line}")

    # ML
    side = _side_from_selection(sel, home, away)
    if side == "home" or "vinner" in sel_l or "to win" in sel_l:
        if side == "home" or name_match_score(home, sel) >= name_match_score(away, sel):
            outcome = "win" if hg > ag else "loss"
            return SelectionVerdict(outcome, 0.88, f"BB ML home {hg:.0f}-{ag:.0f}")
        outcome = "win" if ag > hg else "loss"
        return SelectionVerdict(outcome, 0.88, f"BB ML away {hg:.0f}-{ag:.0f}")
    if side == "away":
        outcome = "win" if ag > hg else "loss"
        return SelectionVerdict(outcome, 0.88, f"BB ML away {hg:.0f}-{ag:.0f}")

    return SelectionVerdict(None, 0.0, "Basketball market not mappable")


def evaluate_match_winner_only(
    selection: str,
    result: MatchResult,
) -> SelectionVerdict:
    side = _side_from_selection(selection, result.home, result.away)
    hs, aws = result.home_score, result.away_score
    if hs is None or aws is None:
        winner = (result.extras or {}).get("winner")
        if winner and side:
            w_home = name_match_score(str(winner), result.home) >= 0.5
            outcome = "win" if (side == "home" and w_home) or (side == "away" and not w_home) else "loss"
            return SelectionVerdict(outcome, 0.75, f"Winner={winner}")
        return SelectionVerdict(None, 0.0, "No score/winner for match")
    if side == "home":
        return SelectionVerdict(
            "win" if float(hs) > float(aws) else "loss",
            0.85,
            f"ML {hs}-{aws}",
        )
    if side == "away":
        return SelectionVerdict(
            "win" if float(aws) > float(hs) else "loss",
            0.85,
            f"ML {hs}-{aws}",
        )
    return SelectionVerdict(None, 0.0, "Could not determine side")


def _side_from_selection(selection: str, home: str, away: str) -> str | None:
    sel = selection or ""
    # Explicit handicap tokens like "Viking -1"
    home_sc = name_match_score(home, sel)
    away_sc = name_match_score(away, sel)
    # Also check first significant token of each name
    if home_sc < 0.35 and home:
        first = norm_name(home).split()[0] if norm_name(home) else ""
        if first and first in norm_name(sel):
            home_sc = max(home_sc, 0.55)
    if away_sc < 0.35 and away:
        first = norm_name(away).split()[0] if norm_name(away) else ""
        if first and first in norm_name(sel):
            away_sc = max(away_sc, 0.55)
    if home_sc >= 0.45 and home_sc > away_sc + 0.05:
        return "home"
    if away_sc >= 0.45 and away_sc > home_sc + 0.05:
        return "away"
    if home_sc >= 0.4 and away_sc < 0.35:
        return "home"
    if away_sc >= 0.4 and home_sc < 0.35:
        return "away"
    return None
