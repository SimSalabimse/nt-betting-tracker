from __future__ import annotations

"""Lab — improve process: learning mults, lessons, edges feed."""

from pathlib import Path

import flet as ft

from desktop.components.layout import scroll_page, segment_tabs
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
    pl_color,
    section_label,
)
from desktop.views.learnings import build_learnings


def _edges_panel(root: Path, limit: int = 25) -> ft.Control:
    path = root / "data" / "edges.jsonl"
    if not path.is_file():
        return card(
            ft.Column(
                [
                    section_label("Edges log"),
                    muted("No data/edges.jsonl yet — settle bets to append lessons."),
                ],
                spacing=6,
            )
        )
    rows: list[ft.Control] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    import json

    parsed = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    for row in reversed(parsed):
        res = str(row.get("result") or "")
        col = PROFIT if res == "Win" else (LOSS if res == "Loss" else TEXT_MUTED)
        try:
            pl = float(row.get("p_l") or row.get("p_l_nok") or 0)
        except (TypeError, ValueError):
            pl = 0.0
        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        chip(res[:4].upper() if res else "—", color=col),
                        ft.Text(
                            f"{row.get('date') or ''}  {(row.get('match') or row.get('selection') or '')[:40]}",
                            size=12,
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
    return card(
        ft.Column(
            [
                section_label(f"Edges log (last {len(rows)})"),
                muted("From data/edges.jsonl · settlement lessons", 11),
                ft.Container(height=6),
                *(rows or [muted("Empty edges log")]),
            ],
            spacing=4,
            tight=True,
        )
    )


class LabView:
    def __init__(self) -> None:
        self._tab = 0
        self.root = ft.Column(expand=True, spacing=8)

    def build(self, state: AppState) -> ft.Control:
        learning_body = build_learnings(state)
        edges = scroll_page(
            page_header("Edges", "Settlement lesson stream (append-only)"),
            _edges_panel(state.root),
            spacing=14,
        )

        # Two top modes so edges aren't buried inside learnings density
        labels = ["Learning", "Edges"]
        contents = [learning_body, edges]
        host = ft.Container(content=contents[self._tab], expand=True)
        buttons: list[ft.Control] = []

        def make_go(i: int):
            def go(_e=None):
                self._tab = i
                host.content = contents[i]
                for j, btn in enumerate(buttons):
                    if isinstance(btn, ft.Container):
                        active = j == i
                        btn.bgcolor = "#E8A317" if active else "#171C27"
                        if isinstance(btn.content, ft.Text):
                            btn.content.color = "#0B0D12" if active else "#8B95A8"
                try:
                    host.update()
                    for btn in buttons:
                        btn.update()
                except Exception:
                    pass

            return go

        for i, lab in enumerate(labels):
            active = i == self._tab
            buttons.append(
                ft.Container(
                    content=ft.Text(
                        lab,
                        size=12,
                        weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500,
                        color="#0B0D12" if active else "#8B95A8",
                    ),
                    bgcolor="#E8A317" if active else "#171C27",
                    border=ft.border.all(1, "#2C3548"),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    ink=True,
                    on_click=make_go(i),
                )
            )

        learn = state.learning or {}
        n_block = int((learn.get("summary") or {}).get("n_blocked_sports") or 0)
        header = page_header(
            "Lab",
            f"Process improvement · learning n={int((learn.get('summary') or {}).get('n_settled') or 0)} · "
            f"{n_block} soft-blocked sports",
        )
        self.root.controls = [header, ft.Row(buttons, spacing=6), host]
        return self.root
