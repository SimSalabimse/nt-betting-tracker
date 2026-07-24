import SwiftUI

/// Risk-gate display status with normative priority:
/// STOP > FREEZE > RISK FULL > CAN BET.
enum RiskGateStatus: Equatable {
    case stop
    case freeze
    case riskFull
    case canBet

    /// Highest-priority flag wins when multiple risk flags are true.
    static func resolve(stopped: Bool?, freeze: Bool?, canBet: Bool?) -> RiskGateStatus {
        if stopped == true { return .stop }
        if freeze == true { return .freeze }
        if canBet == false { return .riskFull }
        return .canBet
    }

    var title: String {
        switch self {
        case .stop: return "STOP"
        case .freeze: return "FREEZE"
        case .riskFull: return "RISK FULL"
        case .canBet: return "CAN BET"
        }
    }

    /// `true` for CAN BET (profit); `false` for gate blocks (loss).
    var isOk: Bool {
        self == .canBet
    }

    var color: Color {
        isOk ? DeskTheme.profit : DeskTheme.loss
    }
}

/// Compact status chip — maps desktop `pill(text, ok:)`.
struct StatusPill: View {
    let text: String
    var ok: Bool = true

    init(text: String, ok: Bool = true) {
        self.text = text
        self.ok = ok
    }

    init(status: RiskGateStatus) {
        self.text = status.title
        self.ok = status.isOk
    }

    private var color: Color {
        ok ? DeskTheme.profit : DeskTheme.loss
    }

    var body: some View {
        HStack(spacing: DeskSpacing.s2) {
            Circle()
                .fill(color)
                .frame(width: 6, height: 6)
            Text(text)
                .font(.system(.caption2, design: .default).weight(.bold))
                .foregroundStyle(color)
                .lineLimit(1)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(
            Capsule()
                .fill(DeskTheme.surface2)
                .overlay(
                    Capsule()
                        .stroke(DeskTheme.border, lineWidth: 1)
                )
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel(text)
        .accessibilityAddTraits(.isStaticText)
    }
}
