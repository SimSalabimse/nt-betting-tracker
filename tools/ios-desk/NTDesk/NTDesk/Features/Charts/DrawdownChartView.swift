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

    @State private var scrubDate: Date?

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
                    selectedRawDay = ChartDataBuilder.nearestRawDay(to: newValue, in: points)
                }
                .chartOverlay { proxy in
                    GeometryReader { geo in
                        Rectangle()
                            .fill(Color.clear)
                            .contentShape(Rectangle())
                            .gesture(scrubGesture(proxy: proxy, geo: geo))
                    }
                }
                .chartBackground { proxy in
                    GeometryReader { _ in
                        if let raw = selectedRawDay,
                           let pt = points.first(where: { $0.day.raw == raw }),
                           plotPoints.contains(where: { $0.day.raw == raw }) == false,
                           let xPos = proxy.position(forX: pt.day.date) {
                            Path { path in
                                path.move(to: CGPoint(x: xPos, y: 0))
                                path.addLine(to: CGPoint(x: xPos, y: proxy.plotSize.height))
                            }
                            .stroke(DeskTheme.text.opacity(0.55), style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
                        }
                    }
                }
                .frame(height: height)
                .chartXAxis {
                    ChartAxisSupport.dateAxisMarks(days: days, density: density)
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(ChartDataBuilder.drawdownSummary(points))
                .accessibilityHint("Drag horizontally to inspect a day")
            }
        }
    }

    private func scrubGesture(proxy: ChartProxy, geo: GeometryProxy) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { value in
                guard let frame = proxy.plotFrame else { return }
                let origin = geo[frame].origin
                let x = value.location.x - origin.x
                if let date: Date = proxy.value(atX: x) {
                    scrubDate = date
                    selectedRawDay = ChartDataBuilder.nearestRawDay(to: date, in: points)
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
