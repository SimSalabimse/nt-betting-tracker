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

    @State private var scrubDate: Date?

    var body: some View {
        if points.isEmpty {
            emptySeries("No daily data")
        } else {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                ChartSelectionCallout(
                    title: selectedRawDay.map { "Daily P/L · \($0)" } ?? "Daily P/L",
                    lines: ChartDataBuilder.dailyDetailLines(points, selected: selectedRawDay),
                    isActive: selectedRawDay != nil
                )

                Chart(plotPoints) { p in
                    BarMark(
                        x: .value("Date", p.day.date, unit: .day),
                        y: .value("P/L", p.pl)
                    )
                    .foregroundStyle(p.pl >= 0 ? DeskTheme.profit : DeskTheme.loss)
                    .opacity(selectedRawDay == nil || selectedRawDay == p.day.raw ? 1 : 0.35)

                    if selectedRawDay == p.day.raw {
                        RuleMark(x: .value("Selected", p.day.date))
                            .foregroundStyle(DeskTheme.text.opacity(0.55))
                            .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 3]))
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
                .frame(height: height)
                .chartXAxis {
                    ChartAxisSupport.dateAxisMarks(days: days, density: density)
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(ChartDataBuilder.dailySummary(points))
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
