import Charts
import SwiftUI

/// Tiny equity sparkline for the Desk header (display-only).
struct EquitySparklineView: View {
    let points: [EquityChartPoint]
    var height: CGFloat = 52

    private var yDomain: ClosedRange<Double>? {
        // Desk sparkline: zoom to true min…max with light pad (no heavy floor).
        ChartAxisSupport.adaptiveDomain(
            points.map(\.equity),
            minRelativeSpan: 0.0,
            padFraction: 0.12,
            absoluteFloor: 3.0
        )
    }

    private var areaBase: Double {
        yDomain?.lowerBound ?? 0
    }

    var body: some View {
        if points.count < 2 {
            EmptyView()
        } else {
            Chart(points) { p in
                LineMark(
                    x: .value("D", p.day.date),
                    y: .value("E", p.equity)
                )
                .foregroundStyle(DeskTheme.accent)
                .interpolationMethod(.linear)
                .lineStyle(StrokeStyle(lineWidth: 2))
                AreaMark(
                    x: .value("D", p.day.date),
                    yStart: .value("Base", areaBase),
                    yEnd: .value("E", p.equity)
                )
                .foregroundStyle(DeskTheme.accent.opacity(0.22))
            }
            .chartYScale(domain: yDomain ?? 0...1)
            .chartPlotStyle { plot in
                plot.background(DeskTheme.surface3.opacity(0.35))
            }
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .chartLegend(.hidden)
            // Flatten to a single texture — cheap for a non-interactive sparkline.
            .drawingGroup(opaque: false, colorMode: .nonLinear)
            .frame(height: height)
            .accessibilityLabel("Equity trend, \(points.count) days")
            .accessibilityValue({
                guard let first = points.first?.equity, let last = points.last?.equity else {
                    return ""
                }
                let delta = last - first
                return "From \(DeskFormatters.nok(first)) to \(DeskFormatters.nok(last)), change \(DeskFormatters.nok(delta, signed: true))"
            }())
        }
    }
}
