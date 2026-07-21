from __future__ import annotations

import flet as ft

from desktop.theme import ACCENT, BG, BORDER, SURFACE_2, SURFACE_ELEV, TEXT, TEXT_DIM, TEXT_MUTED
from nt.analytics import DATE_RANGE_PRESETS


def _chip_hover(e: ft.ControlEvent) -> None:
    hovering = e.data == "true"
    active = bool(getattr(e.control, "data", None) == "active")
    if active:
        e.control.scale = 1.02 if hovering else 1.0
    else:
        e.control.scale = 1.03 if hovering else 1.0
        e.control.border = ft.border.all(1, ACCENT if hovering else BORDER)
    try:
        e.control.update()
    except Exception:
        pass


def build_range_chips(
    active_key: str,
    on_change,
    *,
    range_from: str | None = None,
    range_to: str | None = None,
) -> ft.Control:
    """Segmented date-range control (1d / 3d / 1w / 2w / 1m / 3m / all)."""
    chips: list[ft.Control] = []
    for key, label, _days in DATE_RANGE_PRESETS:
        active = key == active_key

        def _click(_e, k=key):
            on_change(k)

        chips.append(
            ft.Container(
                content=ft.Text(
                    label,
                    size=11,
                    weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500,
                    color=BG if active else TEXT_MUTED,
                ),
                bgcolor=ACCENT if active else "transparent",
                border=ft.border.all(1, ACCENT if active else "transparent"),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=11, vertical=6),
                ink=True,
                on_click=_click,
                on_hover=_chip_hover,
                data="active" if active else "idle",
                animate=ft.Animation(140, ft.AnimationCurve.EASE_OUT),
                animate_scale=ft.Animation(140, ft.AnimationCurve.EASE_OUT),
                scale=1.0,
                tooltip=f"Show stats for: {label}",
            )
        )

    span = ""
    if range_from or range_to:
        span = f"{range_from or '…'}  →  {range_to or '…'}"

    return ft.Container(
        content=ft.Row(
            [
                ft.Text("RANGE", size=10, weight=ft.FontWeight.W_700, color=TEXT_DIM, font_family="Consolas"),
                ft.Container(
                    content=ft.Row(chips, spacing=2, tight=True),
                    bgcolor=SURFACE_2,
                    border=ft.border.all(1, BORDER),
                    border_radius=8,
                    padding=3,
                ),
                ft.Text(span, size=11, color=TEXT_MUTED, font_family="Consolas") if span else ft.Container(),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=SURFACE_ELEV,
        border=ft.border.all(1, BORDER),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )
