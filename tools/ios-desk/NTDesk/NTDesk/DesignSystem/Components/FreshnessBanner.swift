import SwiftUI

/// Client-side `SyncService.freshness` banner (not server `snapshot.stale` / warnings).
struct FreshnessBanner: View {
    @EnvironmentObject private var sync: SyncService

    var body: some View {
        switch sync.freshness {
        case .fresh:
            EmptyView()
        case .stale:
            banner(
                text: "Stale — last sync \(sync.lastSuccessSyncAt ?? "—")",
                symbol: "clock.arrow.circlepath",
                color: DeskTheme.pending,
                accessibilityLabel: "Stale data, last sync \(sync.lastSuccessSyncAt ?? "unknown")"
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
                text: "Live but not saved on device",
                symbol: "externaldrive.badge.exclamationmark",
                color: DeskTheme.pending,
                accessibilityLabel: "Live but not saved on device"
            )
        case .empty:
            banner(
                text: sync.lastError ?? "No cache yet",
                symbol: "wifi.slash",
                color: DeskTheme.textMuted,
                accessibilityLabel: sync.lastError ?? "No cache yet"
            )
        }
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
                .accessibilityHidden(true)
            Text(text)
                .font(.footnote)
                .foregroundStyle(color)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(DeskSpacing.s2)
        .background(
            RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                .fill(DeskTheme.surface2)
                .overlay(
                    RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                        .stroke(color.opacity(0.55), lineWidth: 1)
                )
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilityLabel)
    }
}
