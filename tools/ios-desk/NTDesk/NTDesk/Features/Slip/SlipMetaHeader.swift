import SwiftUI

struct SlipMetaHeader: View {
    let document: PlaceTheseDocument
    var mtime: String?

    var body: some View {
        VStack(alignment: .leading, spacing: DeskSpacing.s2) {
            HStack(alignment: .firstTextBaseline) {
                Text(document.title)
                    .font(DeskTypography.sectionTitle)
                    .foregroundStyle(DeskTheme.text)
                    .accessibilityAddTraits(.isHeader)
                Spacer(minLength: DeskSpacing.s2)
                if let mtime, !mtime.isEmpty {
                    Text(mtime)
                        .font(DeskTypography.caption)
                        .foregroundStyle(DeskTheme.textDim)
                        .lineLimit(1)
                }
            }
            if let phaseId = document.phaseId {
                Text(phaseMetaLine(phaseId: phaseId))
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
            } else if let phaseLine = document.phaseLine, !phaseLine.isEmpty {
                Text(PlaceTheseParser.normalizeCell(phaseLine).replacingOccurrences(of: "**", with: ""))
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
            }
        }
    }

    private func phaseMetaLine(phaseId: String) -> String {
        var parts: [String] = ["Phase \(phaseId)"]
        if let rem = document.remainingRiskNok, let cap = document.dailyCapNok {
            parts.append(String(format: "Remaining %.2f / %.2f", rem, cap))
        } else if let rem = document.remainingRiskNok {
            parts.append(String(format: "Remaining %.2f", rem))
        }
        if let eq = document.equityNok {
            parts.append(String(format: "Equity %.2f", eq))
        }
        return parts.joined(separator: " · ")
    }
}
