import SwiftUI

/// Multi-field selection callout above a chart (parity with prior detail card).
/// Color is not the sole signal — signed amounts appear as text in `lines`.
struct ChartSelectionCallout: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let title: String
    let lines: [String]
    var isActive: Bool = false
    var idleHint: String = "Drag on the chart to inspect a point"

    var body: some View {
        VStack(alignment: .leading, spacing: DeskSpacing.s1) {
            Text(title.uppercased())
                .font(DeskTypography.kpiLabel)
                .foregroundStyle(isActive ? DeskTheme.accent : DeskTheme.textDim)
                .tracking(0.4)
            if lines.isEmpty {
                Text(isActive ? "No data for selection" : idleHint)
                    .font(DeskTypography.caption)
                    .foregroundStyle(DeskTheme.textMuted)
            } else {
                ForEach(Array(lines.enumerated()), id: \.offset) { _, line in
                    Text(line)
                        .font(DeskTypography.monoFootnote)
                        .foregroundStyle(DeskTheme.text)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(DeskSpacing.s3)
        .background(
            RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                .fill(isActive ? DeskTheme.surface : DeskTheme.surfaceElev.opacity(0.85))
                .overlay(
                    RoundedRectangle(cornerRadius: DeskSpacing.radiusSM)
                        .stroke(isActive ? DeskTheme.accent.opacity(0.45) : DeskTheme.borderSoft, lineWidth: 1)
                )
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel(([title] + lines).joined(separator: ", "))
        .animation(reduceMotion ? nil : .easeInOut(duration: 0.12), value: isActive)
    }
}
