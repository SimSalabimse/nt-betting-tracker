import SwiftUI

/// Always-visible last-sync clock + offline / mismatch banners.
struct FreshnessBanner: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        TimelineView(.periodic(from: .now, by: reduceMotion ? 300 : 60)) { context in
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                if !sync.network.isSatisfied {
                    banner(
                        text: "No Wi‑Fi / cellular — showing cache only",
                        symbol: "airplane",
                        color: DeskTheme.loss,
                        accessibilityLabel: "Device offline, showing cache only"
                    )
                }
                syncClockBanner(now: context.date)
                if sync.canRestoreLastKnownGood {
                    lastKnownGoodRow
                }
            }
        }
    }

    @ViewBuilder
    private func syncClockBanner(now: Date) -> some View {
        let relative = DeskFormatters.relativeTime(sync.lastSuccessSyncAt, relativeTo: now)
        switch sync.freshness {
        case .fresh:
            banner(
                text: "Live · last sync \(relative)",
                symbol: "checkmark.circle.fill",
                color: DeskTheme.profit,
                accessibilityLabel: "Live data, last sync \(relative)"
            )
        case .stale:
            banner(
                text: "Stale · last sync \(relative)",
                symbol: "clock.arrow.circlepath",
                color: DeskTheme.pending,
                accessibilityLabel: "Stale data, last sync \(relative)"
            )
        case .staleMismatch:
            banner(
                text: "Cache is from a different base URL — not live",
                symbol: "exclamationmark.triangle",
                color: DeskTheme.loss,
                accessibilityLabel: "Cache from different base URL, not live"
            )
        case .liveNotPersisted:
            banner(
                text: "Live but not saved · \(relative)",
                symbol: "externaldrive.badge.exclamationmark",
                color: DeskTheme.pending,
                accessibilityLabel: "Live but not saved on device"
            )
        case .empty:
            banner(
                text: sync.lastError ?? "No cache yet · set PC URL and sync",
                symbol: "wifi.slash",
                color: DeskTheme.textMuted,
                accessibilityLabel: sync.lastError ?? "No cache yet"
            )
        }
    }

    private var lastKnownGoodRow: some View {
        Button {
            sync.restoreLastKnownGoodBaseURL()
            Task { await sync.sync(waitForConnectivity: true) }
        } label: {
            HStack(spacing: DeskSpacing.s2) {
                Image(systemName: "arrow.uturn.backward.circle.fill")
                    .foregroundStyle(DeskTheme.accent)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Use last known good PC")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(DeskTheme.accent)
                    Text(sync.lastKnownGoodBaseURL ?? "")
                        .font(.caption2.monospaced())
                        .foregroundStyle(DeskTheme.textMuted)
                        .lineLimit(1)
                }
                Spacer(minLength: 0)
            }
            .padding(DeskSpacing.s2)
            .background {
                RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                    .stroke(DeskTheme.accent.opacity(0.5), lineWidth: 1)
                    .background(
                        RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                            .fill(DeskTheme.surfaceElev)
                    )
            }
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("connection.restore_last_good")
        .accessibilityHint("Switches to the last PC URL that synced successfully")
    }

    private func banner(
        text: String,
        symbol: String,
        color: Color,
        accessibilityLabel: String
    ) -> some View {
        HStack(alignment: .center, spacing: DeskSpacing.s2) {
            Image(systemName: symbol)
                .font(.footnote.weight(.semibold))
                .foregroundStyle(color)
                .symbolRenderingMode(.hierarchical)
                .accessibilityHidden(true)
            Text(text)
                .font(.footnote)
                .foregroundStyle(color)
                .frame(maxWidth: .infinity, alignment: .leading)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(DeskSpacing.s2)
        .background {
            RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                .fill(DeskTheme.surfaceElev)
                .overlay {
                    RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                        .fill(color.opacity(0.12))
                }
                .overlay {
                    RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                        .stroke(color.opacity(0.55), lineWidth: 1)
                }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilityLabel)
    }
}
