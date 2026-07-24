import Charts
import SwiftUI

/// Simple charts of the most important Book-aligned stats from `/api/desk` → `charts`.
struct ChartsView: View {
    @EnvironmentObject private var sync: SyncService

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DeskSpacing.s5) {
                    FreshnessBanner()
                    if let charts = sync.snapshot?.charts {
                        if let o = charts.overall {
                            summaryStrip(overall: o, maxDrawdown: charts.maxDrawdown)
                        }

                        chartSection("Equity") {
                            let pts = charts.equityCurve ?? []
                            if pts.isEmpty {
                                emptySeries("No settled history")
                            } else {
                                Chart(pts) { p in
                                    LineMark(
                                        x: .value("Date", p.date ?? ""),
                                        y: .value("Equity", p.equity ?? 0)
                                    )
                                    .foregroundStyle(DeskTheme.accent)
                                    AreaMark(
                                        x: .value("Date", p.date ?? ""),
                                        y: .value("Equity", p.equity ?? 0)
                                    )
                                    .foregroundStyle(DeskTheme.accentSoft)
                                }
                                .frame(height: 180)
                                .chartXAxis {
                                    AxisMarks(values: .automatic(desiredCount: 4))
                                }
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(equityChartSummary(pts))
                            }
                        }

                        chartSection("Daily P/L") {
                            let pts = charts.daily ?? []
                            if pts.isEmpty {
                                emptySeries("No daily data")
                            } else {
                                Chart(pts) { p in
                                    BarMark(
                                        x: .value("Date", p.date ?? ""),
                                        y: .value("P/L", p.pl ?? 0)
                                    )
                                    .foregroundStyle((p.pl ?? 0) >= 0 ? DeskTheme.profit : DeskTheme.loss)
                                }
                                .frame(height: 160)
                                .chartXAxis {
                                    AxisMarks(values: .automatic(desiredCount: 4))
                                }
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(dailyPLChartSummary(pts))
                            }
                        }

                        chartSection("Drawdown") {
                            let pts = charts.drawdown ?? []
                            if pts.isEmpty {
                                emptySeries("No drawdown series")
                            } else {
                                Chart(pts) { p in
                                    LineMark(
                                        x: .value("Date", p.date ?? ""),
                                        y: .value("DD", p.drawdown ?? 0)
                                    )
                                    .foregroundStyle(DeskTheme.loss)
                                }
                                .frame(height: 140)
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(drawdownChartSummary(pts))
                            }
                        }

                        chartSection("By sport (P/L)") {
                            let sports = (charts.bySport ?? [:])
                                .map { (name: $0.key, pl: $0.value.pl ?? 0, roi: $0.value.roi ?? 0, n: $0.value.n ?? 0) }
                                .sorted { $0.pl > $1.pl }
                            if sports.isEmpty {
                                emptySeries("No sport stats")
                            } else {
                                Chart(sports, id: \.name) { s in
                                    BarMark(
                                        x: .value("P/L", s.pl),
                                        y: .value("Sport", s.name)
                                    )
                                    .foregroundStyle(s.pl >= 0 ? DeskTheme.profit : DeskTheme.loss)
                                }
                                .frame(height: CGFloat(max(120, sports.count * 28)))
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(sportChartSummary(sports))
                                ForEach(sports, id: \.name) { s in
                                    HStack {
                                        Text(s.name)
                                            .foregroundStyle(DeskTheme.text)
                                        Spacer()
                                        Text("n=\(DeskFormatters.int(s.n))")
                                            .foregroundStyle(DeskTheme.textMuted)
                                        Text(DeskFormatters.pct(s.roi))
                                            .foregroundStyle(DeskTheme.pl(s.roi))
                                    }
                                    .font(DeskTypography.caption)
                                    .fontDesign(.monospaced)
                                    .accessibilityElement(children: .combine)
                                    .accessibilityLabel(
                                        "\(s.name), P/L \(DeskFormatters.nok(s.pl, signed: true)), ROI \(DeskFormatters.pct(s.roi)), \(DeskFormatters.int(s.n)) settled"
                                    )
                                }
                            }
                        }

                        Text(charts.rangeLabel ?? "All time")
                            .font(DeskTypography.caption)
                            .foregroundStyle(DeskTheme.textDim)
                    } else {
                        emptyState
                    }
                }
                .padding(DeskSpacing.contentPad)
            }
            .background(DeskTheme.bg.ignoresSafeArea())
            .navigationTitle("Charts")
            .toolbarBackground(DeskTheme.surface, for: .navigationBar)
            .refreshable { await sync.sync() }
        }
    }

    // MARK: - Summary strip

    private func summaryStrip(overall o: OverallStats, maxDrawdown: Double?) -> some View {
        HStack(spacing: DeskSpacing.s2) {
            statCell("ROI", DeskFormatters.pct(o.roi, signed: true), color: DeskTheme.pl(o.roi))
            statCell("WR", DeskFormatters.pct(o.winrate), color: DeskTheme.text)
            statCell("P/L", DeskFormatters.nok(o.pl, signed: true), color: DeskTheme.pl(o.pl))
            statCell("DD", DeskFormatters.nok(maxDrawdown), color: DeskTheme.loss)
        }
    }

    private func statCell(_ label: String, _ value: String, color: Color) -> some View {
        VStack(spacing: DeskSpacing.s1) {
            Text(label.uppercased())
                .font(DeskTypography.kpiLabel)
                .foregroundStyle(DeskTheme.textDim)
            Text(value)
                .font(.system(.subheadline, design: .monospaced).weight(.semibold))
                .foregroundStyle(color)
                .minimumScaleFactor(0.6)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, DeskSpacing.s2)
        .padding(.horizontal, DeskSpacing.s1)
        .background(
            RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                .fill(DeskTheme.surfaceElev)
                .overlay(
                    RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                        .stroke(DeskTheme.borderSoft, lineWidth: 1)
                )
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(label), \(value)")
    }

    // MARK: - Sections

    private func chartSection<Content: View>(
        _ title: String,
        @ViewBuilder content: @escaping () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: DeskSpacing.s2) {
            Text(title.uppercased())
                .font(DeskTypography.sectionLabel)
                .foregroundStyle(DeskTheme.textDim)
                .tracking(0.6)
                .accessibilityAddTraits(.isHeader)
            DeskCard(content: content)
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

    private var emptyState: some View {
        VStack(spacing: DeskSpacing.s4) {
            Image(systemName: "chart.xyaxis.line")
                .font(.system(size: 40))
                .foregroundStyle(DeskTheme.textDim)
                .accessibilityHidden(true)
            Text("No chart data")
                .font(DeskTypography.sectionTitle)
                .foregroundStyle(DeskTheme.text)
            Text("Pull to refresh after syncing settled history from the PC.")
                .font(DeskTypography.caption)
                .foregroundStyle(DeskTheme.textMuted)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, DeskSpacing.s7)
        .padding(.horizontal, DeskSpacing.s4)
        .background(
            RoundedRectangle(cornerRadius: DeskSpacing.radius)
                .fill(DeskTheme.surfaceElev)
                .overlay(
                    RoundedRectangle(cornerRadius: DeskSpacing.radius)
                        .stroke(DeskTheme.borderSoft, lineWidth: 1)
                )
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel("No chart data. Pull to refresh after syncing settled history from the PC.")
    }

    // MARK: - Chart VoiceOver summaries

    private func equityChartSummary(_ pts: [EquityPoint]) -> String {
        let last = pts.last?.equity
        let lastStr = last.map { DeskFormatters.nok($0) } ?? "—"
        return "Equity curve, \(pts.count) points, latest \(lastStr)"
    }

    private func dailyPLChartSummary(_ pts: [DailyPoint]) -> String {
        let total = pts.compactMap(\.pl).reduce(0, +)
        return "Daily P/L, \(pts.count) days, total \(DeskFormatters.nok(total, signed: true))"
    }

    private func drawdownChartSummary(_ pts: [DrawdownPoint]) -> String {
        let worst = pts.compactMap(\.drawdown).min()
        let worstStr = worst.map { DeskFormatters.nok($0) } ?? "—"
        return "Drawdown series, \(pts.count) points, worst \(worstStr)"
    }

    private func sportChartSummary(
        _ sports: [(name: String, pl: Double, roi: Double, n: Double)]
    ) -> String {
        "By sport P/L, \(sports.count) sports"
    }
}
