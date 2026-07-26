import SwiftUI

/// Compact charts list of Book-aligned stats from `/api/desk` → `charts`.
/// Time series use UTC date axes, multi-field callouts, and expand-to-full-screen.
struct ChartsView: View {
    @EnvironmentObject private var sync: SyncService

    @State private var equitySelection: String?
    @State private var dailySelection: String?
    @State private var drawdownSelection: String?
    @State private var sportSelection: String?
    @State private var expanded: ExpandableChartKind?

    /// Pre-built on a background queue so large ledgers don't hitch the main thread.
    @State private var equityPoints: [EquityChartPoint] = []
    @State private var dailyPoints: [DailyChartPoint] = []
    /// Full-era daily series for the performance calendar (not clipped by 1w/1m chips).
    @State private var calendarPoints: [DailyChartPoint] = []
    @State private var drawdownPoints: [DrawdownChartPoint] = []
    @State private var sportPoints: [SportChartPoint] = []
    @State private var overall: OverallStats?
    @State private var maxDrawdown: Double?
    @State private var rangeLabel: String?
    @State private var isBuildingSeries = false
    @AppStorage("charts_range_key") private var rangeKey: String = "all"

    private let rangeOptions: [(key: String, label: String, days: Int?)] = [
        ("1w", "1w", 7),
        ("1m", "1m", 30),
        ("all", "All", nil),
    ]

    var body: some View {
        DeskScreenChrome(title: "Charts") {
            ScrollView {
                VStack(alignment: .leading, spacing: DeskSpacing.s5) {
                    FreshnessBanner()
                        .onTapGesture { clearAllSelections() }

                    // Range chips — client filter on full era series from PC.
                    HStack(spacing: DeskSpacing.s2) {
                        ForEach(rangeOptions, id: \.key) { opt in
                            Button {
                                rangeKey = opt.key
                                clearAllSelections()
                                Task { await rebuildSeriesInBackground() }
                            } label: {
                                Text(opt.label)
                                    .font(.caption.weight(.semibold))
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 7)
                                    .background(
                                        Capsule()
                                            .fill(rangeKey == opt.key ? DeskTheme.accent.opacity(0.28) : DeskTheme.surfaceElev)
                                    )
                                    .overlay(
                                        Capsule()
                                            .stroke(rangeKey == opt.key ? DeskTheme.accent : DeskTheme.borderSoft, lineWidth: 1)
                                    )
                                    .foregroundStyle(rangeKey == opt.key ? DeskTheme.accent : DeskTheme.textMuted)
                            }
                            .buttonStyle(.plain)
                        }
                        Spacer()
                    }
                    .accessibilityElement(children: .contain)
                    .accessibilityLabel("Chart date range")

                    // Secure Variant A — capital partition (not time-series); lives on Charts.
                    if let s = sync.snapshot {
                        SecureBucketCard(snapshot: s)
                            .onTapGesture { clearAllSelections() }
                    }

                    if sync.snapshot?.charts != nil {
                        if isBuildingSeries && equityPoints.isEmpty {
                            ProgressView("Preparing charts…")
                                .tint(DeskTheme.accent)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, DeskSpacing.s4)
                        }
                        if let o = overall {
                            summaryStrip(overall: o, maxDrawdown: maxDrawdown)
                                .onTapGesture { clearAllSelections() }
                        }

                        chartSection(.equity) {
                            EquityChartView(
                                points: equityPoints,
                                selectedRawDay: $equitySelection
                            )
                        }

                        // Performance calendar — month heatmap from full-era daily P/L (PC Book style).
                        VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                            HStack {
                                Text("PERFORMANCE CALENDAR")
                                    .font(DeskTypography.sectionLabel)
                                    .foregroundStyle(DeskTheme.textDim)
                                    .tracking(0.6)
                                    .accessibilityAddTraits(.isHeader)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .contentShape(Rectangle())
                                    .onTapGesture { clearAllSelections() }
                                Button {
                                    expanded = .calendar
                                } label: {
                                    Label("Expand", systemImage: "arrow.up.left.and.arrow.down.right")
                                        .labelStyle(.iconOnly)
                                        .font(.body.weight(.medium))
                                        .foregroundStyle(DeskTheme.accent)
                                        .frame(minWidth: 44, minHeight: 44)
                                        .contentShape(Rectangle())
                                }
                                .buttonStyle(.plain)
                                .accessibilityLabel("Expand Performance calendar")
                                .accessibilityHint("Opens a larger full-screen calendar")
                                .accessibilityIdentifier("charts.expand.calendar")
                            }
                            DeskCard {
                                PerformanceCalendarView(
                                    points: calendarPoints,
                                    selectedRawDay: $dailySelection
                                )
                            }
                        }

                        chartSection(.daily) {
                            DailyPLChartView(
                                points: dailyPoints,
                                selectedRawDay: $dailySelection
                            )
                        }

                        chartSection(.drawdown) {
                            DrawdownChartView(
                                points: drawdownPoints,
                                selectedRawDay: $drawdownSelection
                            )
                        }

                        chartSection(.sport) {
                            SportChartView(
                                sports: sportPoints,
                                selectedSport: $sportSelection
                            )
                        }

                        HStack {
                            Text(rangeLabel ?? "All time")
                                .font(DeskTypography.caption)
                                .foregroundStyle(DeskTheme.textDim)
                            Spacer()
                            Text("Drag to inspect · tap callout to close")
                                .font(DeskTypography.caption)
                                .foregroundStyle(DeskTheme.textDim)
                        }
                        .contentShape(Rectangle())
                        .onTapGesture { clearAllSelections() }
                    } else {
                        emptyState
                            .onTapGesture { clearAllSelections() }
                    }
                }
                .padding(DeskSpacing.contentPad)
            }
            .background(DeskTheme.bg.ignoresSafeArea())
            .refreshable { await sync.sync(waitForConnectivity: true) }
            .task(id: sync.snapshot?.generatedAt) {
                await rebuildSeriesInBackground()
            }
            .onChange(of: sync.snapshot?.generatedAt) { _, _ in
                clearAllSelections()
            }
            // Selecting one series clears the others so only one callout stays open.
            .onChange(of: equitySelection) { _, new in
                if new != nil {
                    dailySelection = nil
                    drawdownSelection = nil
                    sportSelection = nil
                }
            }
            .onChange(of: dailySelection) { _, new in
                if new != nil {
                    equitySelection = nil
                    drawdownSelection = nil
                    sportSelection = nil
                }
            }
            .onChange(of: drawdownSelection) { _, new in
                if new != nil {
                    equitySelection = nil
                    dailySelection = nil
                    sportSelection = nil
                }
            }
            .onChange(of: sportSelection) { _, new in
                if new != nil {
                    equitySelection = nil
                    dailySelection = nil
                    drawdownSelection = nil
                }
            }
            .fullScreenCover(item: $expanded) { kind in
                ChartExpandedContainer(title: kind.title) {
                    expandedBody(kind)
                } onDismiss: {
                    expanded = nil
                }
            }
        }
    }

    private func clearAllSelections() {
        equitySelection = nil
        dailySelection = nil
        drawdownSelection = nil
        sportSelection = nil
    }

    /// Decode/map chart points off the main actor; apply range filter (1w / 1m / all).
    private func rebuildSeriesInBackground() async {
        guard let charts = sync.snapshot?.charts else {
            equityPoints = []
            dailyPoints = []
            calendarPoints = []
            drawdownPoints = []
            sportPoints = []
            overall = nil
            maxDrawdown = nil
            rangeLabel = nil
            return
        }
        isBuildingSeries = true
        let equityIn = charts.equityCurve ?? []
        let dailyIn = charts.daily ?? []
        let ddIn = charts.drawdown ?? []
        let sportIn = charts.bySport
        let overallIn = charts.overall
        let key = rangeKey
        let daysLimit = rangeOptions.first(where: { $0.key == key })?.days
        let defaultRangeLabel = charts.rangeLabel ?? "All time (era)"

        let built = await Task.detached(priority: .userInitiated) {
            let eq = ChartDataBuilder.equity(equityIn)
            let dy = ChartDataBuilder.daily(dailyIn)
            let dd = ChartDataBuilder.drawdown(ddIn)
            let sp = ChartDataBuilder.sports(sportIn)
            // Cutoff in UTC to match ChartDay keys (yyyy-MM-dd at UTC midnight).
            var utcCal = Calendar(identifier: .gregorian)
            utcCal.timeZone = TimeZone(secondsFromGMT: 0)!
            let cutoff: Date? = {
                guard let d = daysLimit else { return nil }
                let today = utcCal.startOfDay(for: Date())
                return utcCal.date(byAdding: .day, value: -d + 1, to: today)
            }()
            func keep(_ date: Date) -> Bool {
                guard let cutoff else { return true }
                return date >= cutoff
            }
            let eqF = eq.filter { keep($0.day.date) }
            let dyF = dy.filter { keep($0.day.date) }
            let ddF = dd.filter { keep($0.day.date) }
            let maxDD = ddF.map(\.drawdown).max()
            let label: String = {
                switch key {
                case "1w": return "Last 7 days"
                case "1m": return "Last 30 days"
                default: return defaultRangeLabel
                }
            }()
            // Calendar always uses full era daily so month nav works across history.
            return (eqF, dyF, dy, ddF, sp, maxDD, label)
        }.value

        equityPoints = built.0
        dailyPoints = built.1
        calendarPoints = built.2
        drawdownPoints = built.3
        sportPoints = built.4
        overall = overallIn
        maxDrawdown = built.5
        rangeLabel = built.6
        isBuildingSeries = false
    }

    // MARK: - Expanded content

    @ViewBuilder
    private func expandedBody(_ kind: ExpandableChartKind) -> some View {
        switch kind {
        case .equity:
            EquityChartView(
                points: equityPoints,
                selectedRawDay: $equitySelection,
                height: ChartExpandedMetrics.chartHeight
            )
        case .daily:
            DailyPLChartView(
                points: dailyPoints,
                selectedRawDay: $dailySelection,
                height: ChartExpandedMetrics.chartHeight
            )
        case .calendar:
            PerformanceCalendarView(
                points: calendarPoints,
                selectedRawDay: $dailySelection
            )
            .padding(.horizontal, DeskSpacing.s2)
        case .drawdown:
            DrawdownChartView(
                points: drawdownPoints,
                selectedRawDay: $drawdownSelection,
                height: ChartExpandedMetrics.chartHeight
            )
        case .sport:
            SportChartView(
                sports: sportPoints,
                selectedSport: $sportSelection,
                chartHeight: ChartExpandedMetrics.chartHeight
            )
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
        _ kind: ExpandableChartKind,
        @ViewBuilder content: @escaping () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: DeskSpacing.s2) {
            HStack {
                Text(kind.title.uppercased())
                    .font(DeskTypography.sectionLabel)
                    .foregroundStyle(DeskTheme.textDim)
                    .tracking(0.6)
                    .accessibilityAddTraits(.isHeader)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .contentShape(Rectangle())
                    .onTapGesture { clearAllSelections() }
                Button {
                    expanded = kind
                } label: {
                    Label("Expand", systemImage: "arrow.up.left.and.arrow.down.right")
                        .labelStyle(.iconOnly)
                        .font(.body.weight(.medium))
                        .foregroundStyle(DeskTheme.accent)
                        .frame(minWidth: 44, minHeight: 44)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Expand \(kind.title)")
                .accessibilityHint("Opens a larger full-screen chart")
                .accessibilityIdentifier("charts.expand.\(kind.rawValue)")
            }
            // Chart card: drag still selects; parent VStack tap clears only when
            // the hit is outside interactive chart content (headers/callout handle dismiss).
            DeskCard(content: content)
        }
    }

    private var emptyState: some View {
        DeskCard {
            DeskContentUnavailable(
                title: "No chart data",
                systemImage: "chart.xyaxis.line",
                description: "Pull to refresh after syncing settled history from the PC.",
                accessibilityLabelText: "No chart data. Pull to refresh after syncing settled history from the PC."
            )
        }
    }
}
