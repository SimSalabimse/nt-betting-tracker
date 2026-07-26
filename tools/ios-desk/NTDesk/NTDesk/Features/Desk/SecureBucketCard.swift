import SwiftUI

/// Secure Variant A — locked capital vs riskable working equity (read-only from PC).
struct SecureBucketCard: View {
    let snapshot: DeskSnapshot

    private var secure: Double { snapshot.secureNok ?? 0 }
    private var working: Double? {
        if let w = snapshot.workingEquityNok { return w }
        if let eq = snapshot.equityNok {
            return eq - secure
        }
        return nil
    }

    var body: some View {
        DeskCard(accent: DeskTheme.info) {
            VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                HStack {
                    Text("SECURE · VARIANT A")
                        .font(DeskTypography.sectionLabel)
                        .foregroundStyle(DeskTheme.textDim)
                        .tracking(0.6)
                        .accessibilityAddTraits(.isHeader)
                    Spacer()
                    Text(snapshot.secureVariant ?? "A")
                        .font(DeskTypography.kpiLabel)
                        .foregroundStyle(DeskTheme.info)
                }

                HStack(spacing: DeskSpacing.s3) {
                    metric("Secure (locked)", DeskFormatters.nok(secure), DeskTheme.info)
                    metric("Working", DeskFormatters.nok(working), DeskTheme.profit)
                    metric("Riskable liq.", DeskFormatters.nok(snapshot.riskableLiquidNok), DeskTheme.text)
                }

                if let ref = snapshot.secureRefHwmNok {
                    Text("Ref HWM \(DeskFormatters.nok(ref)) · Soft/hard skim rules run on the PC")
                        .font(DeskTypography.caption)
                        .foregroundStyle(DeskTheme.textMuted)
                } else {
                    Text("Locked secure capital is not used for new stakes. Engine applies soft/hard skim on PC.")
                        .font(DeskTypography.caption)
                        .foregroundStyle(DeskTheme.textMuted)
                }
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(
            "Secure variant A, secure \(DeskFormatters.nok(secure)), working \(DeskFormatters.nok(working))"
        )
    }

    private func metric(_ label: String, _ value: String, _ color: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label.uppercased())
                .font(DeskTypography.kpiLabel)
                .foregroundStyle(DeskTheme.textDim)
            Text(value)
                .font(.system(.subheadline, design: .monospaced).weight(.semibold))
                .foregroundStyle(color)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
