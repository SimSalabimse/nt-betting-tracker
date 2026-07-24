import Charts
import SwiftUI

/// Simple charts of the most important Book-aligned stats from `/api/desk` → `charts`.
/// Time series support finger scrubbing (chartXSelection) with day detail callouts.
struct ChartsView: View {
    @EnvironmentObject private var sync: SyncService

    @State private var equitySelection: String?
    @State private var dailySelection: String?
    @State private var drawdownSelection: String?
    @State private var sportSelection: String?

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
                                selectionDetailCard(
                                    title: equitySelection.map { "Equity · \($0)" } ?? "Equity",
                                    lines: equityDetailLines(pts, selected: equitySelection),
                                    isActive: equitySelection != nil
                                )
                                Chart(pts) { p in
                                    let date = p.date ?? ""
                                    LineMark(
                                        x: .value("Date", date),
                                        y: .value("Equity", p.equity ?? 0)
                                    )
                                    .foregroundStyle(DeskTheme.accent)
                                    .interpolationMethod(.linear)

                                    AreaMark(
                                        x: .value("Date", date),
                                        y: .value("Equity", p.equity ?? 0)
                                    )
                                    .foregroundStyle(DeskTheme.accentSoft)
                                    .interpolationMethod(.linear)

                                    if equitySelection == date {
                                        RuleMark(x: .value("Selected", date))
                                            .foregroundStyle(DeskTheme.text.opacity(0.55))
                                            .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 3]))
                                        PointMark(
                                            x: .value("Date", date),
                                            y: .value("Equity", p.equity ?? 0)
                                        )
                                        .foregroundStyle(DeskTheme.accent)
                                        .symbolSize(64)
                                    }
                                }
                                .chartXSelection(value: $equitySelection)
                                .chartOverlay { proxy in
                                    GeometryReader { geo in
                                        Rectangle()
                                            .fill(Color.clear)
                                            .contentShape(Rectangle())
                                            .gesture(scrubGesture(proxy: proxy, geo: geo, selection: $equitySelection))
                                    }
                                }
                                .frame(height: 180)
                                .chartXAxis {
                                    AxisMarks(values: .automatic(desiredCount: 4))
                                }
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(equityChartSummary(pts))
                                .accessibilityHint("Drag horizontally to inspect a day")
                            }
                        }

                        chartSection("Daily P/L") {
                            let pts = charts.daily ?? []
                            if pts.isEmpty {
                                emptySeries("No daily data")
                            } else {
                                selectionDetailCard(
                                    title: dailySelection.map { "Daily P/L · \($0)" } ?? "Daily P/L",
                                    lines: dailyDetailLines(pts, selected: dailySelection),
                                    isActive: dailySelection != nil
                                )
                                Chart(pts) { p in
                                    let date = p.date ?? ""
                                    BarMark(
                                        x: .value("Date", date),
                                        y: .value("P/L", p.pl ?? 0)
                                    )
                                    .foregroundStyle((p.pl ?? 0) >= 0 ? DeskTheme.profit : DeskTheme.loss)
                                    .opacity(dailySelection == nil || dailySelection == date ? 1 : 0.35)

                                    if dailySelection == date {
                                        RuleMark(x: .value("Selected", date))
                                            .foregroundStyle(DeskTheme.text.opacity(0.55))
                                            .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 3]))
                                    }
                                }
                                .chartXSelection(value: $dailySelection)
                                .chartOverlay { proxy in
                                    GeometryReader { geo in
                                        Rectangle()
                                            .fill(Color.clear)
                                            .contentShape(Rectangle())
                                            .gesture(scrubGesture(proxy: proxy, geo: geo, selection: $dailySelection))
                                    }
                                }
                                .frame(height: 160)
                                .chartXAxis {
                                    AxisMarks(values: .automatic(desiredCount: 4))
                                }
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(dailyPLChartSummary(pts))
                                .accessibilityHint("Drag horizontally to inspect a day")
                            }
                        }

                        chartSection("Drawdown") {
                            let pts = charts.drawdown ?? []
                            if pts.isEmpty {
                                emptySeries("No drawdown series")
                            } else {
                                selectionDetailCard(
                                    title: drawdownSelection.map { "Drawdown · \($0)" } ?? "Drawdown",
                                    lines: drawdownDetailLines(pts, selected: drawdownSelection),
                                    isActive: drawdownSelection != nil
                                )
                                Chart(pts) { p in
                                    let date = p.date ?? ""
                                    LineMark(
                                        x: .value("Date", date),
                                        y: .value("DD", p.drawdown ?? 0)
                                    )
                                    .foregroundStyle(DeskTheme.loss)
                                    .interpolationMethod(.linear)

                                    if drawdownSelection == date {
                                        RuleMark(x: .value("Selected", date))
                                            .foregroundStyle(DeskTheme.text.opacity(0.55))
                                            .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 3]))
                                        PointMark(
                                            x: .value("Date", date),
                                            y: .value("DD", p.drawdown ?? 0)
                                        )
                                        .foregroundStyle(DeskTheme.loss)
                                        .symbolSize(64)
                                    }
                                }
                                .chartXSelection(value: $drawdownSelection)
                                .chartOverlay { proxy in
                                    GeometryReader { geo in
                                        Rectangle()
                                            .fill(Color.clear)
                                            .contentShape(Rectangle())
                                            .gesture(scrubGesture(proxy: proxy, geo: geo, selection: $drawdownSelection))
                                    }
                                }
                                .frame(height: 140)
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(drawdownChartSummary(pts))
                                .accessibilityHint("Drag horizontally to inspect a day")
                            }
                        }

                        chartSection("By sport (P/L)") {
                            let sports = (charts.bySport ?? [:])
                                .map { (name: $0.key, pl: $0.value.pl ?? 0, roi: $0.value.roi ?? 0, n: $0.value.n ?? 0) }
                                .sorted { $0.pl > $1.pl }
                            if sports.isEmpty {
                                emptySeries("No sport stats")
                            } else {
                                selectionDetailCard(
                                    title: sportSelection.map { "Sport · \($0)" } ?? "By sport",
                                    lines: sportDetailLines(sports, selected: sportSelection),
                                    isActive: sportSelection != nil
                                )
                                Chart(sports, id: \.name) { s in
                                    BarMark(
                                        x: .value("P/L", s.pl),
                                        y: .value("Sport", s.name)
                                    )
                                    .foregroundStyle(s.pl >= 0 ? DeskTheme.profit : DeskTheme.loss)
                                    .opacity(sportSelection == nil || sportSelection == s.name ? 1 : 0.35)
                                }
                                .chartYSelection(value: $sportSelection)
                                .frame(height: CGFloat(max(120, sports.count * 28)))
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(sportChartSummary(sports))
                                .accessibilityHint("Drag vertically to inspect a sport")
                                ForEach(sports, id: \.name) { s in
                                    HStack {
                                        Text(s.name)
                                            .foregroundStyle(
                                                sportSelection == nil || sportSelection == s.name
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
                                            sportSelection = sportSelection == s.name ? nil : s.name
                                        }
                                    }
                                    .accessibilityElement(children: .combine)
                                    .accessibilityLabel(
                                        "\(s.name), P/L \(DeskFormatters.nok(s.pl, signed: true)), ROI \(DeskFormatters.pct(s.roi)), \(DeskFormatters.int(s.n)) settled"
                                    )
                                    .accessibilityAddTraits(sportSelection == s.name ? .isSelected : [])
                                }
                            }
                        }

                        HStack {
                            Text(charts.rangeLabel ?? "All time")
                                .font(DeskTypography.caption)
                                .foregroundStyle(DeskTheme.textDim)
                            Spacer()
                            Text("Drag chart to inspect")
                                .font(DeskTypography.caption)
                                .foregroundStyle(DeskTheme.textDim)
                        }
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
            .onChange(of: sync.snapshot?.generatedAt) { _, _ in
                // Clear stale scrubbers when desk payload refreshes
                equitySelection = nil
                dailySelection = nil
                drawdownSelection = nil
                sportSelection = nil
            }
        }
    }

    // MARK: - Scrub gesture (finger hover / drag on time series)

    /// Maps horizontal drag to nearest x-axis date string. Works alongside chartXSelection.
    private func scrubGesture(
        proxy: ChartProxy,
        geo: GeometryProxy,
        selection: Binding<String?>
    ) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { value in
                let origin = geo[proxy.plotFrame!].origin
                let x = value.location.x - origin.x
                if let date: String = proxy.value(atX: x) {
                    if selection.wrappedValue != date {
                        selection.wrappedValue = date
                    }
                }
            }
            .onEnded { _ in
                // Keep last selection so user can read the detail card; tap outside not required
            }
    }

    // MARK: - Selection detail card

    private func selectionDetailCard(title: String, lines: [String], isActive: Bool) -> some View {
        VStack(alignment: .leading, spacing: DeskSpacing.s1) {
            Text(title.uppercased())
                .font(DeskTypography.kpiLabel)
                .foregroundStyle(isActive ? DeskTheme.accent : DeskTheme.textDim)
                .tracking(0.4)
            if lines.isEmpty {
                Text(isActive ? "No data for selection" : "Drag on the chart to inspect a point")
                    .font(DeskTypography.caption)
                    .foregroundStyle(DeskTheme.textMuted)
            } else {
                ForEach(Array(lines.enumerated()), id: \.offset) { _, line in
                    Text(line)
                        .font(.system(.footnote, design: .monospaced))
                        .foregroundStyle(DeskTheme.text)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(DeskSpacing.s3)
        .background(
            RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                .fill(isActive ? DeskTheme.surface : DeskTheme.surfaceElev.opacity(0.85))
                .overlay(
                    RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                        .stroke(isActive ? DeskTheme.accent.opacity(0.45) : DeskTheme.borderSoft, lineWidth: 1)
                )
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel(([title] + lines).joined(separator: ", "))
        .animation(.easeInOut(duration: 0.12), value: isActive)
    }

    private func equityDetailLines(_ pts: [EquityPoint], selected: String?) -> [String] {
        guard let selected, let p = pts.first(where: { $0.date == selected }) else { return [] }
        var lines: [String] = []
        lines.append("Equity  \(DeskFormatters.nok(p.equity))")
        if p.dayPl != nil {
            lines.append("Day P/L \(DeskFormatters.nok(p.dayPl, signed: true))")
        }
        if p.cumPl != nil {
            lines.append("Cum P/L \(DeskFormatters.nok(p.cumPl, signed: true))")
        }
        return lines
    }

    private func dailyDetailLines(_ pts: [DailyPoint], selected: String?) -> [String] {
        guard let selected, let p = pts.first(where: { $0.date == selected }) else { return [] }
        var lines: [String] = []
        lines.append("P/L     \(DeskFormatters.nok(p.pl, signed: true))")
        if p.equity != nil {
            lines.append("Equity  \(DeskFormatters.nok(p.equity))")
        }
        return lines
    }

    private func drawdownDetailLines(_ pts: [DrawdownPoint], selected: String?) -> [String] {
        guard let selected, let p = pts.first(where: { $0.date == selected }) else { return [] }
        var lines: [String] = []
        lines.append("Drawdown \(DeskFormatters.nok(p.drawdown))")
        if let pct = p.drawdownPct {
            lines.append("DD %     \(DeskFormatters.pct(pct))")
        }
        if p.equity != nil {
            lines.append("Equity   \(DeskFormatters.nok(p.equity))")
        }
        if p.peak != nil {
            lines.append("Peak     \(DeskFormatters.nok(p.peak))")
        }
        return lines
    }

    private func sportDetailLines(
        _ sports: [(name: String, pl: Double, roi: Double, n: Double)],
        selected: String?
    ) -> [String] {
        guard let selected, let s = sports.first(where: { $0.name == selected }) else { return [] }
        return [
            "P/L  \(DeskFormatters.nok(s.pl, signed: true))",
            "ROI  \(DeskFormatters.pct(s.roi))",
            "n    \(DeskFormatters.int(s.n))",
        ]
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
        // Engine drawdown is non-negative peak−equity; worst = max magnitude.
        let worst = pts.compactMap(\.drawdown).max()
        let worstStr = worst.map { DeskFormatters.nok($0) } ?? "—"
        return "Drawdown series, \(pts.count) points, worst \(worstStr)"
    }

    private func sportChartSummary(
        _ sports: [(name: String, pl: Double, roi: Double, n: Double)]
    ) -> String {
        "By sport P/L, \(sports.count) sports"
    }
}
