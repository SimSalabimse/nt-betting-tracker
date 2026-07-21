from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import flet as ft

from desktop.components.layout import scroll_page, two_col
from desktop.services.state_service import StateService, is_valid_project_root
from desktop.theme import (
    ACCENT,
    BG,
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
    pill,
    section_label,
)


def build_settings(svc: StateService, page: ft.Page, on_root_changed) -> ft.Control:
    st = svc.state
    root_field = ft.TextField(
        label="Project root",
        value=str(svc.root),
        expand=True,
        dense=True,
        border_color=BORDER,
        color=TEXT,
        focused_border_color=ACCENT,
    )
    status = ft.Text("", size=12, color=TEXT_MUTED)

    def apply_root(_e):
        p = Path(root_field.value or "").expanduser()
        if not is_valid_project_root(p):
            status.value = "Need config.yaml and data/bets.csv"
            status.color = LOSS
            page.update()
            return
        try:
            svc.set_root(p)
            on_root_changed()
            status.value = f"Using {p}"
            status.color = PROFIT
        except Exception as ex:  # noqa: BLE001
            status.value = str(ex)
            status.color = LOSS
        page.update()

    def open_dir(rel: str):
        def _h(_e):
            p = svc.root / rel
            p.mkdir(parents=True, exist_ok=True)
            subprocess.Popen(["explorer", str(p)] if sys.platform == "win32" else ["xdg-open", str(p)])

        return _h

    btn = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=10)
    root_ok = is_valid_project_root(svc.root)
    b = st.bankroll or {}
    risk = st.risk or {}
    phase = st.phase or {}
    n_rows = len(st.rows or [])
    n_pend = len(st.pending_rows()) if hasattr(st, "pending_rows") else 0

    return scroll_page(
        page_header("Settings", "Local-only · no cloud · same engines as CLI"),
        card(
            ft.Column(
                [
                    section_label("Project root"),
                    ft.Row(
                        [
                            root_field,
                            ft.FilledButton(
                                "Apply",
                                on_click=apply_root,
                                style=ft.ButtonStyle(
                                    bgcolor=ACCENT, color=BG, shape=ft.RoundedRectangleBorder(radius=8)
                                ),
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            pill("ROOT OK" if root_ok else "ROOT INVALID", ok=root_ok),
                            chip(f"{n_rows} ledger rows"),
                            chip(f"{n_pend} pending"),
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                    status,
                    muted("Folder must contain config.yaml and data/bets.csv"),
                ],
                spacing=10,
                tight=True,
            )
        ),
        two_col(
            card(
                ft.Column(
                    [
                        section_label("Live snapshot"),
                        muted(f"Equity {fmt_nok(float(b.get('equity_nok') or 0))}"),
                        muted(f"Phase {phase.get('phase_id')} · {phase.get('label')}"),
                        muted(
                            f"Daily cap {fmt_nok(float(risk.get('daily_risk_cap_nok') or 0))} · "
                            f"remaining {fmt_nok(float(risk.get('remaining_risk_nok') or 0))}"
                        ),
                        muted(f"Can bet: {'yes' if risk.get('can_bet') else 'no (risk full)'}"),
                        muted(f"Last bankroll update: {st.updated_at or '—'}"),
                        muted(f"Analytics range: {st.range_label} ({st.range_from or '…'} → {st.range_to or '…'})"),
                    ],
                    spacing=6,
                    tight=True,
                )
            ),
            card(
                ft.Column(
                    [
                        section_label("Quick folders"),
                        ft.Row(
                            [
                                ft.OutlinedButton("Inbox", icon=ft.Icons.INBOX_ROUNDED, on_click=open_dir("inbox"), style=btn),
                                ft.OutlinedButton("Outbox", icon=ft.Icons.OUTBOX_ROUNDED, on_click=open_dir("outbox"), style=btn),
                                ft.OutlinedButton("Data", icon=ft.Icons.STORAGE_ROUNDED, on_click=open_dir("data"), style=btn),
                                ft.OutlinedButton("Evidence", icon=ft.Icons.SCIENCE_ROUNDED, on_click=open_dir("evidence"), style=btn),
                            ],
                            spacing=8,
                            wrap=True,
                        ),
                        muted("Open local folders in Explorer — no cloud sync"),
                    ],
                    spacing=10,
                    tight=True,
                )
            ),
        ),
        card(
            ft.Column(
                [
                    section_label("Workflow cheat-sheet"),
                    muted("1. Paste Oddsen board → inbox/odds_….txt"),
                    muted("2. python run_nt.py recommend --odds inbox/odds_….txt"),
                    muted("3. Place bets from outbox/PLACE_THESE.md (or Workflow tab)"),
                    muted("4. Drop results → inbox/results.txt → python run_nt.py settle --results …"),
                    muted("5. Refresh this desktop app to reload equity / phase / risk"),
                ],
                spacing=6,
                tight=True,
            )
        ),
        card(
            ft.Column(
                [
                    section_label("About"),
                    ft.Text("NT Betting Tracker Desktop", size=14, weight=ft.FontWeight.W_600, color=TEXT),
                    muted("Same engines as CLI · fully offline · local files only"),
                    muted(f"Root: {svc.root}"),
                    muted("UI: Flet · engines: nt/ · ledger: data/bets.csv"),
                ],
                spacing=6,
                tight=True,
            )
        ),
        spacing=16,
    )
