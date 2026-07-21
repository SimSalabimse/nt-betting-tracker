from __future__ import annotations

import flet as ft

from desktop.theme import (
    BORDER_SOFT,
    CHART_M,
    S2,
    S3,
    S4,
    SURFACE_ELEV,
    TEXT,
    TEXT_MUTED,
    card,
    section_label,
    section_title,
)


def data_card(
    title: str,
    body: ft.Control,
    *,
    subtitle: str = "",
    trailing: ft.Control | None = None,
    height: int | None = None,
) -> ft.Control:
    head = ft.Row(
        [
            ft.Column(
                [
                    section_label(title),
                    ft.Text(subtitle, size=11, color=TEXT_MUTED) if subtitle else ft.Container(height=0),
                ],
                spacing=2,
                tight=True,
                expand=True,
            )
        ]
        + ([trailing] if trailing else []),
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    inner: ft.Control = body
    if height:
        inner = ft.Container(content=body, height=height, clip_behavior=ft.ClipBehavior.HARD_EDGE)
    return card(
        ft.Column([head, ft.Container(height=S3), inner], spacing=0, tight=True),
        padding=S4,
    )


def chart_card(title: str, chart: ft.Control, *, subtitle: str = "", height: int = CHART_M) -> ft.Control:
    return data_card(title, chart, subtitle=subtitle, height=height)


def scroll_page(*controls: ft.Control, spacing: int = 18) -> ft.Control:
    """Scrollable page body. Prefer plain Columns over ResponsiveRow inside this."""
    return ft.Column(
        list(controls),
        spacing=spacing,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def two_col(left: ft.Control, right: ft.Control, *, left_w: int = 7, right_w: int = 5) -> ft.Control:
    """
    Side-by-side on wide windows via Row (not ResponsiveRow).

    ResponsiveRow inside scroll Columns often collapses height on Windows/Flet
    and leaves orphan fragments (Learning bug). Plain Row+expand is reliable.
    """
    return ft.Row(
        [
            ft.Container(content=left, expand=left_w),
            ft.Container(content=right, expand=right_w),
        ],
        spacing=S4,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def three_col(a: ft.Control, b: ft.Control, c: ft.Control) -> ft.Control:
    return ft.Row(
        [
            ft.Container(content=a, expand=True),
            ft.Container(content=b, expand=True),
            ft.Container(content=c, expand=True),
        ],
        spacing=S4,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def metrics_row(items: list[ft.Control]) -> ft.Control:
    return ft.Row(
        [ft.Container(content=m, expand=True) for m in items],
        spacing=S3,
    )


def panel_surface(content: ft.Control, *, expand: bool = False) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=SURFACE_ELEV,
        border=ft.border.all(1, BORDER_SOFT),
        border_radius=10,
        padding=S4,
        expand=expand,
    )


def segment_tabs(
    labels: list[str],
    contents: list[ft.Control],
    *,
    selected: int = 0,
) -> ft.Control:
    """Custom segmented control (avoids default Flet Tabs chrome)."""
    assert len(labels) == len(contents)
    host = ft.Container(content=contents[selected] if contents else ft.Container(), expand=True)
    buttons: list[ft.Control] = []

    def make_go(i: int):
        def go(_e=None):
            host.content = contents[i]
            for j, btn in enumerate(buttons):
                if isinstance(btn, ft.Container):
                    active = j == i
                    btn.bgcolor = "#E8A317" if active else SURFACE_ELEV
                    if isinstance(btn.content, ft.Text):
                        btn.content.color = "#0B0D12" if active else TEXT_MUTED
                        btn.content.weight = ft.FontWeight.W_700 if active else ft.FontWeight.W_500
            try:
                host.update()
                for btn in buttons:
                    btn.update()
            except Exception:
                pass

        return go

    for i, lab in enumerate(labels):
        active = i == selected
        buttons.append(
            ft.Container(
                content=ft.Text(
                    lab,
                    size=12,
                    weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500,
                    color="#0B0D12" if active else TEXT_MUTED,
                ),
                bgcolor="#E8A317" if active else SURFACE_ELEV,
                border=ft.border.all(1, BORDER_SOFT),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
                ink=True,
                on_click=make_go(i),
            )
        )

    return ft.Column(
        [
            ft.Container(
                content=ft.Row(buttons, spacing=6),
                padding=ft.padding.only(bottom=S2),
            ),
            host,
        ],
        spacing=8,
        expand=True,
    )
