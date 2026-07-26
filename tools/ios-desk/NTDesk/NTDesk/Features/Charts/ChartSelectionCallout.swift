import SwiftUI

/// Multi-field selection callout above a chart (parity with prior detail card).
/// Color is not the sole signal — signed amounts appear as text in `lines`.
/// When active, tap the callout to dismiss / minimize details.
struct ChartSelectionCallout: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let title: String
    let lines: [String]
    var isActive: Bool = false
    var idleHint: String = "Drag on the chart to inspect a point"
    /// Called when the user taps an active callout (dismiss selection).
    var onDismiss: (() -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: DeskSpacing.s1) {
            HStack(alignment: .firstTextBaseline) {
                Text(title.uppercased())
                    .font(DeskTypography.kpiLabel)
                    .foregroundStyle(isActive ? DeskTheme.accent : DeskTheme.textDim)
                    .tracking(0.4)
                Spacer(minLength: 8)
                if isActive {
                    Text("Tap to close")
                        .font(DeskTypography.caption)
                        .foregroundStyle(DeskTheme.textDim)
                }
            }
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
        .contentShape(Rectangle())
        .onTapGesture {
            guard isActive else { return }
            onDismiss?()
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(([title] + lines).joined(separator: ", "))
        .accessibilityHint(isActive ? "Double tap to close details" : "")
        .accessibilityAddTraits(isActive ? .isButton : [])
        .animation(reduceMotion ? nil : .easeInOut(duration: 0.12), value: isActive)
    }
}
