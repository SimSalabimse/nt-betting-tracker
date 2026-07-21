from __future__ import annotations

"""
Book — understand form: analytics + tickets (range-scoped).
Preserves segment tab across soft reloads.
Forensic: Stats bars/tables drill into Tickets with bet_ids grain.
"""

import flet as ft

from desktop.services.state_service import AppState, StateService
from desktop.theme import ACCENT, LOSS, TEXT_MUTED, page_header
from desktop.views.analytics import build_analytics
from desktop.views.bets import BetsView


class BookView:
    def __init__(self, svc: StateService, page: ft.Page) -> None:
        self.svc = svc
        self.page = page
        self.bets = BetsView(svc, page)
        self._tab = 0
        self.root = ft.Column(expand=True, spacing=8)
        self._status = ft.Text("", size=11, color=TEXT_MUTED)

    def drill(self, dim: str, value: str, label: str = "") -> None:
        """Forensic path: group → bet_ids → Tickets tab."""
        pretty = label or f"{dim}: {value}"
        ids = self.svc.drill_forensic(dim, value, pretty)
        if not ids:
            self._status.value = f"No tickets for {pretty}"
            self._status.color = LOSS
            try:
                self._status.update()
            except Exception:
                pass
            return
        self._status.value = f"Forensic · {pretty} · {len(ids)} bets"
        self._status.color = ACCENT
        self._tab = 1  # Tickets
        # Rebuild tickets with forensic filter
        try:
            self.bets.apply_filters()
        except Exception:
            pass
        # Force full book rebuild so tab host switches
        st = self.svc.state
        self.build(st)
        try:
            self.page.update()
        except Exception:
            pass

    def build(self, state: AppState) -> ft.Control:
        analytics = build_analytics(state, on_drill=self.drill)
        tickets = self.bets.build(state)

        labels = ["Stats", "Tickets"]
        contents = [analytics, tickets]

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
                            btn.content.weight = (
                                ft.FontWeight.W_700 if active else ft.FontWeight.W_500
                            )
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

        st = state
        n_forensic = len(st.forensic_bet_ids or [])
        forensic_note = (
            f" · forensic {n_forensic} ids · {st.forensic_label}"
            if n_forensic
            else ""
        )
        header = page_header(
            "Book",
            f"Stats window · {st.range_label} · {st.range_from or '…'} → {st.range_to or '…'} · "
            f"{int((st.dive or {}).get('period_n') or 0)} settled in range{forensic_note}",
        )
        self.root.controls = [
            header,
            ft.Row([*buttons, ft.Container(expand=True), self._status], spacing=6),
            host,
        ]
        return self.root
