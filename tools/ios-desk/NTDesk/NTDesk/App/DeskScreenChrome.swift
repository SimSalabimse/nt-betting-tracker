import SwiftUI

/// Wraps content in NavigationStack and attaches Settings gear + sync chrome.
/// This is the primary gear mechanism — do not rely on root-only modifiers.
struct DeskScreenChrome<Content: View>: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.openSettings) private var openSettings
    let title: String
    @ViewBuilder var content: () -> Content

    var body: some View {
        NavigationStack {
            content()
                .navigationTitle(title)
                .toolbarBackground(.ultraThinMaterial, for: .navigationBar)
                .toolbarBackground(.visible, for: .navigationBar)
                .toolbar {
                    ToolbarItem(placement: .topBarLeading) {
                        leadingChrome
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
        HStack(spacing: DeskSpacing.s2) {
            if sync.isSyncing {
                ProgressView()
                    .controlSize(.small)
                    .tint(DeskTheme.accent)
                    .accessibilityLabel("Syncing desk snapshot")
            } else if sync.freshness == .fresh {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(DeskTheme.profit)
                    .symbolRenderingMode(.hierarchical)
                    .accessibilityLabel("Live data")
            }
        }
        .accessibilityElement(children: .combine)
    }
}
