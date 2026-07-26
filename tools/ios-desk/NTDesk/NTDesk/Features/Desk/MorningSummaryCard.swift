import SwiftUI

/// Quick morning glance: equity change, open risk, can-bet, pending count.
struct MorningSummaryCard: View {
    let snapshot: DeskSnapshot
    let equityPoints: [EquityChartPoint]

    private var equityDelta: Double? {
        guard equityPoints.count >= 2,
              let first = equityPoints.first?.equity,
              let last = equityPoints.last?.equity
        else { return nil }
        // Prefer today P/L when present; else window from sparkline.
        if let today = snapshot.todayRealizedPlNok { return today }
        return last - first
    }

    var body: some View {
        DeskCard {
            VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                Text("MORNING SNAPSHOT")
                    .font(DeskTypography.sectionLabel)
                    .foregroundStyle(DeskTheme.textDim)
                    .tracking(0.6)
                    .accessibilityAddTraits(.isHeader)

                HStack(spacing: DeskSpacing.s3) {
                    summaryCell(
                        "Today P/L",
                        DeskFormatters.nok(equityDelta ?? snapshot.todayRealizedPlNok, signed: true),
                        color: DeskTheme.pl(equityDelta ?? snapshot.todayRealizedPlNok)
                    )
                    summaryCell(
                        "Open risk",
                        DeskFormatters.nok(snapshot.pendingAtRiskNok),
                        color: DeskTheme.text
                    )
                    summaryCell(
                        "Pending",
                        DeskFormatters.int(Double(snapshot.pendingCount ?? snapshot.pendingBets?.count ?? 0)),
                        color: DeskTheme.text
                    )
                    let can = snapshot.canBet == true
                    summaryCell(
                        "Can bet",
                        can ? "Yes" : "No",
                        color: can ? DeskTheme.profit : DeskTheme.loss
                    )
                }
            }
        }
        .accessibilityElement(children: .combine)
    }

    private func summaryCell(_ label: String, _ value: String, color: Color) -> some View {
        VStack(spacing: 4) {
            Text(label.uppercased())
                .font(DeskTypography.kpiLabel)
                .foregroundStyle(DeskTheme.textDim)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(value)
                .font(.system(.subheadline, design: .monospaced).weight(.semibold))
                .foregroundStyle(color)
                .lineLimit(1)
                .minimumScaleFactor(0.6)
        }
        .frame(maxWidth: .infinity)
    }
}
