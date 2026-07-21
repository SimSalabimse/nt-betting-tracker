from __future__ import annotations

import subprocess
import sys

import flet as ft

from desktop.components.layout import scroll_page, two_col
from desktop.components.widgets import place_slip_panel
from desktop.services.state_service import StateService
from desktop.theme import (
    ACCENT,
    BG,
    BORDER,
    SURFACE_2,
    card,
    muted,
    page_header,
    section_label,
)


def _parse_place_slip_md(text: str) -> tuple[list[dict], str]:
    """Extract bets + meta line from PLACE_THESE markdown."""
    meta = ""
    bets: list[dict] = []
    if not text or text.strip().startswith("_No place"):
        return [], meta
    for line in text.splitlines():
        if line.startswith("Phase ") or "Equity" in line and "Phase" in line:
            meta = line.replace("**", "").strip()
            continue
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 5:
            continue
        if parts[0] in ("#", "—") or parts[0].startswith("-") or "Match" in parts[0]:
            continue
        if parts[1].upper().startswith("NO BET"):
            continue
        try:
            stake = float(str(parts[4]).replace(",", "."))
        except ValueError:
            continue
        try:
            odds = float(str(parts[3]).replace(",", "."))
        except ValueError:
            odds = parts[3]
        ev = parts[5] if len(parts) > 5 else ""
        grade = parts[6] if len(parts) > 6 else ""
        band = parts[7] if len(parts) > 7 else ""
        bets.append(
            {
                "match": parts[1],
                "selection": parts[2],
                "decimal_odds": odds,
                "stake_nok": stake,
                "ev": ev,
                "grade": grade,
                "odds_band": band,
            }
        )
    return bets, meta


def _pending_as_slip(svc: StateService) -> list[dict]:
    """Fallback: today's pending rows as place cards."""
    from datetime import date

    today = date.today().isoformat()
    out = []
    for r in svc.state.pending_rows():
        if (r.get("date") or "") != today:
            continue
        out.append(
            {
                "match": r.get("match"),
                "selection": r.get("selection"),
                "decimal_odds": r.get("decimal_odds"),
                "stake_nok": r.get("stake_nok"),
                "grade": r.get("research_grade"),
                "odds_band": r.get("odds_band"),
                "ev": "",
            }
        )
    return out


def build_workflow(svc: StateService, page: ft.Page) -> ft.Control:
    inbox_list = ft.Column(spacing=3)
    outbox_list = ft.Column(spacing=3)
    slip_host = ft.Container()

    def refresh() -> None:
        inbox_list.controls = [muted(f"· {f.name}") for f in svc.inbox_files()] or [muted("(empty)")]
        outbox_list.controls = [muted(f"· {f.name}") for f in svc.outbox_files()[:16]] or [muted("(empty)")]
        text = svc.place_slip_text()
        bets, meta = _parse_place_slip_md(text)
        if not bets:
            bets = _pending_as_slip(svc)
            if bets and not meta:
                st = svc.state
                meta = (
                    f"Phase {st.phase.get('phase_id')} · Equity {float(st.bankroll.get('equity_nok') or 0):.2f} · "
                    f"from today's pending"
                )
        slip_host.content = place_slip_panel(bets, title="Place slip", meta=meta)

    refresh()

    def open_dir(rel: str):
        def _h(_e):
            p = svc.root / rel
            p.mkdir(parents=True, exist_ok=True)
            subprocess.Popen(["explorer", str(p)] if sys.platform == "win32" else ["xdg-open", str(p)])

        return _h

    btn = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=10)

    return scroll_page(
        page_header("Workflow", "NT Oddsen .txt paste → recommend → place → settle"),
        ft.Row(
            [
                ft.OutlinedButton("Inbox folder", icon=ft.Icons.FOLDER_OPEN_ROUNDED, on_click=open_dir("inbox"), style=btn),
                ft.OutlinedButton("Outbox folder", icon=ft.Icons.FOLDER_OPEN_ROUNDED, on_click=open_dir("outbox"), style=btn),
                ft.FilledButton(
                    "Refresh",
                    icon=ft.Icons.REFRESH_ROUNDED,
                    on_click=lambda e: (refresh(), page.update()),
                    style=ft.ButtonStyle(bgcolor=ACCENT, color=BG, shape=ft.RoundedRectangleBorder(radius=8)),
                ),
            ],
            spacing=8,
            wrap=True,
        ),
        two_col(
            card(
                ft.Column(
                    [
                        section_label("Inbox"),
                        ft.Container(
                            content=inbox_list,
                            bgcolor=SURFACE_2,
                            padding=12,
                            border_radius=8,
                            border=ft.border.all(1, BORDER),
                        ),
                        muted("python run_nt.py recommend --odds inbox/odds_….txt", 11),
                        muted("python run_nt.py settle --results inbox/results.txt", 11),
                    ],
                    spacing=8,
                    tight=True,
                )
            ),
            card(
                ft.Column(
                    [
                        section_label("Outbox"),
                        ft.Container(
                            content=outbox_list,
                            bgcolor=SURFACE_2,
                            padding=12,
                            border_radius=8,
                            border=ft.border.all(1, BORDER),
                        ),
                    ],
                    spacing=8,
                    tight=True,
                )
            ),
        ),
        slip_host,
        spacing=16,
    )
