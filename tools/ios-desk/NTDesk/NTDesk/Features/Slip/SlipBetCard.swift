import SwiftUI

struct SlipBetCard: View {
    let bet: PlaceTheseBet

    var body: some View {
        DeskCard(accent: DeskTheme.accent) {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                HStack(alignment: .firstTextBaseline, spacing: DeskSpacing.s2) {
                    if let index = bet.index {
                        Text("#\(index)")
                            .font(DeskTypography.sectionLabel)
                            .foregroundStyle(DeskTheme.accent)
                    }
                    Text(bet.match)
                        .font(DeskTypography.sectionTitle)
                        .foregroundStyle(DeskTheme.text)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Text(bet.selection)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(DeskTheme.textMuted)
                HStack(spacing: DeskSpacing.s3) {
                    metric("Odds", formatOdds(bet.decimalOdds))
                    metric("Stake", DeskFormatters.nok(bet.stakeNok))
                    metric("EV", formatEV(bet.ev))
                    if let grade = bet.grade, !grade.isEmpty { metric("Grade", grade) }
                    if let band = bet.band, !band.isEmpty { metric("Band", band) }
                }
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilitySummary)
    }

    private func metric(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(DeskTypography.kpiLabel)
                .foregroundStyle(DeskTheme.textDim)
            Text(value)
                .font(DeskTypography.monoFootnote)
                .foregroundStyle(DeskTheme.text)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func formatOdds(_ value: Double?) -> String {
        guard let value else { return "—" }
        return String(format: "%.2f", value)
    }

    private func formatEV(_ value: Double?) -> String {
        guard let value else { return "—" }
        return String(format: "%.3f", value)
    }

    private var accessibilitySummary: String {
        var parts: [String] = []
        if let index = bet.index { parts.append("Bet \(index)") }
        parts.append(bet.match)
        parts.append(bet.selection)
        if let o = bet.decimalOdds { parts.append("Odds \(formatOdds(o))") }
        if let s = bet.stakeNok { parts.append("Stake \(DeskFormatters.nok(s))") }
        if let e = bet.ev { parts.append("EV \(formatEV(e))") }
        if let g = bet.grade { parts.append("Grade \(g)") }
        if let b = bet.band { parts.append("Band \(b)") }
        return parts.joined(separator: ", ")
    }
}

struct SlipEmptySuccessCard: View {
    var body: some View {
        DeskCard(accent: DeskTheme.profit) {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                Label("No bets to place", systemImage: "checkmark.circle.fill")
                    .font(DeskTypography.sectionTitle)
                    .foregroundStyle(DeskTheme.profit)
                Text("Empty slip is success after research. Nothing to place on the PC desk.")
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("No bets to place. Empty slip is success after research.")
    }
}
