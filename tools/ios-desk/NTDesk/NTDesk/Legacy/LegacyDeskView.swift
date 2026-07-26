import SwiftUI

struct LegacyDeskView: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @Binding var selectedTab: LegacyDeskTab

    private var gridColumns: [GridItem] {
        if dynamicTypeSize.isAccessibilitySize {
            return [GridItem(.flexible())]
        }
        return [GridItem(.flexible()), GridItem(.flexible())]
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                    FreshnessBanner()
                    if let s = sync.snapshot {
                        riskGateSection(s)

                        LazyVGrid(columns: gridColumns, spacing: DeskSpacing.s2) {
                            MetricCard(
                                label: "Equity",
                                value: DeskFormatters.nok(s.equityNok)
                            )
                            MetricCard(
                                label: "Liquid",
                                value: DeskFormatters.nok(s.liquidNok)
                            )
                            MetricCard(
                                label: "Open risk",
                                value: DeskFormatters.nok(s.pendingAtRiskNok)
                            )
                            MetricCard(
                                label: "Remaining",
                                value: DeskFormatters.nok(s.remainingRiskNok)
                            )
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
                                MetricCard(
                                    label: "Win rate",
                                    value: DeskFormatters.pct(o.winrate)
                                )
                                MetricCard(
                                    label: "Settled",
                                    value: DeskFormatters.int(o.nSettled)
                                )
                                MetricCard(
                                    label: "Max DD",
                                    value: DeskFormatters.nok(s.charts?.maxDrawdown),
                                    valueColor: DeskTheme.loss,
                                    railColor: DeskTheme.loss
                                )
                            }
                        }

                        TimelineView(.periodic(from: .now, by: 60)) { context in
                            let relative = DeskFormatters.relativeTime(
                                s.generatedAt,
                                relativeTo: context.date
                            )
                            Text("Generated \(relative)")
                                .font(DeskTypography.caption)
                                .foregroundStyle(DeskTheme.textDim)
                                .padding(.top, DeskSpacing.s1)
                                .accessibilityLabel("Snapshot generated \(relative)")
                        }
                    } else {
                        EmptyDeskView {
                            selectedTab = .settings
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, DeskSpacing.s6)
                    }
                }
                .padding(DeskSpacing.contentPad)
            }
            .background(DeskTheme.bg.ignoresSafeArea())
            .navigationTitle("NT Desk")
            .toolbarBackground(DeskTheme.surface, for: .navigationBar)
            .refreshable { await sync.sync() }
            .toolbar {
                if sync.isSyncing {
                    ProgressView()
                        .tint(DeskTheme.accent)
                        .accessibilityLabel("Syncing desk snapshot")
                }
            }
        }
    }

    // MARK: - Risk gate

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
                        .accessibilityAddTraits(.isHeader)
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
                            .accessibilityElement(children: .combine)
                            .accessibilityLabel(reason)
                        }
                    }
                    .accessibilityElement(children: .contain)
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
