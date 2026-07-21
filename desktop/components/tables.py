from __future__ import annotations

import flet as ft

from desktop.components.labels import market_label
from desktop.theme import BORDER, SURFACE_2, TEXT, TEXT_MUTED, card, fmt_nok, fmt_pct, muted, pl_color, section_label


def stats_table(
    title: str,
    data: dict[str, dict[str, float]],
    *,
    sort_key: str = "pl",
    label_fn=None,
    on_drill=None,
    dim: str | None = None,
) -> ft.Control:
    """Stats table. When on_drill(dim, key, label) is set, rows are clickable for forensic grain."""
    items = sorted(data.items(), key=lambda kv: kv[1].get(sort_key, 0), reverse=True)
    lab = label_fn or (lambda x: x)
    header = ft.Container(
        content=ft.Row(
            [
                ft.Text("Group", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, expand=2),
                ft.Text("n", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=36),
                ft.Text("WR", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=52),
                ft.Text("ROI", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=60),
                ft.Text("P/L", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=88),
                ft.Text("Stake", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=72),
                ft.Text("Avg", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600, width=48),
            ],
            spacing=6,
        ),
        bgcolor=SURFACE_2,
        border_radius=6,
        padding=ft.padding.symmetric(vertical=6, horizontal=4),
    )
    rows = []
    for i, (name, s) in enumerate(items):
        disp = lab(name)

        def _click(_e=None, key=name, display=disp):
            if on_drill and dim and key:
                try:
                    on_drill(dim, key, display)
                except Exception:
                    pass

        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(disp or "—", size=12, color=TEXT, expand=2, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(str(int(s.get("n", 0))), size=12, width=36, font_family="Consolas"),
                        ft.Text(fmt_pct(s.get("winrate")), size=12, width=52, font_family="Consolas"),
                        ft.Text(
                            fmt_pct(s.get("roi"), signed=True),
                            size=12,
                            width=60,
                            color=pl_color(s.get("roi") or 0),
                            font_family="Consolas",
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            fmt_nok(s.get("pl") or 0, signed=True),
                            size=12,
                            width=88,
                            color=pl_color(s.get("pl") or 0),
                            font_family="Consolas",
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(fmt_nok(s.get("stake") or 0), size=12, width=72, font_family="Consolas"),
                        ft.Text(
                            f"{s.get('avg_odds', 0):.2f}" if s.get("avg_odds") else "—",
                            size=12,
                            width=48,
                            font_family="Consolas",
                            color=TEXT_MUTED,
                        ),
                    ],
                    spacing=6,
                ),
                bgcolor=SURFACE_2 if i % 2 else None,
                border=ft.border.only(bottom=ft.BorderSide(1, BORDER)) if i % 2 == 0 else None,
                border_radius=4,
                padding=ft.padding.symmetric(vertical=6, horizontal=4),
                ink=bool(on_drill),
                on_click=_click if on_drill else None,
                tooltip="Click → open tickets for this group" if on_drill else None,
            )
        )
    subtitle = muted("Click a row → tickets (bet_ids grain)", 11) if on_drill else None
    head = [section_label(title), ft.Container(height=4)]
    if subtitle:
        head.extend([subtitle, ft.Container(height=4)])
    head.append(header)
    return card(
        ft.Column(
            [*head, *rows]
            if rows
            else [section_label(title), ft.Container(height=6), muted("No rows")],
            spacing=1,
            tight=True,
        )
    )


def market_stats_table(title: str, data: dict[str, dict[str, float]], **kwargs) -> ft.Control:
    kwargs.setdefault("dim", "market")
    return stats_table(title, data, label_fn=market_label, **kwargs)


def bet_list_card(title: str, bets: list[dict[str, str]]) -> ft.Control:
    lines = []
    for i, r in enumerate(bets):
        try:
            pl = float(r.get("p_l_nok") or 0)
        except ValueError:
            pl = 0.0
        lines.append(
            ft.Container(
                content=ft.Text(
                    f"{r.get('date')}  {(r.get('match') or '')[:32]} · {(r.get('selection') or '')[:18]} @ {r.get('decimal_odds')} → {pl:+.2f}",
                    size=11,
                    color=pl_color(pl),
                    font_family="Consolas",
                ),
                bgcolor=SURFACE_2 if i % 2 else None,
                border_radius=6,
                padding=8,
            )
        )
    return card(
        ft.Column([section_label(title), ft.Container(height=6), *(lines or [muted("—")])], spacing=2, tight=True),
        expand=True,
    )
