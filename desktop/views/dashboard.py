from __future__ import annotations

import flet as ft

from desktop.components.layout import chart_card, scroll_page, two_col
from desktop.components.plotly_charts import daily_pl_chart, equity_area_chart
from desktop.components.widgets import pending_panel, phase_panel, risk_gauge
from desktop.services.state_service import AppState
from desktop.theme import (
    ACCENT,
    CHART_M,
    INFO,
    PENDING,
    PROFIT,
    TEXT,
    TEXT_MUTED,
    fmt_nok,
    fmt_pct,
    hero_block,
    metric,
    muted,
    page_header,
    pill,
    pl_color,
)


def build_dashboard(state: AppState) -> ft.Control:
    b = state.bankroll
    d = state.dive or {}
    o = d.get("overall") or state.overall or {}
    cur = (d.get("streaks") or {}).get("current") or state.streak or {}
    streak = f"{cur.get('length')}× {cur.get('type')}" if cur.get("type") else "—"

    equity = float(b.get("equity_nok") or 0)
    pend_n = int(b.get("pending_count") or 0)
    range_label = d.get("range_label") or state.range_label or "All time"
    period_n = int(d.get("period_n") or o.get("n_settled") or 0)
    period_pl = float(o.get("pl") or 0)
    can = bool((state.risk or {}).get("can_bet"))
    baseline = float(b.get("baseline_nok") or 0)
    era_pl = equity - baseline

    learn = state.learning or {}
    n_moves = int((learn.get("summary") or {}).get("n_moves") or len(learn.get("multiplier_moves") or []))
    learn_ts = str(learn.get("updated_at") or "")[:16].replace("T", " ")

    header = page_header(
        "Overview",
        f"{range_label} · {period_n} settled · learning {learn_ts or '—'} · {n_moves} mult moves",
        trailing=pill("CAN BET" if can else "RISK FULL", ok=can),
    )

    hero = hero_block(
        "Live equity",
        fmt_nok(equity),
        sub=f"baseline {fmt_nok(baseline)} · era P/L {fmt_nok(era_pl, signed=True)} · phase {state.phase.get('phase_id') or '—'}",
        color=ACCENT,
        trailing=ft.Column(
            [
                muted("Window P/L", 11),
                ft.Text(
                    fmt_nok(period_pl, signed=True),
                    size=22,
                    weight=ft.FontWeight.W_700,
                    color=pl_color(period_pl),
                    font_family="Consolas",
                ),
                muted(f"ROI {fmt_pct(o.get('roi'), signed=True)}", 11),
            ],
            spacing=2,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        ),
    )

    metrics = ft.Row(
        [
            metric(
                f"P/L · {range_label}",
                fmt_nok(period_pl, signed=True),
                sub=f"ROI {fmt_pct(o.get('roi'), signed=True)} · {period_n} bets",
                color=pl_color(period_pl),
                accent=pl_color(period_pl),
            ),
            metric(
                "Open risk",
                fmt_nok(float(b.get("pending_at_risk_nok") or 0)),
                sub=f"{pend_n} pending · streak {streak}",
                color=PENDING if pend_n else TEXT,
                accent=PENDING if pend_n else INFO,
            ),
            metric(
                "Win rate",
                fmt_pct(o.get("winrate")),
                sub=f"exp {fmt_nok(o.get('expectancy') or 0, signed=True)} · max DD {fmt_nok(state.max_dd)}",
                color=PROFIT if float(o.get("winrate") or 0) >= 0.5 else TEXT,
                accent=INFO,
            ),
            metric(
                "Phase",
                str((state.phase or {}).get("phase_id") or "—"),
                sub=str((state.phase or {}).get("label") or ""),
                accent=ACCENT,
            ),
        ],
        spacing=12,
    )

    charts = two_col(
        chart_card(
            "Equity curve",
            equity_area_chart(state.equity_curve, height=CHART_M),
            subtitle=f"{range_label} · hover points for day detail",
            height=CHART_M + 56,
        ),
        chart_card(
            "Daily P/L",
            daily_pl_chart(state.daily, height=CHART_M, last_n=16),
            subtitle="Green up / red down in selected range",
            height=CHART_M + 56,
        ),
        left_w=7,
        right_w=5,
    )

    side = ft.Column([phase_panel(state), risk_gauge(state)], spacing=12, tight=True)
    body = two_col(charts, side, left_w=8, right_w=4)

    parts: list[ft.Control] = [header, hero, metrics, body]
    pend = pending_panel(state)
    if pend:
        parts.append(pend)
    parts.append(
        muted(
            "Native charts · open Bets for decision dossiers · Learning for multipliers & history"
        )
    )
    return scroll_page(*parts, spacing=18)
