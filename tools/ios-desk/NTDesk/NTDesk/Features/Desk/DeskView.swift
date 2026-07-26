import SwiftUI

struct DeskView: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var sparkPoints: [EquityChartPoint] = []

    private var gridColumns: [GridItem] {
        if dynamicTypeSize.isAccessibilitySize {
            return [GridItem(.flexible())]
        }
        return [GridItem(.flexible()), GridItem(.flexible())]
    }

    private var relativeTimelinePeriod: TimeInterval {
        reduceMotion ? 300 : 60
    }

    private var showStickyRiskBanner: Bool {
        guard let s = sync.snapshot else { return false }
        return s.freeze == true || s.stopped == true || s.canBet == false
    }

    var body: some View {
        DeskScreenChrome(title: "NT Desk") {
            ScrollView {
                VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                    FreshnessBanner()
                    if let s = sync.snapshot {
                        // 1) Morning summary · 2) Risk Gate (Secure Variant A lives on Charts)
                        MorningSummaryCard(snapshot: s, equityPoints: sparkPoints)
                        riskGateSection(s)

                        if sparkPoints.count >= 2 {
                            DeskCard {
                                VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                                    Text("EQUITY TREND")
                                        .font(DeskTypography.sectionLabel)
                                        .foregroundStyle(DeskTheme.textDim)
                                        .tracking(0.6)
                                    EquitySparklineView(points: sparkPoints)
                                }
                            }
                        }

                        LazyVGrid(columns: gridColumns, spacing: DeskSpacing.s2) {
                            MetricCard(label: "Equity", value: DeskFormatters.nok(s.equityNok))
                            MetricCard(label: "Liquid", value: DeskFormatters.nok(s.liquidNok))
                            MetricCard(label: "Open risk", value: DeskFormatters.nok(s.pendingAtRiskNok))
                            MetricCard(label: "Remaining", value: DeskFormatters.nok(s.remainingRiskNok))
                            MetricCard(
                                label: "Phase",
                                value: s.phaseId ?? "—",
                                subtitle: s.phaseLabel ?? ""
                            )
                            MetricCard(
                                label: "Today P/L",
                                value: DeskFormatters.nok(s.todayRealizedPlNok, signed: true),
                                valueColor: DeskTheme.pl(s.todayRealizedPlNok),
                                railColor: DeskTheme.pl(s.todayRealizedPlNok)
                            )
                        }

                        if let o = s.charts?.overall {
                            LazyVGrid(columns: gridColumns, spacing: DeskSpacing.s2) {
                                MetricCard(
                                    label: "ROI",
                                    value: DeskFormatters.pct(o.roi, signed: true),
                                    valueColor: DeskTheme.pl(o.roi),
                                    railColor: DeskTheme.pl(o.roi)
                                )
                                MetricCard(label: "Win rate", value: DeskFormatters.pct(o.winrate))
                                MetricCard(label: "Settled", value: DeskFormatters.int(o.nSettled))
                                MetricCard(
                                    label: "Max DD",
                                    value: DeskFormatters.nok(s.charts?.maxDrawdown),
                                    valueColor: DeskTheme.loss,
                                    railColor: DeskTheme.loss
                                )
                            }
                        }

                        TimelineView(.periodic(from: .now, by: relativeTimelinePeriod)) { context in
                            let relative = DeskFormatters.relativeTime(
                                s.generatedAt,
                                relativeTo: context.date
                            )
                            Text("Generated \(relative)")
                                .font(DeskTypography.caption)
                                .foregroundStyle(DeskTheme.textDim)
                                .padding(.top, DeskSpacing.s1)
                        }
                    } else {
                        EmptyDeskView()
                            .frame(maxWidth: .infinity)
                            .padding(.top, DeskSpacing.s6)
                    }
                }
                .padding(DeskSpacing.contentPad)
            }
            .background(DeskTheme.bg.ignoresSafeArea())
            .refreshable { await sync.sync(waitForConnectivity: true) }
            .safeAreaInset(edge: .top, spacing: 0) {
                if showStickyRiskBanner, let s = sync.snapshot {
                    stickyRiskBanner(s)
                }
            }
            .task(id: sync.snapshot?.generatedAt) {
                await rebuildSparkline()
            }
        }
    }

    private func rebuildSparkline() async {
        let raw = sync.snapshot?.charts?.equityCurve ?? []
        let points = await Task.detached(priority: .utility) {
            // Last ~21 points for a compact sparkline
            let all = ChartDataBuilder.equity(raw)
            return Array(all.suffix(21))
        }.value
        sparkPoints = points
    }

    // MARK: - Sticky freeze banner

    @ViewBuilder
    private func stickyRiskBanner(_ s: DeskSnapshot) -> some View {
        let status = RiskGateStatus.resolve(
            stopped: s.stopped,
            freeze: s.freeze,
            canBet: s.canBet
        )
        HStack(spacing: DeskSpacing.s2) {
            Image(systemName: "exclamationmark.shield.fill")
                .foregroundStyle(status.color)
            VStack(alignment: .leading, spacing: 2) {
                Text(status.title.uppercased())
                    .font(DeskTypography.kpiLabel)
                    .foregroundStyle(status.color)
                Text(stickyRiskSubtitle(s))
                    .font(DeskTypography.caption)
                    .foregroundStyle(DeskTheme.text)
                    .lineLimit(2)
            }
            Spacer(minLength: 0)
            StatusPill(status: status)
        }
        .padding(.horizontal, DeskSpacing.contentPad)
        .padding(.vertical, DeskSpacing.s3)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(status.color.opacity(0.18))
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(status.color.opacity(0.55))
                .frame(height: 1)
        }
        .accessibilityElement(children: .combine)
    }

    /// Human subtitle for the sticky banner — no raw engine flags (`can_bet=`).
    private func stickyRiskSubtitle(_ s: DeskSnapshot) -> String {
        var parts: [String] = []
        if let mode = s.sizeMode?.trimmingCharacters(in: .whitespacesAndNewlines), !mode.isEmpty {
            parts.append(mode)
        }
        if let rem = s.remainingRiskNok {
            parts.append("\(DeskFormatters.nok(rem)) left today")
        }
        // Prefer the first engine reason when present (already human text from PC).
        if let reason = s.riskReasons?.first(where: { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) {
            let trimmed = reason.trimmingCharacters(in: .whitespacesAndNewlines)
            // Avoid duplicating size_mode if it's the only content.
            if parts.isEmpty || !trimmed.localizedCaseInsensitiveContains(parts[0]) {
                parts.append(trimmed)
            }
        }
        if parts.isEmpty {
            switch RiskGateStatus.resolve(stopped: s.stopped, freeze: s.freeze, canBet: s.canBet) {
            case .stop: return "Hard stop — no new stakes"
            case .freeze: return "Risk freeze — no new stakes"
            case .riskFull: return "Daily risk used up — no new stakes"
            case .canBet: return "OK to place"
            }
        }
        return parts.joined(separator: " · ")
    }

    // MARK: - Risk gate card

    @ViewBuilder
    private func riskGateSection(_ s: DeskSnapshot) -> some View {
        let status = RiskGateStatus.resolve(
            stopped: s.stopped,
            freeze: s.freeze,
            canBet: s.canBet
        )
        DeskCard(accent: status.color) {
            VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                HStack(alignment: .center, spacing: DeskSpacing.s2) {
                    Text("RISK GATE")
                        .font(DeskTypography.sectionLabel)
                        .foregroundStyle(DeskTheme.textDim)
                        .tracking(0.6)
                    Spacer(minLength: DeskSpacing.s2)
                    StatusPill(status: status)
                }

                if let mode = s.sizeMode, !mode.isEmpty {
                    Text(mode)
                        .font(DeskTypography.caption)
                        .foregroundStyle(DeskTheme.textMuted)
                }

                if let reasons = s.riskReasons, !reasons.isEmpty {
                    VStack(alignment: .leading, spacing: DeskSpacing.s1) {
                        ForEach(reasons, id: \.self) { reason in
                            HStack(alignment: .top, spacing: DeskSpacing.s2) {
                                Text("·")
                                    .foregroundStyle(DeskTheme.textDim)
                                    .accessibilityHidden(true)
                                Text(reason)
                                    .font(DeskTypography.caption)
                                    .foregroundStyle(DeskTheme.textMuted)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }

                RiskGaugeCard(
                    dailyRiskCapNok: s.dailyRiskCapNok,
                    remainingRiskNok: s.remainingRiskNok,
                    canBet: s.canBet,
                    todayRealizedPlNok: s.todayRealizedPlNok
                )
            }
        }
    }
}
