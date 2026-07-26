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

    // MARK: - Relative time (HIG)

    /// Shared relative formatter — abbreviated units (“2 min ago”).
    private static let relativeFormatter: RelativeDateTimeFormatter = {
        let f = RelativeDateTimeFormatter()
        f.unitsStyle = .abbreviated
        return f
    }()

    private static let isoWithFractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static let isoBasic: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    /// Parse common desk ISO-8601 timestamps (`generated_at`, `cached_at`, last sync).
    static func parseISO8601(_ string: String?) -> Date? {
        guard let string, !string.isEmpty else { return nil }
        if let d = isoWithFractional.date(from: string) { return d }
        if let d = isoBasic.date(from: string) { return d }
        return nil
    }

    /// Human relative time from an ISO-8601 string (HIG: `RelativeDateTimeFormatter`).
    /// - nil/empty → `"—"`
    /// - unparseable → raw string when `fallbackToRaw`, else `"—"`
    /// - optional `relativeTo` / `locale` for tests (locale pins unit substrings)
    static func relativeTime(
        _ iso8601: String?,
        relativeTo: Date = Date(),
        fallbackToRaw: Bool = true,
        locale: Locale? = nil
    ) -> String {
        guard let iso8601, !iso8601.isEmpty else { return "—" }
        guard let date = parseISO8601(iso8601) else {
            return fallbackToRaw ? iso8601 : "—"
        }
        return relativeTime(date: date, relativeTo: relativeTo, locale: locale)
    }

    /// Relative phrase from a `Date` (same formatter as string path).
    static func relativeTime(
        date: Date,
        relativeTo: Date = Date(),
        locale: Locale? = nil
    ) -> String {
        if let locale {
            let f = RelativeDateTimeFormatter()
            f.unitsStyle = .abbreviated
            f.locale = locale
            return f.localizedString(for: date, relativeTo: relativeTo)
        }
        return relativeFormatter.localizedString(for: date, relativeTo: relativeTo)
    }
}
