import SwiftUI

/// Wraps content in NavigationStack and attaches Settings gear.
/// This is the primary gear mechanism — do not rely on root-only modifiers.
struct DeskScreenChrome<Content: View>: View {
    @Environment(\.openSettings) private var openSettings
    let title: String
    @ViewBuilder var content: () -> Content

    var body: some View {
        NavigationStack {
            content()
                .navigationTitle(title)
                .toolbarBackground(DeskTheme.surface, for: .navigationBar)
                .toolbar {
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
}
