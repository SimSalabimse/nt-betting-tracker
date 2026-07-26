import Charts
import SwiftUI

/// Equity curve with UTC date axis, multi-field callout, compact/expanded heights.
struct EquityChartView: View {
    let points: [EquityChartPoint]
    @Binding var selectedRawDay: String?
    var height: CGFloat = ChartAxisSupport.compactHeight

    private var density: ChartAxisDensity {
        ChartAxisDensity.forPointCount(points.count)
    }

    private var plotPoints: [EquityChartPoint] {
        ChartDataBuilder.displayEquity(points)
    }

    private var days: [ChartDay] { points.map(\.day) }

    /// Bridge continuous Date selection → stable API day string.
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
            emptySeries("No settled history")
        } else {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                ChartSelectionCallout(
                    title: selectedRawDay.map { "Equity · \($0)" } ?? "Equity",
                    lines: ChartDataBuilder.equityDetailLines(points, selected: selectedRawDay),
                    isActive: selectedRawDay != nil
                )

                Chart(plotPoints) { p in
                    LineMark(
                        x: .value("Date", p.day.date),
                        y: .value("Equity", p.equity)
                    )
                    .foregroundStyle(DeskTheme.accent)
                    .interpolationMethod(.linear)

                    AreaMark(
                        x: .value("Date", p.day.date),
                        y: .value("Equity", p.equity)
                    )
                    .foregroundStyle(DeskTheme.accentSoft)
                    .interpolationMethod(.linear)

                    // In-plot selection chrome (RuleMark + point).
                    if selectedRawDay == p.day.raw {
                        RuleMark(x: .value("Selected", p.day.date))
                            .foregroundStyle(DeskTheme.text.opacity(0.55))
                            .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 3]))
                        PointMark(
                            x: .value("Date", p.day.date),
                            y: .value("Equity", p.equity)
                        )
                        .foregroundStyle(DeskTheme.accent)
                        .symbolSize(64)
                    }
                }
                // Single scrub path: chartXSelection only (no dual DragGesture).
                .chartXSelection(value: $scrubDate)
                .onChange(of: scrubDate) { _, newValue in
                    // Sticky: only update when we have a date; do not clear on lift.
                    if let newValue {
                        selectedRawDay = ChartDataBuilder.nearestRawDay(to: newValue, in: points)
                    }
                }
                // Non-plot raw selection (weekly downsample): plotFrame-aligned dashed rule.
                .chartSelectionRuleFallback(
                    selectedDate: selectedDate,
                    showFallback: selectedRawDay != nil && !selectedInPlot
                )
                .frame(height: height)
                .chartXAxis {
                    ChartAxisSupport.dateAxisMarks(days: days, density: density)
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(ChartDataBuilder.equitySummary(points))
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
