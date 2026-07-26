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

    /// Zoom Y to the series span (not 0…equity). Floor is soft (~3% of level)
    /// so a ~50 NOK run on a ~550 bank is clearly visible, not flat.
    private var yDomain: ClosedRange<Double>? {
        ChartAxisSupport.adaptiveDomain(
            plotPoints.map(\.equity),
            minRelativeSpan: 0.03,
            padFraction: 0.10,
            absoluteFloor: 5.0
        )
    }

    private var areaBase: Double {
        yDomain?.lowerBound ?? 0
    }

    var body: some View {
        if points.isEmpty {
            emptySeries("No settled history")
        } else {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                ChartSelectionCallout(
                    title: selectedRawDay.map { "EOD equity · \($0)" } ?? "Equity (match date)",
                    lines: ChartDataBuilder.equityDetailLines(points, selected: selectedRawDay),
                    isActive: selectedRawDay != nil,
                    onDismiss: { clearSelection() }
                )

                Chart(plotPoints) { p in
                    LineMark(
                        x: .value("Date", p.day.date),
                        y: .value("Equity", p.equity)
                    )
                    .foregroundStyle(DeskTheme.accent)
                    .interpolationMethod(.linear)
                    .lineStyle(StrokeStyle(lineWidth: 2))

                    // Fill from domain floor (not 0) so area matches adaptive scale.
                    AreaMark(
                        x: .value("Date", p.day.date),
                        yStart: .value("Base", areaBase),
                        yEnd: .value("Equity", p.equity)
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
                    // Sticky while scrubbing: update day when finger moves; lift keeps detail
                    // until user taps out / taps callout (clearSelection).
                    if let newValue {
                        selectedRawDay = ChartDataBuilder.nearestRawDay(to: newValue, in: points)
                    }
                }
                .onChange(of: selectedRawDay) { _, newValue in
                    if newValue == nil { scrubDate = nil }
                }
                // Non-plot raw selection (weekly downsample): plotFrame-aligned dashed rule.
                .chartSelectionRuleFallback(
                    selectedDate: selectedDate,
                    showFallback: selectedRawDay != nil && !selectedInPlot
                )
                .chartYScale(domain: yDomain ?? 0...1)
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
                .accessibilityLabel(ChartDataBuilder.equitySummary(points))
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
