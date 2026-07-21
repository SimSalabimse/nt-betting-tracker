from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import flet as ft

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import nt_bootstrap  # noqa: F401

from desktop.components.range_bar import build_range_chips
from desktop.components.widgets import risk_status_label
from desktop.services.state_service import StateService
from desktop.theme import (
    ACCENT,
    BG,
    BORDER,
    CONTENT_PAD,
    LOSS,
    NAV_WIDTH,
    PENDING,
    PROFIT,
    RAIL,
    SURFACE,
    SURFACE_2,
    TEXT,
    TEXT_DIM,
    TEXT_MUTED,
    apply_theme,
    chip,
    fmt_nok,
    muted,
    num,
    pill,
)
from desktop.views.book import BookView
from desktop.views.desk import DeskView
from desktop.views.lab import LabView
from desktop.views.settings import build_settings


class NTDesktopApp:
    """
    Modes: Desk (operate) · Book (stats/tickets) · Lab (learning) · Setup
    Range chips only on Book.
    """

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        apply_theme(page)
        page.title = "NT Tracker"
        page.window.width = 1320
        page.window.height = 840
        page.window.min_width = 960
        page.window.min_height = 620

        self.svc = StateService()
        self.route = "desk"
        self.content_host = ft.Container(expand=True)
        self.content_pad = ft.Container(
            content=self.content_host,
            expand=True,
            padding=CONTENT_PAD,
            bgcolor=BG,
        )
        self.status = ft.Text("", size=10, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
        self.equity_label = num("—", color=ACCENT, size=20)
        self.meta_chips = ft.Row(spacing=6, scroll=ft.ScrollMode.AUTO, tight=True)
        self.range_host = ft.Container(visible=False)
        self._nav: dict[str, ft.Control] = {}
        self._nav_labels: dict[str, ft.Text] = {}

        self.desk = DeskView(self.svc, page, on_state_changed=self._on_desk_changed)
        self.book = BookView(self.svc, page)
        self.lab = LabView()

        try:
            self.svc.reload(write_state=True)
            self._sync_header()
            self.status.value = "Ready"
        except Exception as e:  # noqa: BLE001
            self.status.value = str(e)[:40]
            self.status.color = LOSS

        page.add(self._shell())
        self._refresh_range_bar()
        self._render()
        self.page.run_task(self._auto_refresh_loop)

    def _on_desk_changed(self) -> None:
        self._sync_header()
        self._refresh_range_bar()
        # Stay on desk; refresh header only — desk already refreshed its panels
        try:
            self.page.update()
        except Exception:
            pass

    def _sync_header(self) -> None:
        st = self.svc.state
        b = st.bankroll
        pl = float(b.get("realized_pl_nok") or 0)
        self.equity_label.value = fmt_nok(float(b.get("equity_nok") or 0))
        pend = int(b.get("pending_count") or 0)
        can = bool(st.risk.get("can_bet"))
        pl_c = PROFIT if pl > 0.005 else (LOSS if pl < -0.005 else TEXT_MUTED)
        chips: list[ft.Control] = [
            chip(f"Phase {st.phase.get('phase_id', '—')}"),
            chip(f"Era {fmt_nok(pl, signed=True)}", color=pl_c),
            chip(f"{int(b.get('settled_count') or 0)} settled"),
        ]
        if self.route == "book":
            chips.append(chip(f"Window · {st.range_label}", color=ACCENT))
        if pend:
            chips.append(
                chip(f"{pend} open · {fmt_nok(float(b.get('pending_at_risk_nok') or 0))}", color=PENDING)
            )
        chips.append(chip(risk_status_label(can), color=ACCENT if can else LOSS))
        if st.errors:
            chips.append(chip(f"{len(st.errors)} ledger errs", color=LOSS))
        self.meta_chips.controls = chips

    def _on_range(self, key: str) -> None:
        self.svc.set_range(key)
        self._sync_header()
        self._refresh_range_bar()
        self._render()
        n = self.svc.state.dive.get("period_n", 0)
        self.status.value = f"Window {self.svc.state.range_label} · {n}"
        self.status.color = TEXT_MUTED
        self.page.update()

    def _refresh_range_bar(self) -> None:
        st = self.svc.state
        show = self.route == "book"
        self.range_host.visible = show
        if show:
            self.range_host.content = build_range_chips(
                st.range_key,
                self._on_range,
                range_from=st.range_from,
                range_to=st.range_to,
            )
        else:
            self.range_host.content = ft.Container(height=0)

    def _nav_btn(self, key: str, label: str, icon) -> ft.Control:
        def go(_):
            self.route = key
            self._render()

        active = self.route == key

        def _nav_hover(e: ft.ControlEvent) -> None:
            hovering = e.data == "true"
            is_active = e.control.data == self.route
            if not is_active:
                e.control.bgcolor = SURFACE_2 if hovering else None
            try:
                e.control.update()
            except Exception:
                pass

        label_ctrl = ft.Text(
            label,
            size=10,
            color=ACCENT if active else TEXT_DIM,
            weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500,
            text_align=ft.TextAlign.CENTER,
        )
        self._nav_labels[key] = label_ctrl

        c = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(icon, size=22, color=ACCENT if active else TEXT_MUTED),
                    label_ctrl,
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            padding=ft.padding.symmetric(vertical=12, horizontal=6),
            border_radius=10,
            bgcolor=SURFACE_2 if active else None,
            border=ft.border.only(left=ft.BorderSide(3, ACCENT)) if active else None,
            ink=True,
            on_click=go,
            on_hover=_nav_hover,
            data=key,
            width=NAV_WIDTH - 16,
            animate=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
        )
        self._nav[key] = c
        return c

    def _shell(self) -> ft.Control:
        nav = ft.Container(
            width=NAV_WIDTH,
            bgcolor=RAIL,
            border=ft.border.only(right=ft.BorderSide(1, BORDER)),
            padding=ft.padding.symmetric(horizontal=8, vertical=16),
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "NT",
                                    size=18,
                                    weight=ft.FontWeight.W_900,
                                    color=ACCENT,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Text(
                                    "DESK",
                                    size=9,
                                    weight=ft.FontWeight.W_700,
                                    color=TEXT_DIM,
                                    text_align=ft.TextAlign.CENTER,
                                    font_family="Consolas",
                                ),
                            ],
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            tight=True,
                        ),
                        padding=ft.padding.only(bottom=20),
                    ),
                    self._nav_btn("desk", "Desk", ft.Icons.DESKTOP_WINDOWS_ROUNDED),
                    self._nav_btn("book", "Book", ft.Icons.MENU_BOOK_ROUNDED),
                    self._nav_btn("lab", "Lab", ft.Icons.SCIENCE_ROUNDED),
                    self._nav_btn("setup", "Setup", ft.Icons.TUNE_ROUNDED),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED,
                        icon_color=ACCENT,
                        tooltip="Refresh ledger + learning",
                        on_click=self._on_refresh,
                    ),
                    self.status,
                ],
                spacing=4,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        header = ft.Container(
            bgcolor=SURFACE,
            border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
            padding=ft.padding.symmetric(horizontal=CONTENT_PAD, vertical=12),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        "EQUITY · LIVE",
                                        size=10,
                                        weight=ft.FontWeight.W_700,
                                        color=TEXT_DIM,
                                        font_family="Consolas",
                                    ),
                                    self.equity_label,
                                ],
                                spacing=0,
                                tight=True,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    "LIVE",
                                    size=10,
                                    weight=ft.FontWeight.W_800,
                                    color=ACCENT,
                                    font_family="Consolas",
                                ),
                                bgcolor=SURFACE_2,
                                border=ft.border.all(1, ACCENT),
                                border_radius=6,
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            ),
                            ft.Container(content=self.meta_chips, expand=True),
                            pill("LOCAL", ok=True),
                        ],
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.range_host,
                ],
                spacing=12,
                tight=True,
            ),
        )

        return ft.Row(
            [nav, ft.Column([header, self.content_pad], spacing=0, expand=True)],
            spacing=0,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    async def _auto_refresh_loop(self) -> None:
        last = ""
        live_bright = True
        while True:
            await asyncio.sleep(1.4)
            try:
                live_bright = not live_bright
                self.equity_label.color = ACCENT if live_bright else "#C48912"
            except Exception:
                pass

            self._pulse_ticks = getattr(self, "_pulse_ticks", 0) + 1
            if self._pulse_ticks % 32 == 0:
                try:
                    self.svc.reload(write_state=False)
                    st = self.svc.state
                    learn_ts = (st.learning or {}).get("updated_at") or ""
                    sig = (
                        f"{st.bankroll.get('equity_nok')}|{st.bankroll.get('pending_count')}|"
                        f"{len(st.rows)}|{st.phase.get('phase_id')}|{st.range_key}|"
                        f"{st.dive.get('period_n')}|{learn_ts}"
                    )
                    if sig != last:
                        last = sig
                        self._sync_header()
                        self._refresh_range_bar()
                        self.status.value = "Synced"
                        self._render()
                        continue
                except Exception:
                    pass
            try:
                self.page.update()
            except Exception:
                pass

    def _on_refresh(self, _e=None) -> None:
        try:
            self.svc.reload(write_state=True)
            self._sync_header()
            self._refresh_range_bar()
            self.status.value = "Refreshed"
            self.status.color = TEXT_MUTED
        except Exception as ex:  # noqa: BLE001
            self.status.value = str(ex)[:36]
            self.status.color = LOSS
        self._render()

    def _paint_nav(self) -> None:
        for key, btn in self._nav.items():
            if not isinstance(btn, ft.Container):
                continue
            active = key == self.route
            btn.bgcolor = SURFACE_2 if active else None
            btn.border = ft.border.only(left=ft.BorderSide(3, ACCENT)) if active else None
            if isinstance(btn.content, ft.Column) and btn.content.controls:
                ic = btn.content.controls[0]
                if isinstance(ic, ft.Icon):
                    ic.color = ACCENT if active else TEXT_MUTED
            lab = self._nav_labels.get(key)
            if lab:
                lab.color = ACCENT if active else TEXT_DIM
                lab.weight = ft.FontWeight.W_700 if active else ft.FontWeight.W_500

    def _render(self) -> None:
        self._paint_nav()
        self._sync_header()
        self._refresh_range_bar()
        st = self.svc.state
        if self.route == "desk":
            body = self.desk.build()
        elif self.route == "book":
            body = self.book.build(st)
        elif self.route == "lab":
            body = self.lab.build(st)
        elif self.route == "setup":
            body = build_settings(self.svc, self.page, on_root_changed=self._on_refresh)
        else:
            body = self.desk.build()
        self.content_host.content = body
        self.page.update()


def main() -> None:
    ft.app(target=lambda page: NTDesktopApp(page))


if __name__ == "__main__":
    main()
