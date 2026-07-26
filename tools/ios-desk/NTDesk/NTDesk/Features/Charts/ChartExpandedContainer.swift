import SwiftUI

/// Full-screen expanded chart shell (design: plot height 280–360pt).
/// Expanded plot height within design band 280–360.
enum ChartExpandedMetrics {
    static let chartHeight: CGFloat = 320
}

struct ChartExpandedContainer<Content: View>: View {
    let title: String
    @ViewBuilder var content: () -> Content
    var onDismiss: () -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DeskSpacing.s4) {
                    content()
                }
                .padding(DeskSpacing.contentPad)
            }
            .background(DeskTheme.bg.ignoresSafeArea())
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(DeskTheme.surface, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { onDismiss() }
                        .accessibilityIdentifier("charts.expand.done")
                }
            }
        }
    }
}
