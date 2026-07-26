import Charts
import SwiftUI

/// Horizontal sport P/L bars with selection callout and list rows.
struct SportChartView: View {
    let sports: [SportChartPoint]
    @Binding var selectedSport: String?
    var chartHeight: CGFloat? = nil

    private var resolvedHeight: CGFloat {
        chartHeight ?? CGFloat(max(120, sports.count * 28))
    }

    private var xDomain: ClosedRange<Double>? {
        ChartAxisSupport.adaptiveDomain(
            sports.map(\.pl),
            includeZero: true,
            minRelativeSpan: 0.0,
            absoluteFloor: 8.0
        )
    }

    var body: some View {
        if sports.isEmpty {
            emptySeries("No sport stats")
        } else {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                ChartSelectionCallout(
                    title: selectedSport.map { "Sport · \($0)" } ?? "By sport",
                    lines: ChartDataBuilder.sportDetailLines(sports, selected: selectedSport),
                    isActive: selectedSport != nil,
                    idleHint: "Drag or tap a sport to inspect",
                    onDismiss: { selectedSport = nil }
                )

                Chart(sports) { s in
                    BarMark(
                        x: .value("P/L", s.pl),
                        y: .value("Sport", s.name)
                    )
                    .foregroundStyle(s.pl >= 0 ? DeskTheme.profit : DeskTheme.loss)
                    .opacity(selectedSport == nil || selectedSport == s.name ? 1 : 0.35)

                    RuleMark(x: .value("Zero", 0))
                        .foregroundStyle(DeskTheme.borderSoft)
                        .lineStyle(StrokeStyle(lineWidth: 1))
                }
                .chartXScale(domain: xDomain ?? -10...10)
                .chartYSelection(value: $selectedSport)
                .frame(height: resolvedHeight)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(ChartDataBuilder.sportSummary(sports))
                .accessibilityHint("Drag vertically to inspect a sport")

                ForEach(sports) { s in
                    HStack {
                        Text(s.name)
                            .foregroundStyle(
                                selectedSport == nil || selectedSport == s.name
                                    ? DeskTheme.text
                                    : DeskTheme.textMuted
                            )
                        Spacer()
                        Text("n=\(DeskFormatters.int(s.n))")
                            .foregroundStyle(DeskTheme.textMuted)
                        Text(DeskFormatters.pct(s.roi))
                            .foregroundStyle(DeskTheme.pl(s.roi))
                    }
                    .font(DeskTypography.caption)
                    .fontDesign(.monospaced)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        withAnimation(.easeInOut(duration: 0.15)) {
                            selectedSport = selectedSport == s.name ? nil : s.name
                        }
                    }
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel(
                        "\(s.name), P/L \(DeskFormatters.nok(s.pl, signed: true)), ROI \(DeskFormatters.pct(s.roi)), \(DeskFormatters.int(s.n)) settled"
                    )
                    .accessibilityAddTraits(selectedSport == s.name ? .isSelected : [])
                }
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
