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

    private var equityPoints: [EquityChartPoint] {
        ChartDataBuilder.equity(sync.snapshot?.charts?.equityCurve ?? [])
    }

    private var dailyPoints: [DailyChartPoint] {
        ChartDataBuilder.daily(sync.snapshot?.charts?.daily ?? [])
    }

    private var drawdownPoints: [DrawdownChartPoint] {
        ChartDataBuilder.drawdown(sync.snapshot?.charts?.drawdown ?? [])
    }

    private var sportPoints: [SportChartPoint] {
        ChartDataBuilder.sports(sync.snapshot?.charts?.bySport)
    }

    var body: some View {
        DeskScreenChrome(title: "Charts") {
            ScrollView {
                VStack(alignment: .leading, spacing: DeskSpacing.s5) {
                    FreshnessBanner()
                    if let charts = sync.snapshot?.charts {
                        if let o = charts.overall {
                            summaryStrip(overall: o, maxDrawdown: charts.maxDrawdown)
                        }

                        chartSection(.equity) {
                            EquityChartView(
                                points: equityPoints,
                                selectedRawDay: $equitySelection
                            )
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
                            Text(charts.rangeLabel ?? "All time")
                                .font(DeskTypography.caption)
                                .foregroundStyle(DeskTheme.textDim)
                            Spacer()
                            Text("Drag chart to inspect · tap expand")
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
            .refreshable { await sync.sync() }
            .onChange(of: sync.snapshot?.generatedAt) { _, _ in
                // Clear stale scrubbers when desk payload refreshes
                equitySelection = nil
                dailySelection = nil
                drawdownSelection = nil
                sportSelection = nil
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
                Spacer()
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
            DeskCard(content: content)
        }
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
}
