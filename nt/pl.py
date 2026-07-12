from __future__ import annotations

"""P/L rules — never trust chat math for settlements."""


def pl_from_payout(stake: float, payout: float) -> float:
    """payout is total returned (including stake). Loss => 0. Refund => stake."""
    return round(payout - stake, 2)


def pl_from_outcome(stake: float, odds: float, outcome: str) -> float:
    outcome = outcome.strip().lower()
    if outcome in ("loss", "l", "lost"):
        return round(-stake, 2)
    if outcome in ("refund", "refunded", "void", "push"):
        return 0.0
    if outcome in ("win", "w", "won"):
        return round(stake * (odds - 1.0), 2)
    raise ValueError(f"Unknown outcome: {outcome}")


def payout_from_outcome(stake: float, odds: float, outcome: str) -> float:
    outcome = outcome.strip().lower()
    if outcome in ("loss", "l", "lost"):
        return 0.0
    if outcome in ("refund", "refunded", "void", "push"):
        return round(stake, 2)
    if outcome in ("win", "w", "won"):
        return round(stake * odds, 2)
    raise ValueError(f"Unknown outcome: {outcome}")


def expected_win_pl(stake: float, odds: float) -> float:
    return round(stake * (odds - 1.0), 2)
