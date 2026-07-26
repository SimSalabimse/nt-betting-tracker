import Charts
import SwiftUI

/// Drawdown series with UTC date axis and multi-field callout.
struct DrawdownChartView: View {
    let points: [DrawdownChartPoint]
    @Binding var selectedRawDay: String?
    var height: CGFloat = ChartAxisSupport.compactBarHeight

    private var density: ChartAxisDensity {
        ChartAxisDensity.forPointCount(points.count)
    }

    private var plotPoints: [DrawdownChartPoint] {
        ChartDataBuilder.displayDrawdown(points)
    }

    private var days: [ChartDay] { points.map(\.day) }

    /// Sticky inspect: last raw day is kept when the gesture ends (`scrubDate` → nil).
    @State private var scrubDate: Date?

    private var selectedInPlot: Bool {
        guard let raw = selectedRawDay else { return false }
        return plotPoints.contains(where: { $0.day.raw == raw })
    }

    private var selectedDate: Date? {
        guard let raw = selectedRawDay else { return nil }
        return points.first(where: { $0.day.raw == raw })?.day.date
    }

    var body: some View {
        if points.isEmpty {
            emptySeries("No drawdown series")
        } else {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                ChartSelectionCallout(
                    title: selectedRawDay.map { "Drawdown · \($0)" } ?? "Drawdown",
                    lines: ChartDataBuilder.drawdownDetailLines(points, selected: selectedRawDay),
                    isActive: selectedRawDay != nil
                )

                Chart(plotPoints) { p in
                    LineMark(
                        x: .value("Date", p.day.date),
                        y: .value("DD", p.drawdown)
                    )
                    .foregroundStyle(DeskTheme.loss)
                    .interpolationMethod(.linear)

                    if selectedRawDay == p.day.raw {
                        RuleMark(x: .value("Selected", p.day.date))
                            .foregroundStyle(DeskTheme.text.opacity(0.55))
                            .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 3]))
                        PointMark(
                            x: .value("Date", p.day.date),
                            y: .value("DD", p.drawdown)
                        )
                        .foregroundStyle(DeskTheme.loss)
                        .symbolSize(64)
                    }
                }
                .chartXSelection(value: $scrubDate)
                .onChange(of: scrubDate) { _, newValue in
                    if let newValue {
                        selectedRawDay = ChartDataBuilder.nearestRawDay(to: newValue, in: points)
                    }
                }
                .chartSelectionRuleFallback(
                    selectedDate: selectedDate,
                    showFallback: selectedRawDay != nil && !selectedInPlot
                )
                .frame(height: height)
                .chartXAxis {
                    ChartAxisSupport.dateAxisMarks(days: days, density: density)
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(ChartDataBuilder.drawdownSummary(points))
                .accessibilityValue(selectedRawDay.map { "Selected \($0)" } ?? "No day selected")
                .accessibilityHint("Drag horizontally to inspect a day")
            }
        }
    }

    private func emptySeries(_ message: String) -> some View {
        Text(message)
            .font(DeskTypography.caption)
            .foregroundStyle(DeskTheme.textMuted)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, DeskSpacing.s2)
            .accessibilityLabel(message)
    }
}
