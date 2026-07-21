from __future__ import annotations

"""
Bets explorer — expandable Case File dossiers + forensic bet_ids filter.

Layout note (Windows/Flet): ListView(expand) under AnimatedSwitcher often
gets height 0. We use a scroll Column with explicit expand on the host only.
"""

from pathlib import Path

import flet as ft

from desktop.components.labels import market_label
from desktop.services.state_service import AppState, StateService
from desktop.theme import (
    ACCENT,
    ANIM_MED,
    BORDER,
    LOSS,
    PENDING,
    PROFIT,
    S2,
    S4,
    SURFACE_2,
    SURFACE_3,
    SURFACE_ELEV,
    TEXT,
    TEXT_MUTED,
    chip,
    fmt_nok,
    muted,
    page_header,
    pl_color,
    result_color,
    section_label,
)
from nt.decisions import (
    get_decision,
    learning_summary_for_ui,
    resolve_decision,
    score_outcome,
    score_process,
)
from nt.evidence import load_evidence

# Cap rendered rows so Flet stays responsive (filters still count full set)
_MAX_RENDER = 120


class BetsView:
    def __init__(self, svc: StateService, page: ft.Page) -> None:
        self.svc = svc
        self.page = page
        self._built = False
        self._expanded: str | None = None
        fs = dict(
            border_color=BORDER,
            color=TEXT,
            focused_border_color=ACCENT,
            dense=True,
            text_size=13,
            bgcolor=SURFACE_2,
        )
        self.query = ft.TextField(
            label="Search",
            expand=True,
            on_submit=lambda e: self.apply_filters(),
            **fs,
        )
        self.sport = ft.Dropdown(
            label="Sport",
            width=130,
            value="__all__",
            options=[ft.dropdown.Option("__all__", "All")],
            on_change=lambda e: self.apply_filters(),
            **fs,
        )
        self.band = ft.Dropdown(
            label="Band",
            width=110,
            value="__all__",
            options=[ft.dropdown.Option("__all__", "All")],
            on_change=lambda e: self.apply_filters(),
            **fs,
        )
        self.result = ft.Dropdown(
            label="Result",
            width=110,
            value="__all__",
            options=[
                ft.dropdown.Option("__all__", "All"),
                ft.dropdown.Option("Win", "Win"),
                ft.dropdown.Option("Loss", "Loss"),
                ft.dropdown.Option("Pending", "Pending"),
                ft.dropdown.Option("Refunded", "Refunded"),
            ],
            on_change=lambda e: self.apply_filters(),
            **fs,
        )
        self.count = muted("")
        self.forensic_banner = ft.Container(visible=False)
        # Scroll Column — not ListView (ListView expand collapses under switcher)
        self.list_col = ft.Column(spacing=6, tight=True)
        self.list_host = ft.Container(
            content=ft.Column(
                [self.list_col],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            expand=True,
            bgcolor=SURFACE_2,
            border=ft.border.all(1, BORDER),
            border_radius=10,
            padding=8,
        )
        self.root = ft.Column(expand=True, spacing=12)

    def _val(self, dd: ft.Dropdown) -> str | None:
        v = dd.value
        return None if not v or v == "__all__" else str(v)

    def _opts(self) -> None:
        sports = sorted(
            {(r.get("sport") or "").strip() for r in self.svc.state.rows if (r.get("sport") or "").strip()}
        )
        bands = sorted(
            {
                (r.get("odds_band") or "").strip()
                for r in self.svc.state.rows
                if (r.get("odds_band") or "").strip()
            }
        )
        cs, cb = self.sport.value, self.band.value
        self.sport.options = [ft.dropdown.Option("__all__", "All")] + [
            ft.dropdown.Option(s, s) for s in sports
        ]
        self.band.options = [ft.dropdown.Option("__all__", "All")] + [
            ft.dropdown.Option(b, b) for b in bands
        ]
        sk = {o.key for o in self.sport.options if o.key}
        bk = {o.key for o in self.band.options if o.key}
        self.sport.value = cs if cs in sk else "__all__"
        self.band.value = cb if cb in bk else "__all__"

    def _decision_for(self, r: dict[str, str]):
        """Side-car + notes recovery (always prefer resolve_decision)."""
        decs = getattr(self.svc.state, "decisions", None) or {}
        try:
            return resolve_decision(self.svc.state.cfg or {}, r, decisions_map=decs)
        except Exception:
            bid = r.get("bet_id") or ""
            if bid and bid in decs:
                return decs[bid]
            try:
                return get_decision(self.svc.state.cfg or {}, bid)
            except Exception:
                return None

    def _evidence_path_for(self, r: dict[str, str], dec: dict) -> str | None:
        bid = str(r.get("bet_id") or "")
        links = getattr(self.svc.state, "evidence_links", None) or {}
        link = links.get(bid) or {}
        ep = (
            (link.get("evidence_path") if isinstance(link, dict) else None)
            or dec.get("evidence_path")
            or ""
        )
        ep = str(ep).strip()
        return ep or None

    def _load_pack(self, ep: str | None) -> dict | None:
        if not ep:
            return None
        p = Path(ep)
        if not p.is_file():
            # try relative to project root
            p2 = self.svc.state.root / ep
            if p2.is_file():
                p = p2
            else:
                # try evidence dir basename
                p3 = self.svc.state.root / "evidence" / Path(ep).name
                if p3.is_file():
                    p = p3
                else:
                    return None
        try:
            return load_evidence(p)
        except Exception:
            return None

    def _calibration_for(self, bid: str) -> dict | None:
        cals = getattr(self.svc.state, "calibration", None) or []
        for c in reversed(cals):
            if str(c.get("bet_id") or "") == str(bid):
                return c
        return None

    def _section(self, title: str, body: list[ft.Control]) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [section_label(title), *body],
                spacing=4,
                tight=True,
            ),
            bgcolor=SURFACE_2,
            border=ft.border.all(1, BORDER),
            border_radius=8,
            padding=10,
        )

    def _kv(self, label: str, value: str, color: str = TEXT) -> ft.Control:
        return ft.Row(
            [
                muted(label, 11),
                ft.Text(
                    value,
                    size=12,
                    color=color,
                    weight=ft.FontWeight.W_600,
                    font_family="Consolas",
                    expand=True,
                    text_align=ft.TextAlign.RIGHT,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=8,
        )

    def _dossier(self, r: dict[str, str]) -> ft.Control:
        """Case File v2 — ledger · decision · evidence · calibration · learning · notes."""
        dec = self._decision_for(r) or {}
        process = score_process(dec, r)
        outcome = score_outcome(r, dec)
        bid = str(r.get("bet_id") or "")

        try:
            odds = float(str(r.get("decimal_odds") or 0).replace(",", "."))
        except ValueError:
            odds = 0.0
        implied = (1.0 / odds) if odds > 1.01 else None
        p_model = dec.get("p_model")
        ev = dec.get("ev")
        try:
            pl = (
                float(str(r.get("p_l_nok") or 0).replace(",", "."))
                if r.get("p_l_nok") not in (None, "")
                else None
            )
        except ValueError:
            pl = None
        try:
            stake = float(str(r.get("stake_nok") or 0).replace(",", "."))
        except ValueError:
            stake = 0.0

        proc_c = (
            PROFIT
            if process["score"] == "good"
            else (PENDING if process["score"] in ("ok", "variance", "lucky") else LOSS)
        )
        out_c = (
            PROFIT
            if outcome["score"] in ("good",)
            else (LOSS if outcome["score"] in ("bad",) else PENDING)
        )

        reasons = dec.get("reasons") or []
        reason_txt = (
            " · ".join(str(x) for x in reasons[:6])
            if reasons
            else (r.get("notes") or "—")[:220]
        )

        learn_state = self.svc.state.learning or {}
        sport = (r.get("sport") or "").strip().lower()
        sp = (learn_state.get("sports") or {}).get(sport) or {}
        learn_lines = learning_summary_for_ui(dec, r, live_sport=sp if sp else None)

        ep = self._evidence_path_for(r, dec)
        pack = self._load_pack(ep)
        cal = self._calibration_for(bid)
        market_key = (
            dec.get("market_key")
            or market_label(r.get("market_type") or "")
            or r.get("market_type")
            or "—"
        )

        chips_row = [
            chip(process["label"], color=proc_c),
            chip(outcome["label"], color=out_c),
            chip(str(r.get("research_grade") or dec.get("grade") or "—"), color=ACCENT),
        ]
        if dec.get("recovered_from_notes") or dec.get("backfill"):
            chips_row.append(chip("NOTES/BACKFILL", color=PENDING))
        if dec.get("explore"):
            chips_row.append(chip("EXPLORE", color=ACCENT))

        # 1 Ledger
        ledger = self._section(
            "1 · Ledger",
            [
                self._kv("Bet ID", bid or "—"),
                self._kv("Date", str(r.get("date") or "—")),
                self._kv("Match", (r.get("match") or "—")[:48]),
                self._kv("Selection", (r.get("selection") or "—")[:40]),
                self._kv("Odds", str(r.get("decimal_odds") or "—")),
                self._kv("Stake", fmt_nok(stake)),
                self._kv(
                    "P/L",
                    fmt_nok(pl, signed=True) if pl is not None else "—",
                    pl_color(pl or 0),
                ),
                self._kv("Sport", r.get("sport") or "—"),
                self._kv("Market", str(market_key)),
                self._kv("Band", r.get("odds_band") or "—"),
                self._kv("Phase", r.get("phase") or "—"),
                self._kv("Source", r.get("source") or "—"),
            ],
        )

        p_label = "p_model"
        if dec.get("p_model_source"):
            p_label = f"p_model ({dec.get('p_model_source')})"
        ev_label = "EV"
        if dec.get("ev_source") == "notes":
            ev_label = "EV (notes)"

        decision = self._section(
            "2 · Decision / model",
            [
                self._kv(
                    p_label,
                    f"{float(p_model)*100:.1f}%" if p_model is not None else "— (missing)",
                    ACCENT if p_model is not None else TEXT_MUTED,
                ),
                self._kv(
                    "Implied",
                    f"{implied*100:.1f}%" if implied else "—",
                ),
                self._kv(
                    ev_label,
                    f"{float(ev)*100:+.1f}pp" if ev is not None else "— (missing)",
                    pl_color(float(ev or 0)) if ev is not None else TEXT_MUTED,
                ),
                self._kv("Explore", "yes" if dec.get("explore") else "no"),
                self._kv(
                    "Learn stake ×",
                    str(dec.get("learning_stake_mult"))
                    if dec.get("learning_stake_mult") is not None
                    else "—",
                ),
                muted(process["detail"], 11),
                muted(outcome["detail"], 11),
                muted(reason_txt, 12),
            ],
        )

        # 3 Evidence
        evi_body: list[ft.Control] = [
            self._kv("Link", ep or "No pack linked (honest empty)", ACCENT if ep else TEXT_MUTED),
            self._kv(
                "Match method",
                str(
                    dec.get("evidence_match")
                    or (self.svc.state.evidence_links.get(bid) or {}).get("match_method")
                    or "none"
                ),
            ),
        ]
        if pack:
            if pack.get("p_model") is not None:
                evi_body.append(self._kv("Pack p_model", str(pack.get("p_model")), ACCENT))
            if pack.get("summary"):
                evi_body.append(section_label("Summary"))
                evi_body.append(muted(str(pack.get("summary"))[:600], 12))
            if pack.get("failure_modes"):
                evi_body.append(section_label("Failure modes"))
                evi_body.append(
                    ft.Text(str(pack.get("failure_modes"))[:400], size=12, color=LOSS)
                )
            if pack.get("thesis"):
                evi_body.append(section_label("Thesis"))
                evi_body.append(muted(str(pack.get("thesis"))[:400], 12))
            sources = pack.get("sources") or []
            if isinstance(sources, list) and sources:
                evi_body.append(muted(f"{len(sources)} sources in pack", 11))
        elif ep:
            evi_body.append(muted("Pack path set but file not readable from desktop root", 11))

        evidence = self._section("3 · Evidence", evi_body)

        # 4 Calibration
        if cal:
            cal_body = [
                self._kv(
                    "p_model",
                    str(cal.get("p_model")) if cal.get("p_model") is not None else "—",
                ),
                self._kv(
                    "y (1=win)",
                    str(cal.get("y")) if cal.get("y") is not None else "—",
                ),
                self._kv(
                    "Brier",
                    str(cal.get("brier")) if cal.get("brier") is not None else "—",
                ),
                self._kv("Result", str(cal.get("result") or "-")),
            ]
        else:
            cal_body = [
                muted("No calibration row (needs trustworthy p_model at settle)", 12),
            ]
        calibration = self._section("4 · Calibration", cal_body)

        learning = self._section(
            "5 · Learning",
            [
                muted(learn_lines["at_place"], 12),
                muted(learn_lines["live_now"], 11),
            ],
        )

        notes = self._section(
            "6 · Notes",
            [
                ft.Container(
                    content=ft.Text(
                        (r.get("notes") or "(no notes)")[:800],
                        size=12,
                        color=TEXT,
                        selectable=True,
                    ),
                    bgcolor=SURFACE_3,
                    border_radius=6,
                    padding=8,
                )
            ],
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(chips_row, spacing=8, wrap=True),
                    ledger,
                    decision,
                    evidence,
                    calibration,
                    learning,
                    notes,
                ],
                spacing=8,
                tight=True,
            ),
            bgcolor=SURFACE_3,
            border_radius=8,
            padding=S4,
            border=ft.border.all(1, BORDER),
            margin=ft.margin.only(top=4),
        )

    def _row(self, r: dict[str, str]) -> ft.Control:
        bid = r.get("bet_id") or ""
        expanded = self._expanded == bid
        res = r.get("result") or ""
        try:
            pl = (
                float(str(r.get("p_l_nok") or 0).replace(",", "."))
                if r.get("p_l_nok") not in (None, "")
                else 0.0
            )
        except ValueError:
            pl = 0.0

        def toggle(_e, b=bid):
            self._expanded = None if self._expanded == b else b
            self.apply_filters()

        res_c = result_color(res)
        summary = ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=4, height=28, bgcolor=res_c, border_radius=2),
                    ft.Icon(
                        ft.Icons.EXPAND_MORE if not expanded else ft.Icons.EXPAND_LESS,
                        size=18,
                        color=TEXT_MUTED,
                    ),
                    ft.Text(
                        str(r.get("date") or "")[5:],
                        size=12,
                        width=48,
                        color=TEXT_MUTED,
                        font_family="Consolas",
                    ),
                    ft.Text(
                        (r.get("match") or "")[:40],
                        size=13,
                        expand=3,
                        color=TEXT,
                        weight=ft.FontWeight.W_500,
                        no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        (r.get("selection") or "")[:24],
                        size=12,
                        expand=2,
                        color=TEXT_MUTED,
                        no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        str(r.get("decimal_odds") or ""),
                        size=12,
                        width=48,
                        font_family="Consolas",
                        color=TEXT,
                    ),
                    ft.Text(
                        str(r.get("stake_nok") or ""),
                        size=12,
                        width=44,
                        font_family="Consolas",
                        color=TEXT_MUTED,
                    ),
                    ft.Text(
                        res[:7] if res else "—",
                        size=12,
                        width=56,
                        color=res_c,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Text(
                        f"{pl:+.1f}" if res != "Pending" else "—",
                        size=12,
                        width=56,
                        color=pl_color(pl),
                        font_family="Consolas",
                        weight=ft.FontWeight.W_700,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                    chip((r.get("sport") or "?")[:10], color=TEXT_MUTED),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            ink=True,
            on_click=toggle,
        )

        body: list[ft.Control] = [summary]
        if expanded:
            body.append(
                ft.Container(
                    content=self._dossier(r),
                    padding=ft.padding.only(left=12, right=12, bottom=10),
                )
            )

        return ft.Container(
            content=ft.Column(body, spacing=0, tight=True),
            bgcolor=SURFACE_3 if expanded else SURFACE_ELEV,
            border=ft.border.all(1, ACCENT if expanded else BORDER),
            border_radius=8,
            animate=ft.Animation(ANIM_MED, ft.AnimationCurve.EASE_OUT),
        )

    def _sync_forensic_banner(self) -> None:
        ids = self.svc.state.forensic_bet_ids
        label = self.svc.state.forensic_label or ""
        if not ids:
            self.forensic_banner.visible = False
            self.forensic_banner.content = None
            return

        def clear(_e=None):
            self.svc.clear_forensic()
            self.apply_filters()
            try:
                self.page.update()
            except Exception:
                pass

        self.forensic_banner.visible = True
        self.forensic_banner.content = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.FILTER_ALT_ROUNDED, size=16, color=ACCENT),
                    ft.Text(
                        f"Forensic · {label} · {len(ids)} bet_ids",
                        size=12,
                        color=ACCENT,
                        weight=ft.FontWeight.W_600,
                        expand=True,
                    ),
                    ft.TextButton("Clear drill", on_click=clear),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=SURFACE_3,
            border=ft.border.all(1, ACCENT),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

    def apply_filters(self) -> None:
        q = (self.query.value or "").strip()
        forensic_ids = self.svc.state.forensic_bet_ids
        kwargs: dict = dict(
            query=q or None,
            sport=self._val(self.sport),
            odds_band=self._val(self.band),
            result=self._val(self.result),
        )
        if forensic_ids:
            # Grain law: exact bet_ids; skip date window so drill is complete
            kwargs["bet_ids"] = forensic_ids
            kwargs["date_from"] = None
            kwargs["date_to"] = None
        rows = self.svc.filtered_rows(**kwargs)
        if not forensic_ids:
            rows = list(reversed(rows[-400:]))
        else:
            # Keep ledger order roughly by date desc
            rows = sorted(rows, key=lambda r: r.get("date") or "", reverse=True)

        self._sync_forensic_banner()

        total = len(rows)
        shown = rows[:_MAX_RENDER]
        if total > _MAX_RENDER:
            self.count.value = f"showing {_MAX_RENDER}/{total}"
        else:
            self.count.value = f"{total} bets"

        if not shown:
            self.list_col.controls = [
                ft.Container(
                    content=muted("No bets match filters"),
                    padding=24,
                    alignment=ft.alignment.center,
                )
            ]
        else:
            self.list_col.controls = [self._row(r) for r in shown]

        try:
            self.list_host.update()
            self.count.update()
            self.forensic_banner.update()
        except Exception:
            try:
                self.page.update()
            except Exception:
                pass

    def build(self, state: AppState) -> ft.Control:
        self._opts()
        if not self._built:
            self.root.controls = [
                page_header(
                    "Bets",
                    "Case File · expand row · evidence pack · calibration · p_model · process",
                ),
                self.forensic_banner,
                ft.Row(
                    [self.query, self.sport, self.band, self.result, self.count],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.list_host,
            ]
            self._built = True
        self.apply_filters()
        return self.root
