from __future__ import annotations

"""
Chart entrypoints used by views.

Windows / Flet desktop does not support WebView reliably, so we always use
native Flet charts from desktop.components.charts (interactive tooltips, no
browser, no WebView messages).
"""

from typing import Any

import flet as ft

from desktop.components.charts import (
    category_bars,
    daily_pl_bars,
    drawdown_chart,
    equity_line_chart,
    line_from_series,
    sport_share,
    volume_bars,
)
from desktop.theme import ACCENT, CHART_M, TEXT_MUTED


def equity_area_chart(points: list[dict[str, Any]], height: int = CHART_M) -> ft.Control:
    return equity_line_chart(points, height=height)


def daily_pl_chart(daily: list[dict[str, Any]], height: int = CHART_M, last_n: int = 20) -> ft.Control:
    return daily_pl_bars(daily, height=height, last_n=last_n)


def rolling_line_chart(
    points: list[dict[str, Any]],
    y_key: str,
    *,
    height: int = CHART_M,
    y_as_pct: bool = True,
    title: str = "",
) -> ft.Control:
    return line_from_series(points, y_key, height=height, color=ACCENT, y_as_pct=y_as_pct)


def category_bar_chart(
    stats: dict[str, dict[str, float]],
    *,
    value_key: str = "pl",
    height: int = CHART_M,
    max_items: int = 8,
    label_fn=None,
    on_drill=None,
    dim: str | None = None,
) -> ft.Control:
    return category_bars(
        stats,
        value_key=value_key,
        max_items=max_items,
        label_fn=label_fn,
        height=height,
        on_drill=on_drill,
        dim=dim,
    )


def drawdown_area_chart(points: list[dict[str, Any]], height: int = CHART_M) -> ft.Control:
    return drawdown_chart(points, height=height)


def volume_bar_chart(volume: list[dict[str, Any]], height: int = CHART_M, last_n: int = 16) -> ft.Control:
    return volume_bars(volume, height=height, last_n=last_n)


def mult_timeline_chart(history: list[dict[str, Any]], sport: str = "football", height: int = CHART_M) -> ft.Control:
    """Build a stake-mult series from learning history snaps."""
    if not history:
        return ft.Container(
            content=ft.Text("No learning history yet — settle bets to build a timeline", size=13, color=TEXT_MUTED),
            height=height,
            alignment=ft.alignment.center,
        )
    series: list[dict[str, Any]] = []
    for i, row in enumerate(history):
        sp = (row.get("sports") or {}).get(sport) or {}
        if not sp:
            continue
        ts = str(row.get("ts") or "")[:16].replace("T", " ")
        series.append(
            {
                "date": ts or str(i),
                "stake_mult": float(sp.get("stake_mult") or 1.0),
                "i": i,
            }
        )
    if not series:
        return ft.Container(
            content=ft.Text(f"No history for sport '{sport}'", size=13, color=TEXT_MUTED),
            height=height,
            alignment=ft.alignment.center,
        )
    return line_from_series(series, "stake_mult", height=height, color=ACCENT, y_as_pct=False)


def sport_share_chart(by_sport: dict[str, dict[str, float]], height: int = CHART_M) -> ft.Control:
    return sport_share(by_sport, height=height)
