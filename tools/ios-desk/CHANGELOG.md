# iOS Desk (NT Desk) changelog

App version = `VERSION` file = `CFBundleShortVersionString` / Xcode `MARKETING_VERSION`.  
Build = `CFBundleVersion` / `CURRENT_PROJECT_VERSION`.

Requires **mobile-view `api_version` ≥ 1.1.1** for settlement equity, kickoff countdown, Secure A.  
Older APIs still load; the app shows an **outdated API** warning.

## [1.1.4] (build 6) — 2026-07-26

### Performance (iPhone 14 Pro · iOS 18 / iPhone 16 Pro · iOS 26+)
- Background poll: **desk-only** (no separate health hop); RTT from desk request
- Adaptive poll intervals (25s–120s) + skip when offline; timers on `.common` run loop
- Skip UI/disk when `generated_at` unchanged
- Cache file writes off main actor
- One TimelineView for entire pending list (not per-row)
- Charts `LazyVStack`; sparkline `drawingGroup`
- Thread-safe chart day parsing for background series build

## [1.1.3] (build 5) — 2026-07-26

### Changed
- Require mobile-view **≥ 1.1.2** (Lumina-matched equity by match date)

## [1.1.2] (build 4) — 2026-07-26

### Added
- Warning banner when connected PC mobile-view is older than required (`api_version` missing or &lt; 1.1.1)
- Settings / Connection sheet show API need + outdated detail

## [1.1.1] (build 3) — 2026-07-26

### Fixed
- Equity sparkline / chart Y zoom more aggressive so trend is visible
- Chart range chips (1w/1m) use UTC day cutoff (matches desk day keys)

### Needs
- mobile-view **1.1.1** (settlement-day equity curve) for correct day buckets

## [1.1.0] (build 2) — 2026-07-26

### Added
- Pending kickoff countdown (`In 2h 15m · 19:20`) when API sends `kickoff`
- Secure Variant A card (Charts), Risk Gate #2 on Desk
- Performance calendar (month heatmap)
- Adaptive chart Y scales (equity no longer flat at top of 0…max axis)
- RTT trend, last-known-good PC, freshness clock, morning summary, equity sparkline
- Pending sport filter, range chips 1w/1m/all, adaptive poll

### Fixed
- Settings large-title + glass blur on iOS 26/27 → inline solid bar
- RTT row separator over “Last success”
- Risk FULL banner no longer shows raw `can_bet=no`

## [1.0.0] (build 1) — earlier

### Added
- HIG redesign: Desk / Charts / Pending / Slip + Settings sheet
- Unsigned IPA scaffold, LAN/Tailscale profiles, cache, charts v1
