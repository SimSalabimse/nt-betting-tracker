import SwiftUI

/// KPI tile with optional left accent rail — maps desktop `metric()`.
struct MetricCard: View {
    let label: String
    let value: String
    var subtitle: String = ""
    var valueColor: Color = DeskTheme.text
    /// When nil, defaults to accent (desktop: accent when value color is TEXT).
    var railColor: Color? = nil

    private var effectiveRail: Color {
        railColor ?? DeskTheme.accent
    }

    var body: some View {
        HStack(spacing: 0) {
            RoundedRectangle(cornerRadius: 2)
                .fill(effectiveRail)
                .frame(width: 3)
            VStack(alignment: .leading, spacing: DeskSpacing.s1) {
                Text(label.uppercased())
                    .font(DeskTypography.kpiLabel)
                    .foregroundStyle(DeskTheme.textDim)
                    .accessibilityAddTraits(.isHeader)
                Text(value)
                    .font(DeskTypography.kpiValue)
                    .foregroundStyle(valueColor)
                    .minimumScaleFactor(0.7)
                    .lineLimit(1)
                if !subtitle.isEmpty {
                    Text(subtitle)
                        .font(DeskTypography.caption)
                        .foregroundStyle(DeskTheme.textMuted)
                        .lineLimit(2)
                }
            }
            .padding(.leading, DeskSpacing.s3)
            .padding(.vertical, DeskSpacing.s2)
            Spacer(minLength: 0)
        }
        .padding(.trailing, DeskSpacing.s3)
        .padding(.vertical, DeskSpacing.s2)
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
        .accessibilityLabel("\(label), \(value)\(subtitle.isEmpty ? "" : ", \(subtitle)")")
    }
}
