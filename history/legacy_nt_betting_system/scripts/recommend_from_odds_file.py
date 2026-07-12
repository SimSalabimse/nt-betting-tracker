#!/usr/bin/env python3
"""
Improved Recommendation Engine for the new automated system.
"""
from datetime import datetime

def analyze_odds_file(odds_data, mode="auto"):
    """
    Main analysis function.
    mode: "auto", "targeted", or "deep"
    """
    if mode == "auto":
        if len(odds_data) >= 8:
            mode = "targeted"
        else:
            mode = "deep"

    recommendations = []

    for bet in odds_data:
        # Basic filtering logic (can be expanded significantly)
        odds = bet.get("decimal_odds", 0)
        selection = bet.get("selection", "").lower()

        # Skip very low odds heavy favorites without strong justification
        if odds < 1.40 and "win" in selection:
            continue

        # Example: Prefer value in overs/unders and props over very low odds
        if mode == "targeted":
            if odds > 1.65:  # Only take higher odds in targeted mode
                recommendations.append({
                    "match": bet.get("match", "Unknown"),
                    "selection": bet.get("selection", ""),
                    "odds": odds,
                    "recommended_stake": 12,
                    "mode_used": "targeted",
                    "rationale": "Passed targeted filter. Moderate value detected."
                })
        else:
            # Deep mode - more lenient but still filtered
            if odds > 1.55:
                recommendations.append({
                    "match": bet.get("match", "Unknown"),
                    "selection": bet.get("selection", ""),
                    "odds": odds,
                    "recommended_stake": 10,
                    "mode_used": "deep",
                    "rationale": "Deep research mode. Selected for further review."
                })

    return recommendations, mode