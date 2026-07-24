import Charts
import SwiftUI

/// Simple charts of the most important Book-aligned stats from `/api/desk` → `charts`.
struct ChartsView: View {
    @EnvironmentObject private var sync: SyncService

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    FreshnessBanner()
                    if let charts = sync.snapshot?.charts {
                        if let o = charts.overall {
                            HStack {
                                stat("ROI", String(format: "%.1f%%", (o.roi ?? 0) * 100))
                                stat("WR", String(format: "%.0f%%", (o.winrate ?? 0) * 100))
                                stat("P/L", String(format: "%.0f", o.pl ?? 0))
                                stat("DD", String(format: "%.0f", charts.maxDrawdown ?? 0))
                            }
                        }

                        section("Equity") {
                            let pts = charts.equityCurve ?? []
                            if pts.isEmpty {
                                Text("No settled history").foregroundStyle(.secondary)
                            } else {
                                Chart(pts) { p in
                                    LineMark(
                                        x: .value("Date", p.date ?? ""),
                                        y: .value("Equity", p.equity ?? 0)
                                    )
                                    .foregroundStyle(Color.accentColor)
                                    AreaMark(
                                        x: .value("Date", p.date ?? ""),
                                        y: .value("Equity", p.equity ?? 0)
                                    )
                                    .foregroundStyle(Color.accentColor.opacity(0.15))
                                }
                                .frame(height: 180)
                                .chartXAxis {
                                    AxisMarks(values: .automatic(desiredCount: 4))
                                }
                            }
                        }

                        section("Daily P/L") {
                            let pts = charts.daily ?? []
                            if pts.isEmpty {
                                Text("No daily data").foregroundStyle(.secondary)
                            } else {
                                Chart(pts) { p in
                                    BarMark(
                                        x: .value("Date", p.date ?? ""),
                                        y: .value("P/L", p.pl ?? 0)
                                    )
                                    .foregroundStyle((p.pl ?? 0) >= 0 ? Color.green : Color.red)
                                }
                                .frame(height: 160)
                                .chartXAxis {
                                    AxisMarks(values: .automatic(desiredCount: 4))
                                }
                            }
                        }

                        section("Drawdown") {
                            let pts = charts.drawdown ?? []
                            if pts.isEmpty {
                                Text("No drawdown series").foregroundStyle(.secondary)
                            } else {
                                Chart(pts) { p in
                                    LineMark(
                                        x: .value("Date", p.date ?? ""),
                                        y: .value("DD", p.drawdown ?? 0)
                                    )
                                    .foregroundStyle(Color.orange)
                                }
                                .frame(height: 140)
                            }
                        }

                        section("By sport (P/L)") {
                            let sports = (charts.bySport ?? [:])
                                .map { (name: $0.key, pl: $0.value.pl ?? 0, roi: $0.value.roi ?? 0, n: $0.value.n ?? 0) }
                                .sorted { $0.pl > $1.pl }
                            if sports.isEmpty {
                                Text("No sport stats").foregroundStyle(.secondary)
                            } else {
                                Chart(sports, id: \.name) { s in
                                    BarMark(
                                        x: .value("P/L", s.pl),
                                        y: .value("Sport", s.name)
                                    )
                                    .foregroundStyle(s.pl >= 0 ? Color.green : Color.red)
                                }
                                .frame(height: CGFloat(max(120, sports.count * 28)))
                                ForEach(sports, id: \.name) { s in
                                    HStack {
                                        Text(s.name)
                                        Spacer()
                                        Text("n=\(Int(s.n))")
                                        Text(String(format: "ROI %.0f%%", s.roi * 100))
                                            .foregroundStyle(.secondary)
                                    }
                                    .font(.caption)
                                }
                            }
                        }

                        Text(charts.rangeLabel ?? "All time")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    } else {
                        ContentUnavailableView("No chart data", systemImage: "chart.bar")
                    }
                }
                .padding()
            }
            .background(Color(red: 0.06, green: 0.07, blue: 0.08))
            .navigationTitle("Charts")
            .refreshable { await sync.sync() }
        }
    }

    private func section<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
                .foregroundStyle(Color.accentColor)
            content()
                .padding(12)
                .background(RoundedRectangle(cornerRadius: 12).fill(Color(red: 0.10, green: 0.11, blue: 0.14)))
        }
    }

    private func stat(_ k: String, _ v: String) -> some View {
        VStack(spacing: 2) {
            Text(k).font(.caption2).foregroundStyle(.secondary)
            Text(v).font(.subheadline.weight(.semibold))
        }
        .frame(maxWidth: .infinity)
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 10).fill(Color(red: 0.10, green: 0.11, blue: 0.14)))
    }
}
