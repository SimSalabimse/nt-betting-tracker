import SwiftUI

/// Compact pending-bet card used in `PendingListView`.
struct PendingBetRow: View {
    let bet: PendingBet

    private var match: String { bet.match ?? "—" }
    private var selection: String { bet.selection ?? "—" }
    /// Visual odds (`@ 1.87`); a11y uses bare decimal to avoid “odds @ …”.
    private var oddsLabel: String {
        guard let o = bet.decimalOdds else { return "—" }
        return String(format: "@ %.2f", o)
    }
    private var oddsAccessibility: String {
        guard let o = bet.decimalOdds else { return "—" }
        return String(format: "%.2f", o)
    }
    private var stakeLabel: String {
        DeskFormatters.nok(bet.stakeNok)
    }

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            RoundedRectangle(cornerRadius: 2)
                .fill(DeskTheme.result(bet.result))
                .frame(width: 3)

            VStack(alignment: .leading, spacing: DeskSpacing.s1) {
                Text(match)
                    .font(.headline)
                    .foregroundStyle(DeskTheme.text)
                    .lineLimit(2)

                Text(selection)
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
                    .lineLimit(2)

                HStack(spacing: DeskSpacing.s2) {
                    if let sport = bet.sport, !sport.isEmpty {
                        Text(sport)
                    }
                    if let date = bet.date, !date.isEmpty {
                        Text(date)
                    }
                    Spacer(minLength: 0)
                    Text(oddsLabel)
                    Text(stakeLabel)
                }
                .font(.system(.caption, design: .monospaced))
                .foregroundStyle(DeskTheme.textDim)
            }
            .padding(.leading, DeskSpacing.s3)
            .padding(.vertical, DeskSpacing.s2)
            .padding(.trailing, DeskSpacing.s3)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: DeskSpacing.radius)
                .fill(DeskTheme.surfaceElev)
                .overlay(
                    RoundedRectangle(cornerRadius: DeskSpacing.radius)
                        .stroke(DeskTheme.borderSoft, lineWidth: 1)
                )
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel(rowAccessibilityLabel)
    }

    private var rowAccessibilityLabel: String {
        var parts = [match, selection, "odds \(oddsAccessibility)", "stake \(stakeLabel)"]
        if let sport = bet.sport, !sport.isEmpty {
            parts.insert(sport, at: 0)
        }
        if let date = bet.date, !date.isEmpty {
            parts.insert(date, at: 0)
        }
        if let result = bet.result, !result.isEmpty {
            parts.append("result \(result)")
        }
        return parts.joined(separator: ", ")
    }
}
