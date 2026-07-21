from __future__ import annotations

import flet as ft

from desktop.components.layout import scroll_page, two_col
from desktop.components.widgets import phase_panel, risk_gauge, risk_status_label
from desktop.services.state_service import AppState
from desktop.theme import (
    ACCENT,
    BORDER,
    LOSS,
    PROFIT,
    SURFACE_2,
    TEXT,
    TEXT_MUTED,
    card,
    chip,
    fmt_nok,
    muted,
    page_header,
    pill,
    section_label,
)


def build_risk_phase(state: AppState) -> ft.Control:
    cfg = state.cfg
    phase = state.phase
    risk = state.risk
    phases = cfg.get("phases") or {}
    order = list(phases.keys())
    current = phase.get("phase_id")
    sel = cfg.get("selection") or {}
    risk_cfg = cfg.get("risk") or {}

    ladder = []
    for pid in order:
        p = phases[pid]
        active = pid == current
        ladder.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                chip(pid, color=ACCENT if active else TEXT_MUTED),
                                ft.Text("NOW" if active else "", size=10, color=ACCENT, weight=ft.FontWeight.W_700),
                            ],
                            spacing=8,
                        ),
                        ft.Text(p.get("label", ""), size=12, color=TEXT if active else TEXT_MUTED, weight=ft.FontWeight.W_600),
                        muted(f"Equity ≥ {p.get('enter_equity')} · settled ≥ {p.get('enter_settled')}"),
                        muted(
                            f"Stake {p.get('stake_min')}–{p.get('stake_max')} · "
                            f"{float(p.get('daily_risk_pct', 0)) * 100:.0f}% risk"
                        ),
                    ],
                    spacing=4,
                    tight=True,
                ),
                bgcolor=SURFACE_2 if active else "transparent",
                border=ft.border.all(1, ACCENT if active else BORDER),
                border_radius=10,
                padding=12,
                width=160,
            )
        )

    return scroll_page(
        page_header(
            "Risk & phase",
            "Live engines + config — code is law",
            trailing=pill(risk_status_label(bool(risk.get("can_bet"))), ok=bool(risk.get("can_bet"))),
        ),
        two_col(phase_panel(state), risk_gauge(state)),
        card(
            ft.Column(
                [
                    section_label("Phase ladder"),
                    ft.Container(height=8),
                    ft.Row(ladder, spacing=10, scroll=ft.ScrollMode.AUTO),
                ],
                tight=True,
            )
        ),
        two_col(
            card(
                ft.Column(
                    [
                        section_label("Risk config"),
                        muted(f"Stop floor: {risk_cfg.get('stop_day_loss_floor_nok')} NOK"),
                        muted(f"Stop % equity: {float(risk_cfg.get('stop_day_loss_pct_of_equity') or 0) * 100:.0f}%"),
                        muted(f"Loss streak → grade A: {risk_cfg.get('loss_streak_grade_a_only')}"),
                        muted(str(risk.get("formula", "")), 11),
                        *[ft.Text(f"· {r}", size=12, color=LOSS) for r in (risk.get("reasons") or [])],
                    ],
                    spacing=6,
                    tight=True,
                )
            ),
            card(
                ft.Column(
                    [
                        section_label("High odds policy"),
                        muted(f"Threshold: odds > {sel.get('high_odds_threshold')}"),
                        muted(f"Min grade {sel.get('high_odds_min_grade')} · min EV {float(sel.get('high_odds_min_ev') or 0) * 100:.0f}%"),
                        muted(f"Stake ×{sel.get('high_odds_stake_multiplier')} · max {sel.get('high_odds_max_per_round')}/round"),
                        muted(f"Standard min EV {float(sel.get('standard_min_ev') or 0) * 100:.0f}% · haircut {float(sel.get('probability_haircut') or 0) * 100:.0f}%"),
                        ft.Text(f"Empty slip OK: {sel.get('empty_slip_ok')}", size=12, color=PROFIT),
                    ],
                    spacing=6,
                    tight=True,
                )
            ),
        ),
        card(
            ft.Column(
                [
                    section_label("Live numbers"),
                    ft.Text(
                        f"Equity {fmt_nok(float(risk.get('equity_nok') or state.bankroll.get('equity_nok') or 0))}  ·  "
                        f"cap {fmt_nok(float(risk.get('daily_risk_cap_nok') or 0))}  ·  "
                        f"remaining {fmt_nok(float(risk.get('remaining_risk_nok') or 0))}",
                        size=13,
                        color=TEXT,
                        font_family="Consolas",
                    ),
                    muted(
                        f"Pending risk {fmt_nok(float(risk.get('open_pending_risk_nok') or 0))} · "
                        f"today P/L {fmt_nok(float(risk.get('today_realized_pl_nok') or 0), signed=True)}"
                    ),
                ],
                spacing=8,
                tight=True,
            )
        ),
        spacing=16,
    )
