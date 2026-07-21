from __future__ import annotations

"""
Unified Analytics — Overview · Breakdowns · Tables
Native Flet charts only (no WebView).
Forensic: click category bars / table rows → tickets via on_drill(dim, value, label).
"""

from typing import Any, Callable

import flet as ft

from desktop.components.labels import market_label
from desktop.components.layout import chart_card, scroll_page, segment_tabs, three_col, two_col
from desktop.components.plotly_charts import (
    category_bar_chart,
    daily_pl_chart,
    drawdown_area_chart,
    equity_area_chart,
    rolling_line_chart,
    sport_share_chart,
    volume_bar_chart,
)
from desktop.components.tables import bet_list_card, market_stats_table, stats_table
from desktop.services.state_service import AppState
from desktop.theme import (
    ACCENT,
    BORDER,
    CHART_M,
    CHART_S,
    LOSS,
    PROFIT,
    SURFACE_2,
    TEXT_MUTED,
    card,
    fmt_nok,
    fmt_pct,
    metric,
    muted,
    page_header,
    pl_color,
    section_label,
)
from nt.analytics import BAND_ORDER, WEEKDAY_ORDER

DrillFn = Callable[[str, str, str], Any]


def _ord(stats: dict, order: list[str]) -> dict:
    out = {k: stats[k] for k in order if k in stats}
    for k, v in stats.items():
        if k not in out:
            out[k] = v
    return out


def build_analytics(state: AppState, *, on_drill: DrillFn | None = None) -> ft.Control:
    d = state.dive or {}
    o = d.get("overall") or {}
    streaks = d.get("streaks") or {}
    cur = streaks.get("current") or {}
    conc = d.get("concentration") or {}
    prog = d.get("phase_progress") or {}
    best_worst = d.get("best_worst") or {}
    by_weekday = _ord(d.get("by_weekday") or {}, WEEKDAY_ORDER)
    by_band = _ord(d.get("by_band") or {}, BAND_ORDER)
    rolling = d.get("rolling_20") or []
    streak = f"{cur.get('length')}× {cur.get('type')}" if cur.get("type") else "—"
    range_label = d.get("range_label") or state.range_label or "All time"
    period_n = int(d.get("period_n") or 0)

    header = page_header(
        "Analytics",
        f"{range_label} · {d.get('date_from') or '—'} → {d.get('date_to') or '—'} · {period_n} settled"
        + (" · click bars/tables → tickets" if on_drill else ""),
    )

    kpis = ft.Row(
        [
            metric("P/L", fmt_nok(o.get("pl") or 0, signed=True), sub=f"ROI {fmt_pct(o.get('roi'), signed=True)}", color=pl_color(o.get("pl") or 0)),
            metric("Win rate", fmt_pct(o.get("winrate")), sub=f"{int(o.get('wins') or 0)}W / {int(o.get('losses') or 0)}L"),
            metric("Profit factor", f"{float(o.get('profit_factor') or 0):.2f}"),
            metric("Expectancy", fmt_nok(o.get("expectancy") or 0, signed=True), color=pl_color(o.get("expectancy") or 0)),
            metric("Max DD", fmt_nok(d.get("max_drawdown") or 0), sub=streak, color=LOSS if d.get("max_drawdown") else TEXT_MUTED),
            metric("Avg odds", f"{float(o.get('avg_odds') or 0):.2f}"),
        ],
        spacing=10,
    )

    overview = scroll_page(
        kpis,
        two_col(
            chart_card("Equity", equity_area_chart(d.get("equity_curve") or [], height=CHART_M), subtitle=range_label, height=CHART_M + 48),
            chart_card("Drawdown", drawdown_area_chart(d.get("drawdown") or [], height=CHART_M), subtitle="Peak-to-trough", height=CHART_M + 48),
        ),
        two_col(
            chart_card("Daily P/L", daily_pl_chart(d.get("daily") or [], height=CHART_S, last_n=16), height=CHART_S + 48),
            chart_card("Volume", volume_bar_chart(d.get("volume") or [], height=CHART_S, last_n=16), height=CHART_S + 48),
        ),
        two_col(
            chart_card("Rolling ROI (20)", rolling_line_chart(rolling, "rolling_roi", height=CHART_S, y_as_pct=True), height=CHART_S + 48),
            chart_card("Rolling win rate (20)", rolling_line_chart(rolling, "rolling_wr", height=CHART_S, y_as_pct=True), height=CHART_S + 48),
        ),
        spacing=16,
    )

    breakdowns = scroll_page(
        three_col(
            chart_card(
                "Sport P/L",
                category_bar_chart(
                    d.get("by_sport") or {},
                    value_key="pl",
                    height=CHART_M,
                    max_items=8,
                    on_drill=on_drill,
                    dim="sport",
                ),
                height=CHART_M + 40,
            ),
            chart_card("Sport mix", sport_share_chart(d.get("by_sport") or {}, height=CHART_M), height=CHART_M + 40),
            chart_card(
                "Weekday P/L",
                category_bar_chart(
                    by_weekday,
                    value_key="pl",
                    height=CHART_M,
                    max_items=7,
                    on_drill=on_drill,
                    dim="weekday",
                ),
                height=CHART_M + 40,
            ),
        ),
        three_col(
            chart_card(
                "Market P/L",
                category_bar_chart(
                    d.get("by_market") or {},
                    value_key="pl",
                    height=CHART_M,
                    max_items=8,
                    label_fn=market_label,
                    on_drill=on_drill,
                    dim="market",
                ),
                height=CHART_M + 40,
            ),
            chart_card(
                "Odds band P/L",
                category_bar_chart(
                    by_band,
                    value_key="pl",
                    height=CHART_M,
                    max_items=8,
                    on_drill=on_drill,
                    dim="odds_band",
                ),
                height=CHART_M + 40,
            ),
            chart_card(
                "Stake size P/L",
                category_bar_chart(
                    d.get("by_stake_bucket") or {},
                    value_key="pl",
                    height=CHART_M,
                    max_items=6,
                    on_drill=on_drill,
                    dim="stake_bucket",
                ),
                height=CHART_M + 40,
            ),
        ),
        two_col(
            card(
                ft.Column(
                    [
                        section_label("Concentration"),
                        muted(f"Top sport: {conc.get('top_sport') or '—'} ({fmt_pct(conc.get('top_sport_pct'))})"),
                        muted(f"Football share: {fmt_pct(conc.get('football_pct'))}"),
                        muted(f"Sports: {int(conc.get('n_sports') or 0)}"),
                        ft.Divider(color=BORDER, height=16),
                        section_label("Archive vs live"),
                        *(
                            [
                                ft.Text(
                                    f"{name}: n={int(s.get('n', 0))}  ROI {fmt_pct(s.get('roi'), signed=True)}  "
                                    f"P/L {fmt_nok(s.get('pl') or 0, signed=True)}",
                                    size=12,
                                    color=pl_color(s.get("pl") or 0),
                                )
                                for name, s in (d.get("by_source") or {}).items()
                            ]
                            or [muted("No source split")]
                        ),
                    ],
                    spacing=6,
                    tight=True,
                )
            ),
            card(
                ft.Column(
                    [
                        section_label("Phase path"),
                        ft.Text(
                            f"{prog.get('current') or state.phase.get('phase_id')} → {prog.get('next') or '—'}",
                            size=20,
                            weight=ft.FontWeight.W_800,
                            color=ACCENT,
                        ),
                        muted(str(prog.get("next_label") or state.phase.get("label") or "")),
                        muted("Equity"),
                        ft.ProgressBar(value=float(prog.get("equity_progress") or 0), color=ACCENT, bgcolor=SURFACE_2, bar_height=7, border_radius=3),
                        muted(
                            f"{fmt_nok(float(prog.get('equity_now') or state.bankroll.get('equity_nok') or 0))} / "
                            f"{fmt_nok(float(prog.get('equity_target') or 0))}"
                        ),
                        muted("Settled count"),
                        ft.ProgressBar(value=float(prog.get("count_progress") or 0), color=PROFIT, bgcolor=SURFACE_2, bar_height=7, border_radius=3),
                        muted(f"{int(prog.get('settled_now') or 0)} / {int(prog.get('settled_target') or 0)}"),
                    ],
                    spacing=6,
                    tight=True,
                )
            ),
        ),
        ft.Row(
            [
                bet_list_card("Best by P/L", best_worst.get("best") or []),
                bet_list_card("Worst by P/L", best_worst.get("worst") or []),
            ],
            spacing=12,
        ),
        spacing=16,
    )

    tables = scroll_page(
        stats_table("By sport", d.get("by_sport") or {}, on_drill=on_drill, dim="sport"),
        market_stats_table("By market", d.get("by_market") or {}, on_drill=on_drill),
        stats_table("By weekday", by_weekday, on_drill=on_drill, dim="weekday"),
        stats_table("By odds band", by_band, on_drill=on_drill, dim="odds_band"),
        stats_table("By phase", d.get("by_phase") or {}, on_drill=on_drill, dim="phase"),
        stats_table("By grade", d.get("by_grade") or state.by_grade or {}, on_drill=on_drill, dim="research_grade"),
        stats_table("By stake", d.get("by_stake_bucket") or {}, on_drill=on_drill, dim="stake_bucket"),
        stats_table("Archive vs live", d.get("by_source") or {}, on_drill=on_drill, dim="source"),
        spacing=14,
    )

    tabs = segment_tabs(
        ["Overview", "Breakdowns", "Tables"],
        [overview, breakdowns, tables],
        selected=0,
    )

    return ft.Column([header, tabs], spacing=8, expand=True)


def build_insights(state: AppState, **kwargs) -> ft.Control:
    return build_analytics(state, **kwargs)


def build_performance(state: AppState, **kwargs) -> ft.Control:
    return build_analytics(state, **kwargs)
