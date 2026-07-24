import SwiftUI

struct DeskView: View {
    @EnvironmentObject private var sync: SyncService

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
                            kpi("Equity", nok(s.equityNok))
                            kpi("Liquid", nok(s.liquidNok))
                            kpi("Open risk", nok(s.pendingAtRiskNok))
                            kpi("Remaining", nok(s.remainingRiskNok))
                            kpi("Phase", "\(s.phaseId ?? "—") \(s.phaseLabel ?? "")")
                            kpi("Today P/L", nok(s.todayRealizedPlNok))
                        }
                        if let o = s.charts?.overall {
                            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                                kpi("ROI", pct(o.roi))
                                kpi("Win rate", pct(o.winrate))
                                kpi("Settled", intStr(o.nSettled))
                                kpi("Max DD", nok(s.charts?.maxDrawdown))
                            }
                        }
                        Text("Generated \(s.generatedAt ?? "—")")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    } else {
                        ContentUnavailableView(
                            "No desk data",
                            systemImage: "wifi.slash",
                            description: Text("Set base URL in Settings and pull to refresh while the PC is reachable.")
                        )
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

    private func kpi(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title.uppercased())
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.title3.weight(.semibold))
                .foregroundStyle(.primary)
                .lineLimit(2)
                .minimumScaleFactor(0.7)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 12).fill(Color(red: 0.10, green: 0.11, blue: 0.14)))
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

struct FreshnessBanner: View {
    @EnvironmentObject private var sync: SyncService

    var body: some View {
        switch sync.freshness {
        case .fresh:
            EmptyView()
        case .stale:
            label("Stale — last sync \(sync.lastSuccessSyncAt ?? "—")", .yellow)
        case .staleMismatch:
            label("Cache is from a different base URL — not live", .orange)
        case .liveNotPersisted:
            label("Live but not saved on device", .orange)
        case .empty:
            label(sync.lastError ?? "No cache yet", .secondary)
        }
    }

    private func label(_ t: String, _ c: Color) -> some View {
        Text(t)
            .font(.footnote)
            .foregroundStyle(c)
            .padding(8)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 8).stroke(c.opacity(0.5)))
    }
}
