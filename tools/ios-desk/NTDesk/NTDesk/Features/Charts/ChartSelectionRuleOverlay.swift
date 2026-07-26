import Charts
import SwiftUI

/// Dashed vertical rule for a selected day, drawn in **chart** coordinates.
///
/// `ChartProxy.position(forX:)` is plot-area-local; `chartBackground` / full-chart
/// `GeometryReader`s must add `plotFrame` origin so the line aligns with `RuleMark`.
struct ChartSelectionRuleOverlay: View {
    let proxy: ChartProxy
    let geo: GeometryProxy
    /// UTC midnight of the selected ledger day (raw series).
    let selectedDate: Date?

    var body: some View {
        if let selectedDate,
           let plotFrame = proxy.plotFrame {
            let frame = geo[plotFrame]
            if let xInPlot = proxy.position(forX: selectedDate) {
                let x = frame.origin.x + xInPlot
                Path { path in
                    path.move(to: CGPoint(x: x, y: frame.minY))
                    path.addLine(to: CGPoint(x: x, y: frame.maxY))
                }
                .stroke(
                    DeskTheme.text.opacity(0.55),
                    style: StrokeStyle(lineWidth: 1, dash: [4, 3])
                )
                .allowsHitTesting(false)
            }
        }
    }
}

extension View {
    /// Fallback selection chrome when the selected raw day is **not** among plot marks
    /// (e.g. weekly display downsample). Uses plotFrame-aligned coordinates.
    ///
    /// When the selected day **is** plotted, prefer in-chart `RuleMark` instead.
    func chartSelectionRuleFallback(
        selectedDate: Date?,
        showFallback: Bool
    ) -> some View {
        chartBackground { proxy in
            GeometryReader { geo in
                if showFallback {
                    ChartSelectionRuleOverlay(
                        proxy: proxy,
                        geo: geo,
                        selectedDate: selectedDate
                    )
                }
            }
        }
    }
}
