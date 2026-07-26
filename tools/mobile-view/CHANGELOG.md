# mobile-view changelog

Package version = `VERSION` file = `api_version` in `/api/health` and `/api/desk`.  
Wire shape = `schema_version` (still **1** unless a breaking change).

Format: [Keep a Changelog](https://keepachangelog.com/)-style.

## [1.1.3] — 2026-07-26

### Fixed
- Equity curve: only **terminal** P/L (never ConfirmedPlaced/Pending); baseline from bankroll
  so a refund-only match day stays at **baseline (500)** like Lumina cumulative equity

## [1.1.2] — 2026-07-26

### Fixed
- Equity curve matches **Lumina Book** again: match `date` buckets + same non-Pending filter
  (25th refund → equity 500; 26th bets accumulate). Reverted settlement-day remap that diverged from PC.

## [1.1.1] — 2026-07-26

### Fixed
- Equity / daily / drawdown series use **settlement day** (Europe/Oslo `updated_at`), not match kickoff `date` — stops wrong day buckets (e.g. activity on the 25th)
- Carry-forward empty calendar days + baseline anchor so equity trend is not a sparse flat segment

## [1.1.0] — 2026-07-26

### Added
- `api_version` / `service` / `schema_version` on `/api/health`
- `api_version` on `/api/desk` (alongside `schema_version: 1`)
- Pending `kickoff` (`YYYY-MM-DD HH:MM`) from notes, ledger peers, inbox/outbox odds dumps
- Secure Variant A fields: `secure_nok`, `working_equity_nok`, `riskable_liquid_nok`, `secure_variant`, `secure_ref_hwm_nok`
- Object-shaped `place_these.rows_preview` (iOS-tolerant)
- Charts block (equity / daily / drawdown / by_sport / overall) — full era

### Changed
- Pending sort prefers soonest kickoff when known
- Docs: product map + schema contract

## [1.0.0] — earlier

### Added
- Read-only FastAPI desk: `/api/health`, `/api/desk`, HTML `/`
- Fail-closed bind (loopback default; `-Lan` opt-in)
- Basic pending + PLACE_THESE excerpt + charts scaffold
