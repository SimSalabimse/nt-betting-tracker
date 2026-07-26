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

    /// Drawdown is ≥ 0 from peak; keep 0 baseline and adapt upper bound.
    private var yDomain: ClosedRange<Double>? {
        ChartAxisSupport.adaptiveDomain(
            plotPoints.map(\.drawdown),
            includeZero: true,
            minRelativeSpan: 0.08,
            absoluteFloor: 5.0
        )
    }

    var body: some View {
        if points.isEmpty {
            emptySeries("No drawdown series")
        } else {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                ChartSelectionCallout(
                    title: selectedRawDay.map { "Drawdown · \($0)" } ?? "Drawdown",
                    lines: ChartDataBuilder.drawdownDetailLines(points, selected: selectedRawDay),
                    isActive: selectedRawDay != nil,
                    onDismiss: { clearSelection() }
                )

                Chart(plotPoints) { p in
                    AreaMark(
                        x: .value("Date", p.day.date),
                        yStart: .value("Zero", 0),
                        yEnd: .value("DD", p.drawdown)
                    )
                    .foregroundStyle(DeskTheme.loss.opacity(0.22))
                    .interpolationMethod(.linear)

                    LineMark(
                        x: .value("Date", p.day.date),
                        y: .value("DD", p.drawdown)
                    )
                    .foregroundStyle(DeskTheme.loss)
                    .interpolationMethod(.linear)
                    .lineStyle(StrokeStyle(lineWidth: 2))

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
                .onChange(of: selectedRawDay) { _, newValue in
                    if newValue == nil { scrubDate = nil }
                }
                .chartSelectionRuleFallback(
                    selectedDate: selectedDate,
                    showFallback: selectedRawDay != nil && !selectedInPlot
                )
                .chartYScale(domain: yDomain ?? 0...10)
                .chartYAxis {
                    AxisMarks(position: .leading, values: .automatic(desiredCount: 4)) { value in
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                            .foregroundStyle(DeskTheme.borderSoft)
                        AxisValueLabel {
                            if let v = value.as(Double.self) {
                                Text(String(format: "%.0f", v))
                                    .font(DeskTypography.caption)
                                    .foregroundStyle(DeskTheme.textMuted)
                            }
                        }
                    }
                }
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

    private func clearSelection() {
        selectedRawDay = nil
        scrubDate = nil
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
