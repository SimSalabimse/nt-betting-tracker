# iOS Desk (NT Desk) changelog

App version = `VERSION` file = `CFBundleShortVersionString` / Xcode `MARKETING_VERSION`.  
Build = `CFBundleVersion` / `CURRENT_PROJECT_VERSION`.

Requires **mobile-view `api_version` ≥ 1.1.0** for kickoff countdown + Secure A cards (older APIs still load; features degrade).

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
