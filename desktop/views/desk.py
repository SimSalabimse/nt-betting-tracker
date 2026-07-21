from __future__ import annotations

"""
Desk — Grok-first ops surface.

Primary: live risk, pending, place slip, rejects, receipt, hand-off paths for Grok.
Secondary (collapsed): local engine shortlist — not a substitute for Grok research.
"""

import subprocess
import sys
import threading
from pathlib import Path

import flet as ft

from desktop.components.layout import scroll_page
from desktop.components.widgets import phase_panel, place_slip_panel, risk_gauge
from desktop.services.state_service import StateService
from desktop.theme import (
    ACCENT,
    BG,
    BORDER,
    LOSS,
    PENDING,
    PROFIT,
    SURFACE_2,
    TEXT,
    TEXT_MUTED,
    card,
    chip,
    fmt_nok,
    muted,
    num,
    page_header,
    pill,
    section_label,
)
from desktop.views.workflow import _parse_place_slip_md, _pending_as_slip


class DeskView:
    def __init__(self, svc: StateService, page: ft.Page, on_state_changed=None) -> None:
        self.svc = svc
        self.page = page
        self.on_state_changed = on_state_changed
        self._busy = False
        self._engine_open = False
        self.status = muted("")
        self.odds_dd = ft.Dropdown(
            label="Odds file (inbox) — for Grok / engine",
            expand=True,
            dense=True,
            border_color=BORDER,
            color=TEXT,
            focused_border_color=ACCENT,
            text_size=13,
            options=[],
        )
        self.results_dd = ft.Dropdown(
            label="Results file (inbox)",
            expand=True,
            dense=True,
            border_color=BORDER,
            color=TEXT,
            focused_border_color=ACCENT,
            text_size=13,
            options=[],
        )
        self.path_hint = muted("", 11)
        self.slip_host = ft.Container()
        self.rejects_host = ft.Container()
        self.receipt_host = ft.Container()
        self.pending_host = ft.Container()
        self.risk_host = ft.Container()
        self.phase_host = ft.Container()
        self.engine_host = ft.Container(visible=False)
        self.root = ft.Column(expand=True, spacing=0)

    def _set_status(self, msg: str, *, err: bool = False) -> None:
        self.status.value = msg
        self.status.color = LOSS if err else TEXT_MUTED
        try:
            self.status.update()
        except Exception:
            pass

    def _refresh_file_options(self) -> None:
        odds = self.svc.inbox_odds_files()
        results = self.svc.inbox_results_files()
        self.odds_dd.options = [ft.dropdown.Option(str(p), p.name) for p in odds]
        self.results_dd.options = [ft.dropdown.Option(str(p), p.name) for p in results]
        if odds and (not self.odds_dd.value or self.odds_dd.value not in {str(p) for p in odds}):
            self.odds_dd.value = str(odds[0])
        if results and (
            not self.results_dd.value or self.results_dd.value not in {str(p) for p in results}
        ):
            pref = next((p for p in results if "result" in p.name.lower()), results[0])
            self.results_dd.value = str(pref)
        self._update_path_hint()

    def _update_path_hint(self) -> None:
        p = Path(self.odds_dd.value or "")
        if p.is_file():
            self.path_hint.value = f"Grok hand-off path: {p}"
        else:
            self.path_hint.value = "Select an odds file · paste board into inbox/ · ask Grok Build to research"
        try:
            self.path_hint.update()
        except Exception:
            pass

    def _open_path(self, path: Path) -> None:
        path = Path(path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _copy_odds_path(self) -> None:
        p = Path(self.odds_dd.value or "")
        if not p.is_file():
            self._set_status("Select a valid odds file first.", err=True)
            return
        try:
            self.page.set_clipboard(str(p.resolve()))
            self._set_status(f"Copied path · {p.name} — paste into Grok Build")
        except Exception:
            self._set_status(str(p.resolve()))

    def _pending_blotter(self) -> ft.Control:
        rows = self.svc.state.pending_rows()
        if not rows:
            return card(
                ft.Column(
                    [
                        section_label("Pending"),
                        muted("No open bets — empty book is fine."),
                        muted("After Grok research + place, Refresh to see pending here.", 11),
                    ],
                    spacing=6,
                    tight=True,
                )
            )
        items = []
        for r in rows:
            items.append(
                ft.Container(
                    content=ft.Row(
                        [
                            chip("PENDING", color=PENDING),
                            ft.Column(
                                [
                                    ft.Text(
                                        (r.get("match") or "")[:48],
                                        size=13,
                                        weight=ft.FontWeight.W_600,
                                        color=TEXT,
                                        no_wrap=True,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    muted(
                                        f"{r.get('date')} · {r.get('selection')} @ {r.get('decimal_odds')} · "
                                        f"{r.get('stake_nok')} NOK · {r.get('sport') or '?'} · "
                                        f"grade {r.get('research_grade') or '—'}",
                                        11,
                                    ),
                                ],
                                spacing=2,
                                tight=True,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=SURFACE_2,
                    border=ft.border.all(1, BORDER),
                    border_radius=8,
                    padding=10,
                )
            )
        at_risk = float(self.svc.state.bankroll.get("pending_at_risk_nok") or 0)
        return card(
            ft.Column(
                [
                    ft.Row(
                        [
                            section_label(f"Pending ({len(rows)})"),
                            chip(fmt_nok(at_risk), color=PENDING),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=6),
                    *items,
                ],
                spacing=6,
                tight=True,
            )
        )

    def _rejects_panel(self) -> ft.Control:
        text = self.svc.latest_rejects_text()
        if not text.strip():
            return card(
                ft.Column(
                    [
                        section_label("Rejects / cut list"),
                        muted("No REJECTS_*.md yet."),
                        muted("Appears after engine shortlist — or after Grok documents cuts.", 11),
                    ],
                    spacing=6,
                    tight=True,
                )
            )
        lines = [ln for ln in text.splitlines() if ln.strip()][:40]
        return card(
            ft.Column(
                [
                    section_label("Rejects / cut list"),
                    ft.Text(
                        "\n".join(lines),
                        size=11,
                        color=TEXT_MUTED,
                        font_family="Consolas",
                        selectable=True,
                    ),
                ],
                spacing=6,
                tight=True,
            )
        )

    def _receipt_panel(self) -> ft.Control:
        text = self.svc.latest_receipt_text()
        if not text.strip():
            return card(
                ft.Column(
                    [
                        section_label("Last settlement receipt"),
                        muted("No SETTLEMENT_RECEIPT.md yet."),
                        muted("After results land: settle here or via Grok → Refresh.", 11),
                    ],
                    spacing=6,
                    tight=True,
                )
            )
        lines = text.splitlines()[:28]
        return card(
            ft.Column(
                [
                    section_label("Last settlement receipt"),
                    ft.Text(
                        "\n".join(lines),
                        size=11,
                        color=TEXT_MUTED,
                        font_family="Consolas",
                        selectable=True,
                    ),
                ],
                spacing=6,
                tight=True,
            )
        )

    def _slip_panel(self) -> ft.Control:
        text = self.svc.place_slip_text()
        bets, meta = _parse_place_slip_md(text)
        if not bets:
            bets = _pending_as_slip(self.svc)
            if bets and not meta:
                st = self.svc.state
                meta = (
                    f"Phase {st.phase.get('phase_id')} · Equity "
                    f"{float(st.bankroll.get('equity_nok') or 0):.2f} · today's pending"
                )
        if not bets:
            return card(
                ft.Column(
                    [
                        section_label("Place slip"),
                        muted("No place slip yet."),
                        muted(
                            "Grok path: research odds → write evidence + PLACE_THESE / pending → Refresh.",
                            11,
                        ),
                    ],
                    spacing=6,
                    tight=True,
                )
            )
        return place_slip_panel(bets, title="Place slip", meta=meta)

    def _sync_panels(self) -> None:
        st = self.svc.state
        self.risk_host.content = risk_gauge(st)
        self.phase_host.content = phase_panel(st)
        self.pending_host.content = self._pending_blotter()
        self.slip_host.content = self._slip_panel()
        self.rejects_host.content = self._rejects_panel()
        self.receipt_host.content = self._receipt_panel()

    def _after_action(self) -> None:
        self._refresh_file_options()
        self._sync_panels()
        if self.on_state_changed:
            self.on_state_changed()
        try:
            self.page.update()
        except Exception:
            pass

    def _run_engine_shortlist(self, dry_run: bool) -> None:
        """Demoted: local engine only — not Grok research."""
        if self._busy:
            return
        path = Path(self.odds_dd.value or "")
        if not path.is_file():
            self._set_status("Select a valid odds file from inbox.", err=True)
            return
        self._busy = True
        self._set_status(f"Engine shortlist {'(dry-run)' if dry_run else ''}… {path.name}")

        def work():
            try:
                result = self.svc.run_recommend_odds(path, dry_run=dry_run)
                n = result.get("n_picked", 0)
                rej = result.get("n_rejects", 0)
                self._set_status(
                    f"Engine shortlist done · picked {n} · rejects {rej} · "
                    f"NOT full Grok research — review evidence packs"
                )
            except Exception as ex:  # noqa: BLE001
                self._set_status(str(ex), err=True)
            finally:
                self._busy = False
                self._after_action()

        threading.Thread(target=work, daemon=True).start()

    def _run_settle(self) -> None:
        if self._busy:
            return
        path = Path(self.results_dd.value or "")
        if not path.is_file():
            self._set_status("Select a valid results file from inbox.", err=True)
            return
        self._busy = True
        self._set_status(f"Settle running… {path.name}")

        def work():
            try:
                result = self.svc.run_settle_results(path)
                n = int(result.get("settled") or 0)
                errs = result.get("errors") or []
                if errs:
                    self._set_status(f"Settle finished with {len(errs)} error(s) · settled {n}", err=True)
                else:
                    self._set_status(f"Settle done · {n} matched · receipt + learning updated")
            except Exception as ex:  # noqa: BLE001
                self._set_status(str(ex), err=True)
            finally:
                self._busy = False
                self._after_action()

        threading.Thread(target=work, daemon=True).start()

    def _toggle_engine(self, _e=None) -> None:
        self._engine_open = not self._engine_open
        self.engine_host.visible = self._engine_open
        try:
            self.engine_host.update()
            self.page.update()
        except Exception:
            pass

    def build(self) -> ft.Control:
        self._refresh_file_options()
        self._sync_panels()
        st = self.svc.state
        can = bool((st.risk or {}).get("can_bet"))
        remaining = float((st.risk or {}).get("remaining_risk_nok") or 0)
        today_pl = float((st.risk or {}).get("today_realized_pl_nok") or 0)
        phase_id = str((st.phase or {}).get("phase_id") or "—")

        dive = st.dive or {}
        roll = dive.get("rolling_20") or []
        why = ""
        if roll:
            last = roll[-1]
            r_roi = last.get("rolling_roi")
            if r_roi is not None and float(r_roi) < 0:
                why = f"Form soft · rolling ROI {float(r_roi)*100:+.1f}% (count unlock needs ≥ 0%)"
            elif r_roi is not None:
                why = f"Rolling ROI {float(r_roi)*100:+.1f}%"
        reason = str((st.phase or {}).get("reason") or (st.phase or {}).get("note") or "")[:120]

        # Grok workflow card (PRIMARY)
        grok = card(
            ft.Column(
                [
                    section_label("Grok workflow (primary)"),
                    muted(
                        "You research odds with Grok Build. This desk tracks bankroll, risk, slips, and settlements.",
                        12,
                    ),
                    ft.Container(height=6),
                    ft.Text("1. Paste Oddsen board → inbox/", size=12, color=TEXT),
                    ft.Text("2. Select file · Copy path · research in Grok Build", size=12, color=TEXT),
                    ft.Text("3. Grok writes evidence + place list / pending", size=12, color=TEXT),
                    ft.Text("4. Place at Oddsen · drop results · Settle or ask Grok", size=12, color=TEXT),
                    ft.Text("5. Refresh — equity, learning, Book dossiers update", size=12, color=TEXT),
                    ft.Container(height=10),
                    self.odds_dd,
                    self.path_hint,
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Copy odds path",
                                icon=ft.Icons.CONTENT_COPY_ROUNDED,
                                on_click=lambda e: self._copy_odds_path(),
                                style=ft.ButtonStyle(bgcolor=ACCENT, color=BG),
                            ),
                            ft.OutlinedButton(
                                "Open inbox",
                                icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                                on_click=lambda e: self._open_path(self.svc.root / "inbox"),
                            ),
                            ft.OutlinedButton(
                                "Open outbox",
                                icon=ft.Icons.FOLDER_ROUNDED,
                                on_click=lambda e: self._open_path(self.svc.root / "outbox"),
                            ),
                            ft.OutlinedButton(
                                "Open evidence",
                                icon=ft.Icons.DESCRIPTION_ROUNDED,
                                on_click=lambda e: self._open_path(self.svc.root / "evidence"),
                            ),
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                    ft.Container(height=8),
                    self.results_dd,
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Settle results",
                                icon=ft.Icons.TASK_ALT_ROUNDED,
                                on_click=lambda e: self._run_settle(),
                                style=ft.ButtonStyle(bgcolor=PROFIT, color=BG),
                            ),
                            ft.OutlinedButton(
                                "Refresh desk",
                                icon=ft.Icons.REFRESH_ROUNDED,
                                on_click=lambda e: self._after_action(),
                            ),
                        ],
                        spacing=10,
                    ),
                    self.status,
                ],
                spacing=6,
                tight=True,
            ),
            accent=ACCENT,
        )

        live = card(
            ft.Column(
                [
                    section_label("Live pulse"),
                    ft.Row(
                        [
                            pill("CAN BET" if can else "RISK FULL", ok=can),
                            chip(f"Phase {phase_id}"),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=8),
                    muted("Remaining risk today", 11),
                    num(fmt_nok(remaining), color=ACCENT if can else LOSS, size=28),
                    muted(f"Today P/L {fmt_nok(today_pl, signed=True)}", 12),
                    muted(why or reason or "Phase engine is law", 11),
                    ft.Container(height=8),
                    muted(
                        f"Ledger errors: {len(st.errors)}" if st.errors else "Ledger validate: clean",
                        11,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
            accent=ACCENT if can else LOSS,
        )

        # Engine shortlist — demoted, collapsed by default
        self.engine_host.content = card(
            ft.Column(
                [
                    section_label("Engine shortlist (optional · not Grok)"),
                    muted(
                        "Local portfolio only: evidence JSON + EV haircut. Does not replace Grok deep research. "
                        "Thin meta if no p_model packs.",
                        11,
                    ),
                    ft.Container(height=6),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "Run engine shortlist",
                                icon=ft.Icons.AUTO_FIX_HIGH_ROUNDED,
                                on_click=lambda e: self._run_engine_shortlist(False),
                            ),
                            ft.TextButton(
                                "Dry-run only",
                                on_click=lambda e: self._run_engine_shortlist(True),
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=6,
                tight=True,
            )
        )
        self.engine_host.visible = self._engine_open

        body = scroll_page(
            page_header(
                "Desk",
                "Grok-first · operate · hand-off paths · settle · monitor risk",
                trailing=pill("CAN BET" if can else "RISK FULL", ok=can),
            ),
            ft.Row(
                [
                    ft.Container(content=live, expand=2),
                    ft.Container(content=grok, expand=3),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            ft.TextButton(
                "Show engine shortlist (advanced)" if not self._engine_open else "Hide engine shortlist",
                icon=ft.Icons.EXPAND_MORE if not self._engine_open else ft.Icons.EXPAND_LESS,
                on_click=self._toggle_engine,
            ),
            self.engine_host,
            ft.Row(
                [
                    ft.Container(content=self.phase_host, expand=True),
                    ft.Container(content=self.risk_host, expand=True),
                ],
                spacing=12,
            ),
            self.pending_host,
            ft.Row(
                [
                    ft.Container(content=self.slip_host, expand=True),
                    ft.Container(content=self.rejects_host, expand=True),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            self.receipt_host,
            spacing=16,
        )
        self.root.controls = [body]
        return self.root
