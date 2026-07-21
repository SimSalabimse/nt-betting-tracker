from __future__ import annotations

"""
NT Tracker design system v2 — “desk night”

Warm amber accent on deep ink surfaces. Distinct from the old teal-on-grey stack:
left-edge KPI rails, denser type scale, segmented range, icon rail nav.
"""

import flet as ft

# ── Palette ─────────────────────────────────────────────────────────────
BG = "#0B0D12"              # page ink
SURFACE = "#12161F"         # rail / header
SURFACE_ELEV = "#171C27"    # cards
SURFACE_2 = "#1C2330"       # nested / chips
SURFACE_3 = "#262E3D"       # pressed / bars
BORDER = "#2C3548"
BORDER_SOFT = "#232A38"
BORDER_FOCUS = "#4A5568"
TEXT = "#F3F5F9"
TEXT_MUTED = "#8B95A8"
TEXT_DIM = "#5C6678"
ACCENT = "#E8A317"          # amber gold (desk)
ACCENT_SOFT = "#E8A31728"
ACCENT_DIM = "#B87E10"
PROFIT = "#3DDC97"
LOSS = "#FF6B7A"
PENDING = "#F5C542"
INFO = "#7C9CFF"
RAIL = "#1A2030"            # nav rail

# Spacing (4px base)
S1, S2, S3, S4, S5, S6, S7, S8 = 4, 8, 12, 16, 20, 24, 32, 40
NAV_WIDTH = 84              # icon rail (redesigned — was full labels)
NAV_WIDE = 200
CONTENT_PAD = 22
RADIUS = 10
RADIUS_SM = 6
RADIUS_LG = 14

CHART_S, CHART_M, CHART_L = 150, 210, 280

ANIM_FAST = 120
ANIM_MED = 200
ANIM_SLOW = 280


def pl_color(value: float) -> str:
    if value > 0.005:
        return PROFIT
    if value < -0.005:
        return LOSS
    return TEXT_MUTED


def result_color(result: str) -> str:
    r = (result or "").strip()
    if r == "Win":
        return PROFIT
    if r == "Loss":
        return LOSS
    if r == "Pending":
        return PENDING
    return TEXT_MUTED


def apply_theme(page: ft.Page) -> None:
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.padding = 0
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ACCENT,
            on_primary=BG,
            secondary=INFO,
            surface=SURFACE,
            on_surface=TEXT,
            outline=BORDER,
            error=LOSS,
        ),
    )


def card(
    content: ft.Control,
    *,
    padding: int = S4,
    expand: bool | int = False,
    fill: bool = True,
    accent: str | None = None,
) -> ft.Container:
    """Elevated surface. Optional left accent rail for hierarchy."""
    body = content
    if accent:
        body = ft.Row(
            [
                ft.Container(width=3, bgcolor=accent, border_radius=2),
                ft.Container(content=content, expand=True, padding=ft.padding.only(left=S3)),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            expand=True if expand else False,
        )
        pad = ft.padding.only(left=0, top=padding, right=padding, bottom=padding)
    else:
        pad = padding
    return ft.Container(
        content=body,
        bgcolor=SURFACE_ELEV if fill else "transparent",
        border=ft.border.all(1, BORDER_SOFT) if fill else None,
        border_radius=RADIUS,
        padding=pad,
        expand=expand,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def muted(text: str, size: int = 12) -> ft.Text:
    return ft.Text(text, size=size, color=TEXT_MUTED)


def num(text: str, *, color: str = TEXT, size: int = 22) -> ft.Text:
    return ft.Text(text, size=size, weight=ft.FontWeight.W_700, color=color, font_family="Consolas")


def section_label(text: str) -> ft.Text:
    return ft.Text(
        text.upper(),
        size=11,
        weight=ft.FontWeight.W_700,
        color=TEXT_MUTED,
        font_family="Consolas",
    )


def section_title(text: str) -> ft.Text:
    return ft.Text(text, size=15, weight=ft.FontWeight.W_700, color=TEXT)


def fmt_nok(x: float | None, signed: bool = False) -> str:
    if x is None:
        return "—"
    return f"{x:+.2f} NOK" if signed else f"{x:.2f} NOK"


def fmt_pct(x: float | None, signed: bool = False) -> str:
    if x is None:
        return "—"
    return f"{x * 100:+.1f}%" if signed else f"{x * 100:.1f}%"


def chip(text: str, *, color: str = ACCENT) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=11, weight=ft.FontWeight.W_600, color=color),
        bgcolor=SURFACE_2,
        border=ft.border.all(1, BORDER),
        border_radius=999,
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
    )


def pill(text: str, *, ok: bool = True) -> ft.Container:
    c = PROFIT if ok else LOSS
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(width=6, height=6, bgcolor=c, border_radius=99),
                ft.Text(text, size=11, weight=ft.FontWeight.W_700, color=c),
            ],
            spacing=6,
            tight=True,
        ),
        bgcolor=SURFACE_2,
        border=ft.border.all(1, BORDER),
        border_radius=999,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
    )


def metric(
    label: str,
    value: str,
    *,
    sub: str = "",
    color: str = TEXT,
    expand: bool = True,
    accent: str | None = None,
) -> ft.Container:
    """KPI tile with optional left accent strip."""
    rail = accent if accent is not None else color if color not in (TEXT, TEXT_MUTED) else ACCENT
    inner = ft.Column(
        [
            ft.Text(label.upper(), size=10, weight=ft.FontWeight.W_700, color=TEXT_DIM, font_family="Consolas"),
            num(value, color=color, size=22),
            muted(sub, 11) if sub else ft.Container(height=0),
        ],
        spacing=4,
        tight=True,
    )
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(width=3, bgcolor=rail, border_radius=2),
                ft.Container(content=inner, expand=True, padding=ft.padding.only(left=S3, top=2, bottom=2)),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=SURFACE_ELEV,
        border=ft.border.all(1, BORDER_SOFT),
        border_radius=RADIUS,
        padding=ft.padding.symmetric(horizontal=S3, vertical=S3),
        expand=expand,
        animate=ft.Animation(ANIM_FAST, ft.AnimationCurve.EASE_OUT),
        animate_scale=ft.Animation(ANIM_FAST, ft.AnimationCurve.EASE_OUT),
        scale=1.0,
        on_hover=_metric_hover,
    )


def _metric_hover(e: ft.ControlEvent) -> None:
    hovering = e.data == "true"
    e.control.scale = 1.015 if hovering else 1.0
    e.control.border = ft.border.all(1, ACCENT if hovering else BORDER_SOFT)
    try:
        e.control.update()
    except Exception:
        pass


def page_header(title: str, subtitle: str = "", trailing: ft.Control | None = None) -> ft.Control:
    left = ft.Column(
        [
            ft.Text(title, size=24, weight=ft.FontWeight.W_800, color=TEXT),
            muted(subtitle, 12) if subtitle else ft.Container(height=0),
        ],
        spacing=4,
        tight=True,
        expand=True,
    )
    return ft.Container(
        content=ft.Row(
            [left] + ([trailing] if trailing else []),
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(bottom=S4),
    )


def hero_block(
    title: str,
    value: str,
    *,
    sub: str = "",
    color: str = ACCENT,
    trailing: ft.Control | None = None,
) -> ft.Control:
    """Large overview hero (equity / era P/L)."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(title.upper(), size=11, weight=ft.FontWeight.W_700, color=TEXT_DIM, font_family="Consolas"),
                        num(value, color=color, size=36),
                        muted(sub, 12) if sub else ft.Container(height=0),
                    ],
                    spacing=4,
                    tight=True,
                    expand=True,
                ),
            ]
            + ([trailing] if trailing else []),
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=SURFACE_ELEV,
        border=ft.border.all(1, BORDER),
        border_radius=RADIUS_LG,
        padding=S5,
    )


# Back-compat aliases
def kpi_value(text: str, color: str = TEXT, size: int = 26) -> ft.Text:
    return num(text, color=color, size=size)


def status_pill(text: str, *, ok: bool = True) -> ft.Container:
    return pill(text, ok=ok)


def metric_card(
    label: str,
    value: str,
    *,
    sub: str = "",
    color: str = TEXT,
    icon=None,
    expand: bool = True,
) -> ft.Container:
    return metric(label, value, sub=sub, color=color, expand=expand)
