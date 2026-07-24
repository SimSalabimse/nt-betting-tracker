import Foundation

// Source of truth: desktop/theme.py (“desk night”)
// Mirrors fmt_nok / fmt_pct; KPI surfaces must use these helpers.

enum DeskFormatters {
    /// NOK amount: nil → "—"; 2 decimal places + " NOK"; signed forces +/−.
    static func nok(_ value: Double?, signed: Bool = false) -> String {
        guard let value else { return "—" }
        if signed {
            return String(format: "%+.2f NOK", value)
        }
        return String(format: "%.2f NOK", value)
    }

    /// Ratio percent: nil → "—"; multiplies by 100; 1 decimal place; signed forces +/−.
    /// Input is a ratio (0.125 → "12.5%"), matching desktop `fmt_pct`.
    static func pct(_ value: Double?, signed: Bool = false) -> String {
        guard let value else { return "—" }
        let percent = value * 100
        if signed {
            return String(format: "%+.1f%%", percent)
        }
        return String(format: "%.1f%%", percent)
    }

    /// Integer display: nil → "—"; Double truncates toward zero via `Int(v)`.
    static func int(_ value: Double?) -> String {
        guard let value else { return "—" }
        return String(Int(value))
    }

    /// Integer display: nil → "—".
    static func int(_ value: Int?) -> String {
        guard let value else { return "—" }
        return String(value)
    }
}
