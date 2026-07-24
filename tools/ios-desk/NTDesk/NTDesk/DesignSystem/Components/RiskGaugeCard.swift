import SwiftUI

/// Simplified daily risk gauge — mirrors desktop `risk_gauge` used/cap progress math.
///
/// Visibility: omit when `cap` is nil or ≤ 0, or when `remaining` is nil.
/// Fraction is **used/cap** (not remaining/cap): `used = max(0, cap - remaining)`.
struct RiskGaugeCard: View {
    let dailyRiskCapNok: Double?
    let remainingRiskNok: Double?
    let canBet: Bool?
    var todayRealizedPlNok: Double? = nil

    /// Whether the gauge should be shown for these inputs.
    static func shouldShow(cap: Double?, remaining: Double?) -> Bool {
        guard let cap, cap > 0, remaining != nil else { return false }
        return true
    }

    private var cap: Double { dailyRiskCapNok ?? 0 }
    private var remaining: Double { remainingRiskNok ?? 0 }

    private var used: Double {
        max(0, cap - remaining)
    }

    private var frac: Double {
        cap > 0 ? min(1, used / cap) : 0
    }

    private var barColor: Color {
        if frac > 0.85 || canBet == false {
            return DeskTheme.loss
        }
        if frac > 0.55 {
            return DeskTheme.pending
        }
        return DeskTheme.accent
    }

    private var remainingColor: Color {
        canBet == false ? DeskTheme.loss : DeskTheme.accent
    }

    var body: some View {
        if Self.shouldShow(cap: dailyRiskCapNok, remaining: remainingRiskNok) {
            content
        }
    }

    private var content: some View {
        VStack(alignment: .leading, spacing: DeskSpacing.s2) {
            Text(DeskFormatters.nok(remaining))
                .font(DeskTypography.kpiValue)
                .foregroundStyle(remainingColor)
                .minimumScaleFactor(0.7)
                .lineLimit(1)

            Text("remaining today")
                .font(DeskTypography.caption)
                .foregroundStyle(DeskTheme.textMuted)

            // Used/cap progress bar (visual only; summary is on the card)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(DeskTheme.surface3)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(barColor)
                        .frame(width: max(0, geo.size.width * CGFloat(frac)))
                }
            }
            .frame(height: 8)
            .accessibilityHidden(true)

            Text("Used \(DeskFormatters.nok(used)) of \(DeskFormatters.nok(cap))")
                .font(DeskTypography.caption)
                .foregroundStyle(DeskTheme.textMuted)

            if todayRealizedPlNok != nil {
                Text("Today P/L \(DeskFormatters.nok(todayRealizedPlNok, signed: true))")
                    .font(DeskTypography.monoFootnote)
                    .foregroundStyle(DeskTheme.pl(todayRealizedPlNok))
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(gaugeAccessibilityLabel)
    }

    private var gaugeAccessibilityLabel: String {
        var parts = [
            "Daily risk remaining \(DeskFormatters.nok(remaining))",
            "used \(DeskFormatters.nok(used)) of \(DeskFormatters.nok(cap))",
            "\(Int(frac * 100)) percent used",
        ]
        if let pl = todayRealizedPlNok {
            parts.append("Today P/L \(DeskFormatters.nok(pl, signed: true))")
        }
        return parts.joined(separator: ", ")
    }
}
