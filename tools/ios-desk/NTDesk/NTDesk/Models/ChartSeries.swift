import Foundation

// MARK: - Chart day (ledger calendar key → Date)

/// Ledger calendar day → Date.
/// Normative parse (axis position):
/// - Format: `yyyy-MM-dd`, Gregorian calendar
/// - Time zone: **UTC midnight** (not Europe/Oslo) — dates are day keys without zone
/// - Selection equality: same `yyyy-MM-dd` string / same UTC day component
/// Display labels may use `Locale.current` for formatting only.
struct ChartDay: Hashable, Sendable {
    /// Original API string — selection identity.
    let raw: String
    /// UTC midnight for that day.
    let date: Date
}

// MARK: - Rich series points (callout fields preserved)

struct EquityChartPoint: Identifiable, Hashable, Sendable {
    var id: String { day.raw }
    var day: ChartDay
    var equity: Double
    var dayPl: Double?
    var cumPl: Double?
}

struct DailyChartPoint: Identifiable, Hashable, Sendable {
    var id: String { day.raw }
    var day: ChartDay
    var pl: Double
    var equity: Double?
}

struct DrawdownChartPoint: Identifiable, Hashable, Sendable {
    var id: String { day.raw }
    var day: ChartDay
    var drawdown: Double
    var drawdownPct: Double?
    var equity: Double?
    var peak: Double?
}

/// Sport P/L bar row (categorical Y, not a day series).
struct SportChartPoint: Identifiable, Hashable, Sendable {
    var id: String { name }
    var name: String
    var pl: Double
    var roi: Double
    var n: Double
}

// MARK: - Axis density (design §5)

/// Starting defaults for operator history length; tunable later.
enum ChartAxisDensity: Equatable, Sendable {
    /// No points.
    case empty
    /// 1…14: all raw days as labels.
    case allLabels
    /// 15…60: all raw points plotted; thinned axis labels (`desiredCount` 5…7).
    case thinnedLabels
    /// 61+: weekly display reduction; month-oriented ticks; selection stays on raw.
    case weeklyDisplay

    static func forPointCount(_ count: Int) -> ChartAxisDensity {
        switch count {
        case 0: return .empty
        case 1...14: return .allLabels
        case 15...60: return .thinnedLabels
        default: return .weeklyDisplay
        }
    }

    /// Automatic axis mark count for thinned density.
    var desiredAxisCount: Int {
        switch self {
        case .empty: return 0
        case .allLabels: return 14
        case .thinnedLabels: return 6
        case .weeklyDisplay: return 6
        }
    }
}

// MARK: - Expandable chart kinds

enum ExpandableChartKind: String, Identifiable, CaseIterable, Hashable {
    case equity
    case daily
    case drawdown
    case sport

    var id: String { rawValue }

    var title: String {
        switch self {
        case .equity: return "Equity"
        case .daily: return "Daily P/L"
        case .drawdown: return "Drawdown"
        case .sport: return "By sport (P/L)"
        }
    }
}
