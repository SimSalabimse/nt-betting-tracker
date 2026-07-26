import Charts
import SwiftUI

/// Tiny equity sparkline for the Desk header (display-only).
struct EquitySparklineView: View {
    let points: [EquityChartPoint]
    var height: CGFloat = 44

    private var yDomain: ClosedRange<Double>? {
        ChartAxisSupport.adaptiveDomain(points.map(\.equity), minRelativeSpan: 0.05, padFraction: 0.1)
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
                .lineStyle(StrokeStyle(lineWidth: 1.5))
                AreaMark(
                    x: .value("D", p.day.date),
                    yStart: .value("Base", areaBase),
                    yEnd: .value("E", p.equity)
                )
                .foregroundStyle(DeskTheme.accentSoft)
            }
            .chartYScale(domain: yDomain ?? 0...1)
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .chartLegend(.hidden)
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
