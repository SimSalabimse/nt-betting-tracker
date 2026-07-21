# Desktop layout rules (Windows / Flet)

1. Do **not** put `ListView(expand=True)` under animated switchers without a fixed parent height.
2. Do **not** use `ResponsiveRow` inside scroll `Column`s for primary content (height collapse).
3. Prefer `Column(scroll=AUTO)` + capped row counts for long lists.
4. Prefer plain `Container` content host over `AnimatedSwitcher` for route body.
5. Preserve tab selection / expanded bet id across soft reloads — do not remount the whole mode tree on auto-sync when possible.
6. Cap rendered controls (bets ~100–150).
7. Charts: **native Flet only** — never WebView / Plotly embeds on Windows desktop.
8. Engines in `nt/` are law — UI only presents and invokes them.
9. Forensic drill: category bars / stats tables → `StateService.drill_forensic` → `bet_ids` grain → Book Tickets (clearable). Never invent p_model in UI.
10. Case File (expanded bet): ledger · decision · evidence pack content · calibration · learning · notes.
