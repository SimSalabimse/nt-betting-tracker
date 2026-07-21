from __future__ import annotations

"""
Chart components for Flet.

Line charts stay interactive with tooltips on data points.
Hover banner is silent until the user interacts (no permanent helper chrome).
"""

from typing import Any

import flet as ft

from desktop.components.labels import market_label
from desktop.theme import (
    ACCENT,
    BORDER,
    LOSS,
    PROFIT,
    SURFACE_2,
    SURFACE_ELEV,
    TEXT,
    TEXT_MUTED,
)


def _short_date(d: str) -> str:
    if not d:
        return ""
    return d[5:] if len(d) >= 10 else d


def _empty_state(message: str, *, detail: str = "") -> ft.Control:
    kids = [
        ft.Text(message, size=13, color=TEXT_MUTED, weight=ft.FontWeight.W_500),
    ]
    if detail:
        kids.append(ft.Text(detail, size=11, color=TEXT_MUTED))
    return ft.Container(
        content=ft.Column(kids, spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
        padding=ft.padding.symmetric(vertical=28, horizontal=16),
        alignment=ft.alignment.center,
        bgcolor=SURFACE_2,
        border_radius=8,
        border=ft.border.all(1, BORDER),
    )


def _panel(
    content: ft.Control,
    *,
    height: int | None = None,
    caption: str | None = None,
    hover_label: ft.Control | None = None,
    framed: bool = False,
) -> ft.Control:
    """Chart body. Hover strip is fixed-height so the card never jumps."""
    box = ft.Container(
        content=content,
        height=height,
        border=ft.border.all(1, BORDER) if framed else None,
        border_radius=8 if framed else 0,
        bgcolor=SURFACE_2 if framed else None,
        padding=ft.padding.symmetric(horizontal=4 if not framed else 10, vertical=4 if not framed else 10),
        clip_behavior=ft.ClipBehavior.NONE,
    )
    kids: list[ft.Control] = [box]
    if hover_label is not None:
        kids.append(hover_label)
    if caption:
        kids.append(ft.Text(caption, size=11, color=TEXT_MUTED))
    return ft.Column(kids, spacing=6, tight=True)


# Fixed strip height — never collapse/expand (that was the flash / lag)
_BANNER_H = 36


def _hover_banner(default: str = "") -> ft.Container:
    """
    Always occupies the same vertical space.
    Idle: invisible content, same box size (no layout thrash when moving between points).
    """
    text = ft.Text(
        default or " ",
        size=12,
        color=TEXT_MUTED,
        selectable=True,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        no_wrap=True,
    )
    active = bool(default and default.strip())
    banner = ft.Container(
        content=text,
        bgcolor=SURFACE_ELEV if active else "transparent",
        border=ft.border.all(1, BORDER if active else "transparent"),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        height=_BANNER_H,
        alignment=ft.alignment.center_left,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        # data: text control + last message (skip redundant updates)
        data={"text": text, "last": default or ""},
    )
    return banner


def _set_hover(banner: ft.Container, msg: str, *, active: bool = True) -> None:
    """Update detail strip without changing layout size. Skip no-op updates (reduces lag)."""
    meta = banner.data
    if not isinstance(meta, dict):
        return
    text = meta.get("text")
    if not isinstance(text, ft.Text):
        return

    show = bool(active and msg and str(msg).strip())
    next_msg = str(msg).strip() if show else ""
    # Same state → no page paint
    if meta.get("last") == next_msg and bool(meta.get("shown")) == show:
        return
    meta["last"] = next_msg
    meta["shown"] = show

    if show:
        text.value = next_msg
        text.color = TEXT
        banner.bgcolor = SURFACE_ELEV
        banner.border = ft.border.all(1, ACCENT)
    else:
        text.value = " "
        text.color = TEXT_MUTED
        banner.bgcolor = "transparent"
        banner.border = ft.border.all(1, "transparent")
    # Keep height fixed always
    banner.height = _BANNER_H
    try:
        banner.update()
    except Exception:
        pass


# ── line charts ──────────────────────────────────────────────────────────


def _line_chart(
    ys: list[float],
    *,
    height: int,
    color: str,
    tooltips: list[str] | None = None,
    x_labels: list[tuple[int, str]] | None = None,
    curved: bool = True,
    on_hover_index=None,
) -> ft.LineChart:
    n = len(ys)
    ymin = min(ys)
    ymax = max(ys)
    if abs(ymax - ymin) < 1e-9:
        ymax = ymin + 1.0
    pad = (ymax - ymin) * 0.14
    ymin -= pad
    ymax += pad

    y_ticks = [ymin, (ymin + ymax) / 2, ymax]
    left_labels = [
        ft.ChartAxisLabel(
            value=v,
            label=ft.Text(f"{v:.0f}", size=9, color=TEXT_MUTED, font_family="Consolas"),
        )
        for v in y_ticks
    ]
    bottom_labels = []
    if x_labels:
        for idx, text in x_labels:
            if 0 <= idx < n:
                bottom_labels.append(
                    ft.ChartAxisLabel(value=idx, label=ft.Text(text, size=9, color=TEXT_MUTED))
                )

    tip_style = ft.TextStyle(size=11, color=TEXT, weight=ft.FontWeight.W_500)
    r = 5 if n <= 3 else (4 if n <= 20 else (3 if n <= 60 else 2))
    data_points = []
    for i, y in enumerate(ys):
        tip = tooltips[i] if tooltips and i < len(tooltips) else f"{y:.2f}"
        # Shorter floating tip; full detail lives in the under-chart strip
        short = tip if len(tip) <= 48 else (tip[:45] + "…")
        data_points.append(
            ft.LineChartDataPoint(
                x=i,
                y=y,
                tooltip=short,
                show_tooltip=True,
                tooltip_style=tip_style,
                point=ft.ChartCirclePoint(radius=r, color=color, stroke_width=0),
                selected_point=ft.ChartCirclePoint(
                    radius=r + 3, color=color, stroke_width=2, stroke_color=TEXT
                ),
            )
        )

    # Track last index so we don't thrash the detail strip on every mouse pixel
    last_idx: dict[str, int | None] = {"i": None}

    def _on_event(e: ft.LineChartEvent):
        if on_hover_index is None:
            return
        spots = getattr(e, "spots", None) or []
        idx = None
        if spots:
            spot0 = spots[0]
            if isinstance(spot0, dict):
                idx = spot0.get("spot_index")
            else:
                idx = getattr(spot0, "spot_index", None)
        et = (getattr(e, "type", None) or "").lower()
        if et in ("pointerexit", "exit", "panend"):
            if last_idx["i"] is not None:
                last_idx["i"] = None
                on_hover_index(None)
            return
        if idx is None:
            return
        try:
            i = int(idx)
        except (TypeError, ValueError):
            return
        if i == last_idx["i"]:
            return
        last_idx["i"] = i
        on_hover_index(i)

    # Horizontal padding in data space so first/last point tooltips aren't flush to the edge
    x_pad = 0.35 if n > 1 else 0.5
    return ft.LineChart(
        data_series=[
            ft.LineChartData(
                data_points=data_points,
                stroke_width=2.5,
                color=color,
                curved=curved and n >= 3,
                stroke_cap_round=True,
                below_line_bgcolor=ft.Colors.with_opacity(0.10, color),
                prevent_curve_over_shooting=True,
                point=True,
                selected_point=True,
            )
        ],
        min_y=ymin,
        max_y=ymax,
        min_x=-x_pad,
        max_x=max(n - 1, 1) + x_pad,
        animate=0,
        interactive=True,
        border=ft.border.all(0, "transparent"),
        horizontal_grid_lines=ft.ChartGridLines(
            interval=(ymax - ymin) / 3 or 1,
            color=ft.Colors.with_opacity(0.10, TEXT_MUTED),
            width=1,
        ),
        left_axis=ft.ChartAxis(labels=left_labels, labels_size=34, show_labels=True),
        bottom_axis=ft.ChartAxis(
            labels=bottom_labels,
            labels_size=20 if bottom_labels else 0,
            show_labels=bool(bottom_labels),
        ),
        tooltip_bgcolor=ft.Colors.with_opacity(0.96, "#0F1720"),
        tooltip_rounded_radius=8,
        tooltip_margin=8,
        tooltip_padding=8,
        # Keep floating tips inside the chart box (esp. rightmost / top points)
        tooltip_fit_inside_horizontally=True,
        tooltip_fit_inside_vertically=True,
        tooltip_show_on_top_of_chart_box_area=True,
        on_chart_event=_on_event,
        height=height,
        expand=True,
    )


def equity_line_chart(points: list[dict[str, Any]], height: int = 190) -> ft.Control:
    if not points:
        return _empty_state(
            "No settled equity points in this range",
            detail="Pending bets don’t move equity until settled · try a wider range",
        )
    if len(points) == 1:
        p = points[0]
        return _empty_state(
            f"Only one equity day in range · {p.get('date')}",
            detail=f"Equity {float(p.get('equity') or 0):.2f} NOK · expand range for a curve",
        )
    pts = list(points)
    ys = [float(p["equity"]) for p in pts]
    n = len(pts)
    tips = [
        f"{p['date']}  ·  Equity {float(p['equity']):.2f} NOK  ·  Day P/L {float(p.get('day_pl') or 0):+.2f}"
        for p in pts
    ]
    labels: list[tuple[int, str]] = [(0, _short_date(pts[0]["date"])), (n - 1, _short_date(pts[-1]["date"]))]
    if n >= 5:
        labels.insert(1, (n // 2, _short_date(pts[n // 2]["date"])))

    banner = _hover_banner()

    def on_idx(i: int | None) -> None:
        if i is None or i < 0 or i >= n:
            _set_hover(banner, "", active=False)
        else:
            _set_hover(banner, tips[i], active=True)

    chart = _line_chart(
        ys,
        height=height - 12,
        color=ACCENT,
        tooltips=tips,
        x_labels=labels,
        curved=True,
        on_hover_index=on_idx,
    )
    return _panel(
        chart,
        height=height,
        hover_label=banner,
        caption=f"{pts[0]['date']} → {pts[-1]['date']}  ·  {n} days",
    )


def line_from_series(
    points: list[dict[str, Any]],
    y_key: str,
    *,
    height: int = 170,
    color: str = ACCENT,
    y_as_pct: bool = False,
) -> ft.Control:
    if not points:
        return _empty_state("No series data in this range")
    if len(points) == 1:
        return _empty_state("Only one point in range · expand the date filter")
    pts = list(points)
    scale = 100.0 if y_as_pct else 1.0
    ys = [float(p[y_key]) * scale for p in pts]
    n = len(pts)
    unit = "%" if y_as_pct else ""
    tips = []
    for p, y in zip(pts, ys):
        d = str(p.get("date") or p.get("i") or "")
        extra = ""
        if "rolling_pl" in p:
            extra = f"  ·  Window P/L {float(p['rolling_pl']):+.2f} NOK (n={int(p.get('window_n') or 0)})"
        elif "drawdown" in p or y_key == "dd":
            extra = f"  ·  Drawdown {abs(y):.2f} NOK"
        tips.append(f"{d}  ·  {y_key.replace('_', ' ')}: {y:.2f}{unit}{extra}")

    d0 = str(pts[0].get("date") or pts[0].get("i") or "")
    d1 = str(pts[-1].get("date") or pts[-1].get("i") or "")
    labels = [
        (0, _short_date(d0) if "-" in d0 else str(d0)[:6]),
        (n - 1, _short_date(d1) if "-" in d1 else str(d1)[:6]),
    ]
    if n >= 8:
        mid = n // 2
        dm = str(pts[mid].get("date") or pts[mid].get("i") or "")
        labels.insert(1, (mid, _short_date(dm) if "-" in dm else str(dm)[:6]))

    banner = _hover_banner()

    def on_idx(i: int | None) -> None:
        if i is None or i < 0 or i >= n:
            _set_hover(banner, "", active=False)
        else:
            _set_hover(banner, tips[i], active=True)

    chart = _line_chart(
        ys,
        height=height - 12,
        color=color,
        tooltips=tips,
        x_labels=labels,
        curved=True,
        on_hover_index=on_idx,
    )
    return _panel(
        chart,
        height=height,
        hover_label=banner,
        caption=f"last {ys[-1]:.1f}{unit}  ·  {n} points",
    )


def drawdown_chart(dd_pts: list[dict[str, Any]], height: int = 170) -> ft.Control:
    if not dd_pts:
        return _empty_state("No drawdown data in this range")
    pts = [
        {
            "date": p["date"],
            "dd": -float(p["drawdown"]),
            "drawdown": p["drawdown"],
        }
        for p in dd_pts
    ]
    return line_from_series(pts, "dd", height=height, color=LOSS, y_as_pct=False)


# ── bars ─────────────────────────────────────────────────────────────────


def _bipolar_bars(
    values: list[float],
    labels: list[str],
    tooltips: list[str],
    *,
    half: int = 56,
    bar_width: int = 16,
    on_select=None,
) -> ft.Control:
    if not values:
        return _empty_state("No data")
    max_abs = max(abs(v) for v in values) or 1.0
    cols: list[ft.Control] = []
    for i, (v, lab, tip) in enumerate(zip(values, labels, tooltips)):
        h = max(3, int(abs(v) / max_abs * half)) if abs(v) > 1e-9 else 3
        col = PROFIT if v >= 0 else LOSS

        def _pick(_e, idx=i, t=tip):
            if on_select:
                on_select(idx, t)

        cols.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Container(
                                width=bar_width,
                                height=h if v >= 0 else 0,
                                bgcolor=col,
                                border_radius=3,
                            ),
                            height=half,
                            alignment=ft.alignment.bottom_center,
                        ),
                        ft.Container(height=1, width=bar_width + 6, bgcolor=BORDER),
                        ft.Container(
                            content=ft.Container(
                                width=bar_width,
                                height=h if v < 0 else 0,
                                bgcolor=col,
                                border_radius=3,
                            ),
                            height=half,
                            alignment=ft.alignment.top_center,
                        ),
                        ft.Text(lab, size=9, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER, no_wrap=True),
                        ft.Text(
                            f"{v:+.0f}" if abs(v) >= 1 else f"{v:+.1f}",
                            size=9,
                            color=col,
                            font_family="Consolas",
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
                on_click=_pick,
                on_hover=lambda e, idx=i, t=tip: (
                    on_select(idx, t) if e.data == "true" and on_select else None
                ),
                ink=True,
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=3, vertical=2),
            )
        )
    return ft.Row(
        cols,
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.START,
        scroll=ft.ScrollMode.AUTO if len(values) > 14 else None,
    )


def _uni_bars(
    values: list[float],
    labels: list[str],
    tooltips: list[str],
    *,
    bar_area: int = 100,
    bar_width: int = 14,
    color: str = ACCENT,
    on_select=None,
) -> ft.Control:
    if not values:
        return _empty_state("No data")
    top = max(values) or 1.0
    cols = []
    for i, (v, lab, tip) in enumerate(zip(values, labels, tooltips)):
        h = max(3, int((v / top) * bar_area)) if v > 0 else 3

        def _pick(_e, idx=i, t=tip):
            if on_select:
                on_select(idx, t)

        cols.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"{v:.0f}", size=9, color=TEXT_MUTED, font_family="Consolas"),
                        ft.Container(
                            content=ft.Container(width=bar_width, height=h, bgcolor=color, border_radius=4),
                            height=bar_area,
                            alignment=ft.alignment.bottom_center,
                        ),
                        ft.Text(lab, size=9, color=TEXT_MUTED, no_wrap=True),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
                on_click=_pick,
                on_hover=lambda e, idx=i, t=tip: (
                    on_select(idx, t) if e.data == "true" and on_select else None
                ),
                ink=True,
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=3, vertical=2),
            )
        )
    return ft.Row(
        cols,
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        scroll=ft.ScrollMode.AUTO if len(values) > 14 else None,
    )


def daily_pl_bars(daily: list[dict[str, Any]], height: int = 200, last_n: int = 12) -> ft.Control:
    if not daily:
        return _empty_state(
            "No daily P/L in this range",
            detail="Settled results will show as green/red day bars",
        )
    pts = daily[-last_n:]
    values = [float(p["pl"]) for p in pts]
    labels = [_short_date(p["date"]) for p in pts]
    tips = [
        f"{p['date']}  ·  P/L {float(p['pl']):+.2f} NOK  ·  {int(p.get('n') or 0)} bets"
        + (f"  ·  stake {float(p.get('stake') or 0):.0f}" if p.get("stake") is not None else "")
        for p in pts
    ]
    banner = _hover_banner()
    bw = max(14, min(28, 340 // max(len(pts), 1)))

    def on_select(_idx: int, tip: str) -> None:
        _set_hover(banner, tip, active=True)

    bars = _bipolar_bars(
        values,
        labels,
        tips,
        half=max(48, (height - 70) // 2),
        bar_width=bw,
        on_select=on_select,
    )
    cap = f"{pts[0]['date']} → {pts[-1]['date']}  ·  {len(pts)} day(s)"
    return _panel(bars, hover_label=banner, caption=cap)


def volume_bars(volume: list[dict[str, Any]], height: int = 160, last_n: int = 12) -> ft.Control:
    if not volume:
        return _empty_state("No volume in this range")
    pts = volume[-last_n:]
    values = [float(p["n"]) for p in pts]
    labels = [_short_date(p["date"]) for p in pts]
    tips = [
        f"{p['date']}  ·  {int(p['n'])} bets  ·  stake {float(p.get('stake') or 0):.0f} NOK"
        for p in pts
    ]
    banner = _hover_banner()
    bw = max(14, min(20, 340 // max(len(pts), 1)))

    def on_select(_idx: int, tip: str) -> None:
        _set_hover(banner, tip, active=True)

    bars = _uni_bars(
        values,
        labels,
        tips,
        bar_area=max(70, height - 50),
        bar_width=bw,
        color=ACCENT,
        on_select=on_select,
    )
    return _panel(
        bars,
        hover_label=banner,
        caption=f"{int(sum(values))} bets · {len(pts)} day(s)",
    )


def category_bars(
    stats: dict[str, dict[str, float]],
    *,
    value_key: str = "pl",
    height: int = 220,
    max_items: int = 8,
    color_by_sign: bool = True,
    label_fn=None,
    on_drill=None,
    dim: str | None = None,
) -> ft.Control:
    """
    Category bars. Click sets hover tip; when on_drill is set, click also fires
    forensic drill: on_drill(dim, group_key, display_label).
    """
    items = [(k, v) for k, v in stats.items() if v.get("n", 0) > 0]
    if not items:
        return _empty_state("No category data in this range")

    items = sorted(items, key=lambda kv: kv[1].get(value_key, 0), reverse=True)[:max_items]
    raw_vals = []
    for _, v in items:
        raw = float(v.get(value_key, 0))
        if value_key in ("roi", "winrate"):
            raw *= 100
        raw_vals.append(raw)
    max_abs = max(abs(x) for x in raw_vals) or 1.0
    bar_max_w = 140
    lab = label_fn or (lambda x: x)

    banner = _hover_banner()
    rows: list[ft.Control] = []
    for (name, v), val in zip(items, raw_vals):
        col = (PROFIT if val >= 0 else LOSS) if color_by_sign else ACCENT
        w = max(4, int(abs(val) / max_abs * bar_max_w))
        if value_key == "pl":
            val_txt = f"{val:+.1f}"
        elif value_key in ("roi", "winrate"):
            val_txt = f"{val:+.1f}%"
        else:
            val_txt = f"{val:.1f}"
        disp = lab(name)
        tip = (
            f"{disp}  ·  n={int(v.get('n', 0))}  ·  WR {float(v.get('winrate', 0)) * 100:.1f}%  ·  "
            f"ROI {float(v.get('roi', 0)) * 100:+.1f}%  ·  P/L {float(v.get('pl', 0)):+.2f} NOK  ·  "
            f"stake {float(v.get('stake', 0)):.0f}"
        )
        if on_drill:
            tip = tip + "  ·  click → tickets"

        def _pick(_e, t=tip, key=name, display=disp):
            _set_hover(banner, t, active=True)
            if on_drill and dim and key and not str(key).startswith("Other"):
                try:
                    on_drill(dim, key, display)
                except Exception:
                    pass

        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(
                            disp if len(disp) <= 16 else disp[:15] + "…",
                            size=12,
                            color=TEXT,
                            width=108,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Container(
                            content=ft.Container(width=w, height=12, bgcolor=col, border_radius=4),
                            width=bar_max_w,
                            height=14,
                            alignment=ft.alignment.center_left,
                        ),
                        ft.Text(
                            val_txt,
                            size=12,
                            color=col,
                            width=60,
                            font_family="Consolas",
                            text_align=ft.TextAlign.RIGHT,
                        ),
                        ft.Text(f"n={int(v.get('n', 0))}", size=11, color=TEXT_MUTED, width=42),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                on_click=_pick,
                on_hover=lambda e, t=tip: (_set_hover(banner, t, active=True) if e.data == "true" else None),
                ink=True,
                border_radius=6,
                padding=ft.padding.symmetric(vertical=4, horizontal=4),
                tooltip="Click → open tickets for this group" if on_drill else None,
            )
        )

    return _panel(ft.Column(rows, spacing=2, tight=True), hover_label=banner)


def market_bars(stats: dict[str, dict[str, float]], **kwargs) -> ft.Control:
    return category_bars(stats, label_fn=market_label, **kwargs)


def sport_share(by_sport: dict[str, dict[str, float]], height: int = 170) -> ft.Control:
    if not by_sport:
        return _empty_state("No sport data in this range")

    items = sorted(by_sport.items(), key=lambda kv: kv[1].get("n", 0), reverse=True)
    total = sum(float(v.get("n", 0)) for _, v in items) or 1.0
    top = items[:6]
    rest_n = sum(float(v.get("n", 0)) for _, v in items[6:])
    if rest_n > 0:
        top = top + [("Other", {"n": rest_n, "pl": 0.0, "roi": 0.0, "winrate": 0.0})]

    palette = [ACCENT, PROFIT, "#60A5FA", "#A78BFA", "#FBBF24", "#F472B6", "#94A3B8"]
    banner = _hover_banner()

    stack_segments: list[ft.Control] = []
    rows: list[ft.Control] = []
    for i, (name, v) in enumerate(top):
        n = float(v.get("n", 0))
        if n <= 0:
            continue
        col = palette[i % len(palette)]
        pct = n / total
        tip = (
            f"{name}  ·  {int(n)} bets  ·  {pct * 100:.1f}%  ·  "
            f"P/L {float(v.get('pl') or 0):+.2f} NOK  ·  ROI {float(v.get('roi') or 0) * 100:+.1f}%"
        )

        def _pick(_e, t=tip):
            _set_hover(banner, t, active=True)

        weight = max(1, int(round(pct * 100)))
        stack_segments.append(
            ft.Container(
                expand=weight,
                height=14,
                bgcolor=col,
                on_click=_pick,
                tooltip=tip,
            )
        )

        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(width=10, height=10, bgcolor=col, border_radius=3),
                        ft.Text(
                            name,
                            size=12,
                            color=TEXT,
                            expand=True,
                            no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Container(
                            content=ft.Container(
                                width=max(4, int(pct * 100)),
                                height=8,
                                bgcolor=col,
                                border_radius=3,
                            ),
                            width=100,
                            height=10,
                            alignment=ft.alignment.center_left,
                        ),
                        ft.Text(f"{int(n)}", size=12, width=36, font_family="Consolas", color=TEXT_MUTED),
                        ft.Text(f"{pct * 100:.0f}%", size=12, width=40, font_family="Consolas", color=TEXT),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                on_click=_pick,
                on_hover=lambda e, t=tip: (_set_hover(banner, t, active=True) if e.data == "true" else None),
                ink=True,
                border_radius=8,
                padding=ft.padding.symmetric(vertical=5, horizontal=6),
            )
        )

    stacked = ft.Container(
        content=ft.Row(stack_segments, spacing=0),
        height=14,
        border_radius=7,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        bgcolor=SURFACE_2,
    )

    body = ft.Column(
        [
            stacked,
            ft.Container(height=6),
            ft.Column(rows, spacing=2, tight=True),
        ],
        spacing=0,
        tight=True,
    )
    return _panel(
        body,
        hover_label=banner,
        caption=f"{int(total)} bets · {len(items)} sports",
    )


def sport_pie(by_sport: dict[str, dict[str, float]], height: int = 170) -> ft.Control:
    return sport_share(by_sport, height=height)
