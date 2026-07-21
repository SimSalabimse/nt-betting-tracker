from __future__ import annotations

"""
Learning v2 — multipliers, what changed, history, lessons.

Layout: stacked Columns only (no ResponsiveRow — breaks scroll height on Windows/Flet).
Segmented into Summary · Multipliers · Lessons for reliability.
"""

import flet as ft

from desktop.components.labels import market_label
from desktop.components.layout import chart_card, scroll_page, segment_tabs
from desktop.components.plotly_charts import mult_timeline_chart
from desktop.theme import (
    ACCENT,
    BORDER,
    CHART_M,
    LOSS,
    PENDING,
    PROFIT,
    SURFACE_2,
    TEXT,
    TEXT_MUTED,
    card,
    chip,
    fmt_nok,
    fmt_pct,
    hero_block,
    muted,
    num,
    page_header,
    pill,
    pl_color,
    section_label,
)


def _status_color(status: str) -> str:
    s = (status or "").lower()
    if s in ("strong", "good"):
        return PROFIT
    if s in ("poor", "blocked", "weak"):
        return LOSS
    if s == "thin":
        return TEXT_MUTED
    return PENDING


def _mult_row(name: str, s: dict, *, name_w: int = 120) -> ft.Control:
    roi = float(s.get("roi_blended") if s.get("roi_blended") is not None else s.get("roi") or 0)
    st_mult = float(s.get("stake_mult") or 1.0)
    ev_b = float(s.get("ev_boost") or 0)
    status = str(s.get("status") or "—")
    n = int(s.get("n") or 0)
    bar_w = max(4, int(abs(st_mult - 1.0) / 0.3 * 80)) if abs(st_mult - 1.0) > 0.01 else 4
    bar_col = PROFIT if st_mult >= 1.0 else LOSS

    return ft.Container(
        content=ft.Row(
            [
                ft.Text(
                    name,
                    size=12,
                    color=TEXT,
                    width=name_w,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(str(n), size=12, width=36, font_family="Consolas", color=TEXT_MUTED),
                ft.Text(
                    fmt_pct(roi, signed=True),
                    size=12,
                    width=64,
                    color=pl_color(roi),
                    font_family="Consolas",
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(
                    content=ft.Container(width=bar_w, height=10, bgcolor=bar_col, border_radius=3),
                    width=90,
                    height=12,
                    alignment=ft.alignment.center_left if st_mult >= 1 else ft.alignment.center_right,
                ),
                ft.Text(
                    f"×{st_mult:.2f}",
                    size=13,
                    width=52,
                    color=bar_col,
                    font_family="Consolas",
                    weight=ft.FontWeight.W_700,
                ),
                ft.Text(
                    f"{ev_b*100:+.1f}pp",
                    size=12,
                    width=56,
                    color=pl_color(ev_b),
                    font_family="Consolas",
                ),
                chip(status, color=_status_color(status)),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=SURFACE_2,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border=ft.border.all(1, BORDER),
    )


def _header_row(name_label: str = "Group", name_w: int = 120) -> ft.Control:
    return ft.Container(
        content=ft.Row(
            [
                ft.Text(name_label, size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=name_w),
                ft.Text("n", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=36),
                ft.Text("ROI", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=64),
                ft.Text("Size lean", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=90),
                ft.Text("Stake", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=52),
                ft.Text("EV", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=56),
                ft.Text("Status", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=72),
            ],
            spacing=8,
        ),
        padding=ft.padding.only(left=4, bottom=4),
    )


def _lesson_card(L: dict) -> ft.Control:
    level = (L.get("level") or "info").lower()
    col = PROFIT if level == "good" else (LOSS if level == "warn" else ACCENT)
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        chip(level.upper(), color=col),
                        chip(str(L.get("scope") or ""), color=TEXT_MUTED),
                        ft.Text(
                            str(L.get("title") or ""),
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=TEXT,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                muted(str(L.get("detail") or ""), 12),
            ],
            spacing=4,
            tight=True,
        ),
        bgcolor=SURFACE_2,
        border=ft.border.all(1, BORDER),
        border_radius=10,
        padding=12,
    )


def _move_row(m: dict) -> ft.Control:
    """Show stake× AND EV boost changes (both live in learning.json)."""
    d_st = float(m.get("delta_stake") or 0)
    d_ev = float(m.get("delta_ev") or 0)
    col = (
        PROFIT
        if d_st > 0.005 or d_ev > 0.0005
        else (LOSS if d_st < -0.005 or d_ev < -0.0005 else TEXT_MUTED)
    )
    kind = str(m.get("kind") or "")
    name = str(m.get("name") or "")
    if kind == "market":
        name = market_label(name)
    sf = float(m.get("stake_from") if m.get("stake_from") is not None else 1.0)
    st = float(m.get("stake_to") if m.get("stake_to") is not None else 1.0)
    ef = float(m.get("ev_from") or 0.0)
    et = float(m.get("ev_to") or 0.0)
    return ft.Container(
        content=ft.Row(
            [
                chip(kind.upper(), color=ACCENT if kind == "sport" else TEXT_MUTED),
                ft.Text(
                    name,
                    size=12,
                    weight=ft.FontWeight.W_600,
                    color=TEXT,
                    width=110,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    f"×{sf:.3f}→×{st:.3f}",
                    size=11,
                    color=col,
                    font_family="Consolas",
                    width=110,
                ),
                ft.Text(
                    f"EV {ef*100:+.1f}→{et*100:+.1f}pp",
                    size=11,
                    color=pl_color(d_ev),
                    font_family="Consolas",
                    width=120,
                ),
                ft.Text(
                    f"Δ×{d_st:+.3f} · ΔEV{d_ev*100:+.1f}pp",
                    size=11,
                    color=col,
                    font_family="Consolas",
                    expand=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=SURFACE_2,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )


def _settlement_impact_row(r: dict) -> ft.Control:
    res = str(r.get("result") or "")
    try:
        pl = float(r.get("pl") or 0)
    except (TypeError, ValueError):
        pl = 0.0
    res_c = PROFIT if res == "Win" else (LOSS if res == "Loss" else PENDING)
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        chip(res[:4].upper() if res else "—", color=res_c),
                        ft.Text(
                            f"{r.get('date') or ''}  {(r.get('match') or '')[:42]}",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=TEXT,
                            expand=True,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            fmt_nok(pl, signed=True),
                            size=12,
                            color=pl_color(pl),
                            font_family="Consolas",
                            weight=ft.FontWeight.W_700,
                        ),
                    ],
                    spacing=8,
                ),
                muted(
                    f"{r.get('selection')} @ {r.get('odds')} · "
                    f"feeds {r.get('sport')} (now ×{r.get('sport_stake_now') or 1}) · "
                    f"{market_label(str(r.get('market') or ''))} (now ×{r.get('market_stake_now') or 1})",
                    11,
                ),
            ],
            spacing=3,
            tight=True,
        ),
        bgcolor=SURFACE_2,
        border=ft.border.all(1, BORDER),
        border_radius=8,
        padding=10,
    )


def _history_table(history: list[dict], limit: int = 12) -> ft.Control:
    if not history:
        return muted("No learning_history.jsonl yet — recompute after settles to build timeline")
    rows: list[ft.Control] = [
        ft.Container(
            content=ft.Row(
                [
                    ft.Text("When (UTC)", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=130),
                    ft.Text("n", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=40),
                    ft.Text("Era ROI", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=70),
                    ft.Text("Moves", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=50),
                    ft.Text("Top sports ×", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, expand=True),
                ],
                spacing=8,
            ),
            padding=ft.padding.only(bottom=4),
        )
    ]
    for snap in reversed(history[-limit:]):
        sports = snap.get("sports") or {}
        top = sorted(sports.items(), key=lambda kv: kv[1].get("n") or 0, reverse=True)[:4]
        top_txt = " · ".join(f"{k}×{float(v.get('stake_mult') or 1):.2f}" for k, v in top) or "—"
        era = snap.get("era_roi")
        try:
            era_f = float(era) if era is not None else None
        except (TypeError, ValueError):
            era_f = None
        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(
                            str(snap.get("ts") or "")[:16].replace("T", " "),
                            size=12,
                            width=130,
                            font_family="Consolas",
                            color=TEXT,
                        ),
                        ft.Text(
                            str(snap.get("n_settled") or "—"),
                            size=12,
                            width=40,
                            font_family="Consolas",
                            color=TEXT_MUTED,
                        ),
                        ft.Text(
                            fmt_pct(era_f, signed=True) if era_f is not None else "—",
                            size=12,
                            width=70,
                            color=pl_color(era_f or 0),
                            font_family="Consolas",
                        ),
                        ft.Text(str(snap.get("n_moves") or 0), size=12, width=50, font_family="Consolas"),
                        ft.Text(
                            top_txt,
                            size=11,
                            expand=True,
                            color=TEXT_MUTED,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=8,
                ),
                bgcolor=SURFACE_2,
                border=ft.border.all(1, BORDER),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
            )
        )
    return ft.Column(rows, spacing=4, tight=True)


def _stack(*controls: ft.Control, spacing: int = 12) -> ft.Control:
    """Vertical stack — never ResponsiveRow (safe inside scroll)."""
    return ft.Column(list(controls), spacing=spacing, tight=True)


def build_learnings(state) -> ft.Control:
    learn = getattr(state, "learning", None) or {}
    history = list(getattr(state, "learning_history", None) or [])
    cfg_learn = (getattr(state, "cfg", None) or {}).get("learning") or {}
    enabled = bool(learn.get("enabled", cfg_learn.get("enabled", True)))
    summary = learn.get("summary") or {}
    sports = learn.get("sports") or {}
    markets = learn.get("markets") or {}
    bands = learn.get("bands") or {}
    lessons = learn.get("lessons") or []
    snap = learn.get("config_snapshot") or {}
    moves = learn.get("multiplier_moves") or []
    recent_setts = learn.get("recent_settlements") or []
    updated = str(learn.get("updated_at") or "—")
    prev_updated = str(learn.get("previous_updated_at") or "")
    weight_mode = str(snap.get("weight_mode") or cfg_learn.get("weight_mode") or "weighted")
    half_life = snap.get("half_life_days", cfg_learn.get("half_life_days", 60))

    timeline_sport = "football"
    if sports:
        timeline_sport = max(sports.items(), key=lambda kv: kv[1].get("n") or 0)[0]

    if not learn:
        return scroll_page(
            page_header("Learning", "No learning state yet — run settle or: python run_nt.py learn"),
            card(
                ft.Column(
                    [
                        muted("The learning loop reads the settled ledger and produces sport/market/band multipliers."),
                        muted("They feed recommend (EV boost + stake ×) without rewriting config.yaml."),
                    ],
                    spacing=8,
                )
            ),
        )

    header = page_header(
        "Learning",
        f"Last recompute {updated.replace('T', ' ')[:19]} UTC · n={int(summary.get('n_settled') or 0)} settled · "
        f"{int(summary.get('n_moves') or len(moves))} multiplier moves · {weight_mode}",
        trailing=pill("LEARNING ON" if enabled else "OFF", ok=enabled),
    )

    hero = hero_block(
        "Era ROI (learning sample)",
        fmt_pct(summary.get("era_roi"), signed=True),
        sub=(
            f"P/L {fmt_nok(summary.get('era_pl') or 0, signed=True)} · "
            f"{int(summary.get('n_settled') or 0)} settled · {weight_mode} · half-life {half_life}d"
        ),
        color=pl_color(float(summary.get("era_roi") or 0)),
    )

    kpis = ft.Row(
        [
            card(
                ft.Column(
                    [
                        muted("Sample", 11),
                        num(str(int(summary.get("n_settled") or 0)), size=22),
                        muted("settled bets", 11),
                    ],
                    spacing=2,
                    tight=True,
                ),
                expand=True,
            ),
            card(
                ft.Column(
                    [
                        muted("Sports tracked", 11),
                        num(str(int(summary.get("n_sports_active") or len(sports))), size=22),
                        muted(f"{int(summary.get('n_blocked_sports') or 0)} soft-blocked", 11),
                    ],
                    spacing=2,
                    tight=True,
                ),
                expand=True,
            ),
            card(
                ft.Column(
                    [
                        muted("Weight mode", 11),
                        num(weight_mode[:12], size=18, color=ACCENT),
                        muted(f"half-life {half_life}d · {len(history)} snaps", 11),
                    ],
                    spacing=2,
                    tight=True,
                ),
                expand=True,
            ),
            card(
                ft.Column(
                    [
                        muted("Mult moves", 11),
                        num(str(int(summary.get("n_moves") or len(moves))), size=22),
                        muted(updated.replace("T", " ")[:16], 11),
                    ],
                    spacing=2,
                    tight=True,
                ),
                expand=True,
            ),
        ],
        spacing=12,
    )

    # ── Tab: Summary ──
    change_bits: list[ft.Control] = [section_label("What changed (this recompute)")]
    if prev_updated:
        change_bits.append(
            muted(f"Compared to previous @ {prev_updated.replace('T', ' ')[:19]} UTC", 11)
        )
    else:
        change_bits.append(muted("First snapshot or no previous file", 11))
    if moves:
        change_bits.extend(_move_row(m) for m in moves[:12])
    else:
        change_bits.append(muted("No stake/EV/status moves vs last snapshot."))

    impact_bits: list[ft.Control] = [
        section_label("Recent bets feeding learnings"),
        muted("Each settled bet updates sport + market mults", 11),
    ]
    if recent_setts:
        impact_bits.extend(_settlement_impact_row(r) for r in recent_setts[:10])
    else:
        impact_bits.append(muted("No settled bets yet."))

    best = summary.get("best_sports") or []
    worst = summary.get("worst_sports") or []

    summary_tab = scroll_page(
        hero,
        kpis,
        chart_card(
            f"Stake × timeline · {timeline_sport}",
            mult_timeline_chart(history, sport=timeline_sport, height=CHART_M),
            subtitle="From learning_history.jsonl",
            height=CHART_M + 48,
        ),
        card(
            ft.Column(
                [
                    section_label("History snapshots"),
                    muted(f"{len(history)} stored · newest first", 11),
                    ft.Container(height=6),
                    _history_table(history, limit=10),
                ],
                spacing=4,
                tight=True,
            )
        ),
        card(ft.Column(change_bits, spacing=4, tight=True)),
        card(ft.Column(impact_bits, spacing=4, tight=True)),
        card(
            ft.Column(
                [
                    section_label("Best sports"),
                    *(
                        [
                            muted(
                                f"· {b.get('name')} · n={b.get('n')} · "
                                f"ROI {fmt_pct(b.get('roi_blended'), signed=True)} · ×{b.get('stake_mult')}"
                            )
                            for b in best
                        ]
                        if best
                        else [muted("Need more sample")]
                    ),
                    ft.Container(height=8),
                    section_label("Weakest sports"),
                    *(
                        [
                            muted(
                                f"· {b.get('name')} · n={b.get('n')} · "
                                f"ROI {fmt_pct(b.get('roi_blended'), signed=True)} · ×{b.get('stake_mult')}"
                            )
                            for b in worst
                        ]
                        if worst
                        else [muted("Need more sample")]
                    ),
                ],
                spacing=4,
                tight=True,
            )
        ),
        spacing=14,
    )

    # ── Tab: Multipliers ──
    sport_rows = [_header_row("Sport", 120)]
    for name, s in sorted(sports.items(), key=lambda kv: kv[1].get("n", 0), reverse=True):
        sport_rows.append(_mult_row(name, s, name_w=120))

    market_rows = [_header_row("Market", 140)]
    for name, s in sorted(markets.items(), key=lambda kv: kv[1].get("n", 0), reverse=True)[:18]:
        market_rows.append(_mult_row(market_label(name), s, name_w=140))

    band_rows = [_header_row("Band", 90)]
    band_order = ["<1.5", "1.5-1.8", "1.8-2.2", "2.2-2.5", "2.5-3.0", ">=3.0"]
    ordered_bands = [(b, bands[b]) for b in band_order if b in bands]
    ordered_bands += [(k, v) for k, v in bands.items() if k not in band_order]
    for name, s in ordered_bands:
        band_rows.append(_mult_row(name, s, name_w=90))

    mults_tab = scroll_page(
        card(
            ft.Column(
                [
                    section_label("Sport multipliers (used in recommend)"),
                    ft.Container(height=8),
                    *sport_rows,
                ],
                spacing=4,
                tight=True,
            )
        ),
        card(
            ft.Column(
                [section_label("Market multipliers"), ft.Container(height=8), *market_rows],
                spacing=4,
                tight=True,
            )
        ),
        card(
            ft.Column(
                [section_label("Odds-band learning"), ft.Container(height=8), *band_rows],
                spacing=4,
                tight=True,
            )
        ),
        spacing=14,
    )

    # ── Tab: Lessons + rules ──
    lesson_cards = [_lesson_card(L) for L in lessons] or [muted("No lessons yet — settle more bets.")]
    div = cfg_learn.get("diversification") or {}
    rules = card(
        ft.Column(
            [
                section_label("How multipliers are computed"),
                muted(
                    f"Weight mode: {weight_mode} · half-life {half_life}d · "
                    f"archive×{cfg_learn.get('archive_process_weight', 0.35)} · "
                    f"full process×{cfg_learn.get('full_process_weight', 1.0)}"
                ),
                muted(
                    f"Min sample {snap.get('min_sample', cfg_learn.get('min_sample', 12))} · "
                    f"recent window {snap.get('recent_window', 30)} · "
                    f"recent weight {float(snap.get('recent_weight', 0.4))*100:.0f}%"
                ),
                muted(
                    f"Stake × clamped [{snap.get('stake_mult_min', 0.72)} … {snap.get('stake_mult_max', 1.18)}] · "
                    f"soft-block if n≥{snap.get('block_min_sample', 20)} and "
                    f"ROI≤{float(snap.get('block_roi_below', -0.18))*100:.0f}%"
                ),
                muted(
                    f"Diversify: max {div.get('max_per_sport', 2)}/sport · "
                    f"{div.get('max_per_market', 2)}/market · {div.get('max_per_band', 3)}/band "
                    f"(includes open pending)"
                ),
                muted(
                    f"Football soft max {div.get('max_football_per_round', 1)}/round then "
                    f"fill empty seats with good football (up to sport cap)"
                ),
                muted("Recommend: EV += boosts · stake × lean · blocked rejected · caps stop mono-slips"),
                muted("Files: learning.json · learning_history.jsonl · bet_decisions.jsonl"),
            ],
            spacing=6,
            tight=True,
        )
    )

    lessons_tab = scroll_page(
        card(
            ft.Column(
                [
                    section_label(f"Lessons ({len(lessons)})"),
                    ft.Container(height=8),
                    *lesson_cards,
                ],
                spacing=8,
                tight=True,
            )
        ),
        rules,
        spacing=14,
    )

    tabs = segment_tabs(
        ["Summary", "Multipliers", "Lessons"],
        [summary_tab, mults_tab, lessons_tab],
        selected=0,
    )

    return ft.Column([header, tabs], spacing=8, expand=True)
