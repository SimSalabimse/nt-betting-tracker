import SwiftUI

struct DeskView: View {
    @EnvironmentObject private var sync: SyncService
    @Binding var selectedTab: DeskTab

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    FreshnessBanner()
                    if let s = sync.snapshot {
                        if s.freeze == true || s.stopped == true || s.canBet == false {
                            banner(
                                "Risk gate — can_bet=\(s.canBet.map(String.init) ?? "?") · mode=\(s.sizeMode ?? "—")",
                                color: .orange
                            )
                        }
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                            MetricCard(label: "Equity", value: nok(s.equityNok))
                            MetricCard(label: "Liquid", value: nok(s.liquidNok))
                            MetricCard(label: "Open risk", value: nok(s.pendingAtRiskNok))
                            MetricCard(label: "Remaining", value: nok(s.remainingRiskNok))
                            MetricCard(label: "Phase", value: "\(s.phaseId ?? "—") \(s.phaseLabel ?? "")")
                            MetricCard(label: "Today P/L", value: nok(s.todayRealizedPlNok))
                        }
                        if let o = s.charts?.overall {
                            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                                MetricCard(label: "ROI", value: pct(o.roi))
                                MetricCard(label: "Win rate", value: pct(o.winrate))
                                MetricCard(label: "Settled", value: intStr(o.nSettled))
                                MetricCard(label: "Max DD", value: nok(s.charts?.maxDrawdown))
                            }
                        }
                        Text("Generated \(s.generatedAt ?? "—")")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    } else {
                        EmptyDeskView {
                            selectedTab = .settings
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, DeskSpacing.s6)
                    }
                }
                .padding()
            }
            .background(Color(red: 0.06, green: 0.07, blue: 0.08))
            .navigationTitle("NT Desk")
            .refreshable { await sync.sync() }
            .toolbar {
                if sync.isSyncing {
                    ProgressView()
                }
            }
        }
    }

    private func banner(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.footnote)
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 10).fill(color.opacity(0.2)))
    }

    private func nok(_ v: Double?) -> String {
        guard let v else { return "—" }
        return String(format: "%.2f NOK", v)
    }

    private func pct(_ v: Double?) -> String {
        guard let v else { return "—" }
        return String(format: "%.1f%%", v * 100)
    }

    private func intStr(_ v: Double?) -> String {
        guard let v else { return "—" }
        return String(Int(v))
    }
}
