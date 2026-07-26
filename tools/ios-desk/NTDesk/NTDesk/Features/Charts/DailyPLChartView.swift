import Charts
import SwiftUI

/// Daily P/L bars with UTC date axis and multi-field callout.
struct DailyPLChartView: View {
    let points: [DailyChartPoint]
    @Binding var selectedRawDay: String?
    var height: CGFloat = ChartAxisSupport.compactBarHeight

    private var density: ChartAxisDensity {
        ChartAxisDensity.forPointCount(points.count)
    }

    private var plotPoints: [DailyChartPoint] {
        ChartDataBuilder.displayDaily(points)
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

    /// Keep zero baseline; pad to data extremes without a huge empty axis.
    private var yDomain: ClosedRange<Double>? {
        ChartAxisSupport.adaptiveDomain(
            plotPoints.map(\.pl),
            includeZero: true,
            minRelativeSpan: 0.0,
            absoluteFloor: 8.0
        )
    }

    var body: some View {
        if points.isEmpty {
            emptySeries("No daily data")
        } else {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                ChartSelectionCallout(
                    title: selectedRawDay.map { "Daily P/L · \($0)" } ?? "Daily P/L",
                    lines: ChartDataBuilder.dailyDetailLines(points, selected: selectedRawDay),
                    isActive: selectedRawDay != nil,
                    onDismiss: { clearSelection() }
                )

                Chart(plotPoints) { p in
                    BarMark(
                        x: .value("Date", p.day.date, unit: .day),
                        y: .value("P/L", p.pl)
                    )
                    .foregroundStyle(p.pl >= 0 ? DeskTheme.profit : DeskTheme.loss)
                    // Dim only when selected raw is among plot bars; otherwise all full opacity + fallback rule.
                    .opacity(barOpacity(for: p))

                    if selectedRawDay == p.day.raw {
                        RuleMark(x: .value("Selected", p.day.date))
                            .foregroundStyle(DeskTheme.text.opacity(0.55))
                            .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 3]))
                    }

                    // Zero baseline for signed P/L.
                    RuleMark(y: .value("Zero", 0))
                        .foregroundStyle(DeskTheme.borderSoft)
                        .lineStyle(StrokeStyle(lineWidth: 1))
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
                .chartYScale(domain: yDomain ?? -10...10)
                .chartYAxis {
                    AxisMarks(position: .leading, values: .automatic(desiredCount: 4)) { value in
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                            .foregroundStyle(DeskTheme.borderSoft)
                        AxisValueLabel {
                            if let v = value.as(Double.self) {
                                Text(String(format: "%+.0f", v))
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
                .accessibilityLabel(ChartDataBuilder.dailySummary(points))
                .accessibilityValue(selectedRawDay.map { "Selected \($0)" } ?? "No day selected")
                .accessibilityHint("Drag horizontally to inspect a day")
            }
        }
    }

    private func clearSelection() {
        selectedRawDay = nil
        scrubDate = nil
    }

    /// When selected raw ∉ plotPoints (weekly max-abs reduction), leave all bars full opacity.
    private func barOpacity(for p: DailyChartPoint) -> Double {
        guard let selected = selectedRawDay else { return 1 }
        guard selectedInPlot else { return 1 }
        return selected == p.day.raw ? 1 : 0.35
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
