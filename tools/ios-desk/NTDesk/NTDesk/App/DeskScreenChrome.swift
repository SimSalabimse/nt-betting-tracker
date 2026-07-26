import SwiftUI

/// Wraps content in NavigationStack and attaches Settings gear + sync chrome.
/// This is the primary gear mechanism — do not rely on root-only modifiers.
struct DeskScreenChrome<Content: View>: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.openSettings) private var openSettings
    let title: String
    @ViewBuilder var content: () -> Content

    private var showsLeadingChrome: Bool {
        sync.isSyncing || sync.freshness == .fresh
    }

    var body: some View {
        NavigationStack {
            content()
                .navigationTitle(title)
                .toolbarBackground(.ultraThinMaterial, for: .navigationBar)
                .toolbarBackground(.visible, for: .navigationBar)
                .toolbar {
                    // Only attach when content exists — avoids empty combined VO toolbar ghost.
                    if showsLeadingChrome {
                        ToolbarItem(placement: .topBarLeading) {
                            leadingChrome
                        }
                    }
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            openSettings()
                        } label: {
                            Label("Settings", systemImage: "gearshape")
                        }
                        .accessibilityIdentifier("settings.gear")
                    }
                }
        }
    }

    @ViewBuilder
    private var leadingChrome: some View {
        if sync.isSyncing {
            ProgressView()
                .controlSize(.small)
                .tint(DeskTheme.accent)
                .accessibilityLabel("Syncing desk snapshot")
        } else {
            // Caller only installs this item when freshness == .fresh (and not syncing).
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(DeskTheme.profit)
                .symbolRenderingMode(.hierarchical)
                .accessibilityLabel("Live data")
        }
    }
}
