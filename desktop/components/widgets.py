from __future__ import annotations

import flet as ft

from desktop.components.labels import humanize_phase_reason
from desktop.theme import (
    ACCENT,
    BORDER,
    LOSS,
    PENDING,
    PROFIT,
    SURFACE,
    SURFACE_2,
    SURFACE_3,
    TEXT,
    TEXT_MUTED,
    card,
    chip,
    fmt_nok,
    fmt_pct,
    muted,
    num,
    pill,
    pl_color,
    result_color,
    section_label,
)


def risk_status_label(can_bet: bool) -> str:
    return "CAN BET" if can_bet else "RISK FULL"


def risk_gauge(state) -> ft.Control:
    risk = state.risk
    cfg = getattr(state, "cfg", {}) or {}
    min_stake = float((cfg.get("norsk_tipping") or {}).get("min_stake_nok") or 10)
    cap = float(risk.get("daily_risk_cap_nok") or 0)
    remaining = float(risk.get("remaining_risk_nok") or 0)
    used = max(0.0, cap - remaining)
    frac = min(1.0, (used / cap) if cap > 0 else 0.0)
    can = bool(risk.get("can_bet", False))
    bar = LOSS if (frac > 0.85 or not can) else (PENDING if frac > 0.55 else ACCENT)

    if can:
        remain_note = "remaining today · room for new bets"
    elif remaining + 1e-6 < min_stake:
        remain_note = f"no room for new bets (min stake {min_stake:.0f} NOK)"
    else:
        remain_note = "risk full · cannot open new stakes"

    return card(
        ft.Column(
            [
                ft.Row(
                    [section_label("Daily risk"), pill(risk_status_label(can), ok=can)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=8),
                num(fmt_nok(remaining), color=ACCENT if can else LOSS, size=24),
                muted(remain_note),
                ft.Container(height=8),
                ft.ProgressBar(value=frac, color=bar, bgcolor=SURFACE_3, bar_height=8, border_radius=4),
                ft.Container(height=6),
                muted(
                    f"Used {fmt_nok(used)} of {fmt_nok(cap)} · "
                    f"stop ≤ −{float(risk.get('stop_day_loss_limit_nok') or 0):.0f}"
                ),
                ft.Text(
                    f"Today P/L {fmt_nok(float(risk.get('today_realized_pl_nok') or 0), signed=True)}",
                    size=12,
                    color=pl_color(float(risk.get("today_realized_pl_nok") or 0)),
                    font_family="Consolas",
                ),
            ],
            spacing=2,
            tight=True,
        )
    )


def phase_panel(state) -> ft.Control:
    p = state.phase
    dive = getattr(state, "dive", {}) or {}
    prog = dive.get("phase_progress") or {}
    nxt = prog.get("next") or p.get("next")
    nxt_label = prog.get("next_label") or ""
    eq_now = float(prog.get("equity_now") or p.get("equity_nok") or 0)
    eq_tgt = float(prog.get("equity_target") or 0)
    n_now = int(prog.get("settled_now") or p.get("settled_count") or 0)
    n_tgt = int(prog.get("settled_target") or 0)
    eq_prog = float(prog.get("equity_progress") or 0)
    n_prog = float(prog.get("count_progress") or 0)

    human_bits: list[str] = []
    eq_phase = p.get("equity_phase") or prog.get("equity_phase")
    count_phase = p.get("count_phase") or prog.get("count_phase")
    pid = str(p.get("phase_id") or "—")
    if eq_phase and str(eq_phase) != pid:
        human_bits.append(
            f"Equity ladder at {eq_phase}; count path lifted you to {pid}"
        )
    elif eq_phase:
        human_bits.append(f"Equity ladder matches phase {eq_phase}")
    if count_phase and str(count_phase) != pid:
        human_bits.append(f"Raw count ladder would be {count_phase} (capped)")

    for r in p.get("reasons") or []:
        h = humanize_phase_reason(str(r))
        if not h:
            continue
        # skip duplicates of equity/count we already phrased
        low = h.lower()
        if "equity ladder" in low or "count ladder" in low:
            continue
        if h not in human_bits:
            human_bits.append(h)

    if nxt:
        path_title = f"Path to {nxt}" + (f" ({nxt_label})" if nxt_label else "")
        eq_line = f"Equity {eq_now:.0f} / {eq_tgt:.0f} NOK" + (
            f" · need +{eq_tgt - eq_now:.0f}" if eq_now < eq_tgt else " · met"
        )
        n_line = f"Settled {n_now} / {n_tgt}" + (
            " · met" if n_now >= n_tgt else f" · need {n_tgt - n_now}"
        )
    else:
        path_title = "Top phase"
        eq_line = f"Equity {eq_now:.0f} NOK"
        n_line = f"Settled {n_now}"

    return card(
        ft.Column(
            [
                section_label("Phase"),
                ft.Container(height=8),
                ft.Row(
                    [
                        chip(pid),
                        ft.Text(str(p.get("label", "")), size=13, color=TEXT, expand=True),
                    ],
                    spacing=10,
                ),
                muted(
                    f"Stake {float(p.get('stake_min') or 0):.0f}–{float(p.get('stake_max') or 0):.0f} · "
                    f"max {p.get('max_bets_per_round')}/round · doubles {p.get('max_doubles_per_round')}"
                ),
                muted(f"Rolling ROI {fmt_pct(p.get('rolling_roi'), signed=True)} · next {nxt or '—'}"),
                ft.Container(height=6),
                muted(path_title, 11),
                muted(eq_line, 11),
                ft.ProgressBar(
                    value=eq_prog,
                    color=ACCENT,
                    bgcolor=SURFACE_3,
                    bar_height=6,
                    border_radius=3,
                ),
                muted(n_line, 11),
                ft.ProgressBar(
                    value=n_prog,
                    color=PROFIT,
                    bgcolor=SURFACE_3,
                    bar_height=6,
                    border_radius=3,
                ),
                *[muted(f"· {r}", 11) for r in human_bits[:4]],
            ],
            spacing=4,
            tight=True,
        )
    )


def recent_settlements_strip(state, n: int = 10) -> ft.Control:
    chips = []
    for r in (state.recent or [])[:n]:
        res = r.get("result") or ""
        try:
            pl = float(r.get("p_l_nok") or 0) if res != "Pending" else 0.0
        except ValueError:
            pl = 0.0
        chips.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(res[:4], size=10, weight=ft.FontWeight.W_700, color=result_color(res)),
                        ft.Text(
                            f"{pl:+.1f}" if res != "Pending" else "—",
                            size=12,
                            color=pl_color(pl),
                            font_family="Consolas",
                        ),
                        muted((r.get("date") or "")[5:], 10),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
                bgcolor=SURFACE_2,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
                tooltip=f"{r.get('match')}\n{r.get('selection')} @ {r.get('decimal_odds')}",
            )
        )
    return card(
        ft.Column(
            [
                section_label("Recent results"),
                ft.Container(height=8),
                ft.Row(chips, scroll=ft.ScrollMode.AUTO, spacing=8)
                if chips
                else muted("None yet"),
            ],
            spacing=0,
            tight=True,
        )
    )


def pending_panel(state) -> ft.Control | None:
    pending = state.pending_rows() if hasattr(state, "pending_rows") else []
    if not pending:
        return None
    lines = []
    for r in pending:
        lines.append(
            ft.Container(
                content=ft.Row(
                    [
                        chip("PENDING", color=PENDING),
                        ft.Column(
                            [
                                ft.Text(
                                    f"{r.get('match') or '—'}",
                                    size=12,
                                    color=TEXT,
                                    weight=ft.FontWeight.W_600,
                                    no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                muted(
                                    f"{r.get('date')} · {r.get('selection')} @ {r.get('decimal_odds')} · "
                                    f"{r.get('stake_nok')} NOK",
                                    11,
                                ),
                            ],
                            spacing=2,
                            tight=True,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=SURFACE_2,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=10,
            )
        )
    list_h = min(320, max(72, 64 * len(pending) + 8))
    return card(
        ft.Column(
            [
                section_label(f"Open pending ({len(pending)})"),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Column(lines, spacing=6, scroll=ft.ScrollMode.AUTO),
                    height=list_h,
                ),
            ],
            spacing=0,
            tight=True,
        )
    )


def band_heatmap(bands: dict) -> ft.Control:
    order = ["<1.5", "1.5-1.8", "1.8-2.2", "2.2-2.5", "2.5-3.0", ">=3.0"]
    keys = [k for k in order if k in bands] + sorted(k for k in bands if k not in order)
    cells = []
    for k in keys:
        s = bands[k]
        roi = float(s.get("roi") or 0)
        col = pl_color(roi)
        cells.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(k, size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                        num(fmt_pct(roi, signed=True), color=col, size=16),
                        muted(f"n={int(s.get('n', 0))}  {fmt_nok(s.get('pl') or 0, signed=True)}", 10),
                    ],
                    spacing=3,
                    tight=True,
                ),
                bgcolor=SURFACE_2,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=12,
                width=120,
            )
        )
    return card(
        ft.Column(
            [
                section_label("ROI by odds band"),
                ft.Container(height=8),
                ft.Row(cells, spacing=8, wrap=True, run_spacing=8) if cells else muted("No data"),
            ],
            spacing=0,
            tight=True,
        )
    )


def place_slip_panel(bets: list[dict], *, title: str = "Place these", meta: str = "") -> ft.Control:
    """Structured place-slip cards (not raw Markdown)."""
    if not bets:
        return card(
            ft.Column(
                [
                    section_label(title),
                    ft.Container(height=8),
                    muted("Empty slip — no bets to place (success when edge is thin)."),
                    muted(meta, 11) if meta else ft.Container(height=0),
                ],
                spacing=4,
                tight=True,
            )
        )

    rows: list[ft.Control] = []
    total_stake = 0.0
    for i, b in enumerate(bets, 1):
        try:
            stake = float(b.get("stake_nok") or b.get("stake") or 0)
        except (TypeError, ValueError):
            stake = 0.0
        total_stake += stake
        try:
            odds = float(b.get("decimal_odds") or b.get("odds") or 0)
            odds_s = f"{odds:.2f}"
        except (TypeError, ValueError):
            odds_s = str(b.get("decimal_odds") or b.get("odds") or "—")
        ev = b.get("ev")
        try:
            ev_s = f"{float(ev):.3f}" if ev is not None and str(ev) != "" else "—"
        except (TypeError, ValueError):
            ev_s = str(ev) if ev else "—"
        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(str(i), size=14, weight=ft.FontWeight.W_700, color=ACCENT),
                            width=28,
                            height=28,
                            alignment=ft.alignment.center,
                            bgcolor=SURFACE_3,
                            border_radius=8,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    str(b.get("match") or "—"),
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    color=TEXT,
                                    no_wrap=True,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                muted(
                                    f"{b.get('selection') or '—'}  ·  grade {b.get('grade') or b.get('research_grade') or '—'}"
                                    + (f"  ·  band {b.get('odds_band')}" if b.get("odds_band") else ""),
                                    11,
                                ),
                            ],
                            spacing=2,
                            tight=True,
                            expand=True,
                        ),
                        ft.Column(
                            [
                                num(odds_s, size=16),
                                muted("odds", 10),
                            ],
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            tight=True,
                        ),
                        ft.Column(
                            [
                                num(f"{stake:.0f}", color=ACCENT, size=16),
                                muted("NOK", 10),
                            ],
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            tight=True,
                        ),
                        ft.Column(
                            [
                                ft.Text(ev_s, size=13, color=TEXT_MUTED, font_family="Consolas"),
                                muted("EV", 10),
                            ],
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            tight=True,
                        ),
                    ],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=SURFACE_2,
                border=ft.border.all(1, BORDER),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
            )
        )

    return card(
        ft.Column(
            [
                ft.Row(
                    [
                        section_label(title),
                        ft.Container(expand=True),
                        chip(f"{len(bets)} bets"),
                        chip(f"{total_stake:.0f} NOK"),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                muted(meta, 11) if meta else ft.Container(height=0),
                ft.Container(height=6),
                *rows,
            ],
            spacing=6,
            tight=True,
        )
    )
