# NT Desk — future ideas (parked)

Ideas deferred on purpose. Do not implement until requested.

| Idea | Notes |
|------|--------|
| **Profile chips in connection popover** | Quick switch LAN / Tailscale without full Settings. |
| **Discovery → auto-name profile** | e.g. “Home LAN” / “Tailscale” from host + interface. |
| **Support all orientations or declare full-screen** | Clears Xcode orientation warning; either add upside-down or `UIRequiresFullScreen`. |
| **Throttle poll when backgrounded** | Already stop poll on inactive; optionally lengthen interval when app is active but data is still *fresh* (e.g. 20s → 60s after recent success). Saves battery / PC load. |

## What those technical notes meant

### Cap equity series points in UI
If the ledger has hundreds of settled days, drawing every point on a phone chart can be slow. The app already **downsamples display marks** for series longer than 61 days (weekly ticks) while selection still uses raw days. “Cap” means: never try to plot thousands of points at full density — keep a hard upper bound on drawn marks so scrolling Charts stays smooth.

### Throttle poll when backgrounded
Auto-refresh currently hits `/api/desk` about every 20s while the app is **active**. When the app is backgrounded we **stop** the timer. “Throttle when backgrounded” would mean: if we ever poll in background (we don’t today), do it much less often — or, more useful: when the last sync is still fresh, poll less often even in foreground.

---

Last updated: 2026-07-26
