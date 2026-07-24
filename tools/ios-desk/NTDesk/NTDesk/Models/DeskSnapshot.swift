import Foundation

/// UI view model only — never the sole cache serialization of desk.
struct DeskSnapshot: Codable, Equatable {
    var schemaVersion: Int?
    var generatedAt: String?
    var viewOnly: Bool?
    var stale: Bool?
    var warnings: [String]?
    var equityNok: Double?
    var liquidNok: Double?
    var pendingAtRiskNok: Double?
    var realizedPlNok: Double?
    var baselineNok: Double?
    var settledCount: Int?
    var pendingCount: Int?
    var bankrollUpdatedAt: String?
    var phaseId: String?
    var phaseLabel: String?
    var canBet: Bool?
    var sizeMode: String?
    var stopped: Bool?
    var freeze: Bool?
    var remainingRiskNok: Double?
    var dailyRiskCapNok: Double?
    var openPendingRiskNok: Double?
    var todayRealizedPlNok: Double?
    var unitSizeNok: Double?
    var riskReasons: [String]?
    var pendingBets: [PendingBet]?
    var placeThese: PlaceThese?
    var statusExcerpt: String?
    var charts: ChartsPayload?

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case generatedAt = "generated_at"
        case viewOnly = "view_only"
        case stale, warnings
        case equityNok = "equity_nok"
        case liquidNok = "liquid_nok"
        case pendingAtRiskNok = "pending_at_risk_nok"
        case realizedPlNok = "realized_pl_nok"
        case baselineNok = "baseline_nok"
        case settledCount = "settled_count"
        case pendingCount = "pending_count"
        case bankrollUpdatedAt = "bankroll_updated_at"
        case phaseId = "phase_id"
        case phaseLabel = "phase_label"
        case canBet = "can_bet"
        case sizeMode = "size_mode"
        case stopped, freeze
        case remainingRiskNok = "remaining_risk_nok"
        case dailyRiskCapNok = "daily_risk_cap_nok"
        case openPendingRiskNok = "open_pending_risk_nok"
        case todayRealizedPlNok = "today_realized_pl_nok"
        case unitSizeNok = "unit_size_nok"
        case riskReasons = "risk_reasons"
        case pendingBets = "pending_bets"
        case placeThese = "place_these"
        case statusExcerpt = "status_excerpt"
        case charts
    }
}

struct PendingBet: Codable, Equatable, Identifiable {
    var betId: String?
    var date: String?
    var match: String?
    var selection: String?
    var decimalOdds: Double?
    var stakeNok: Double?
    var result: String?
    var sport: String?
    var updatedAt: String?

    var id: String {
        betId ?? "\(match ?? "")-\(selection ?? "")-\(updatedAt ?? "")"
    }

    enum CodingKeys: String, CodingKey {
        case betId = "bet_id"
        case date, match, selection, result, sport
        case decimalOdds = "decimal_odds"
        case stakeNok = "stake_nok"
        case updatedAt = "updated_at"
    }
}

struct PlaceThese: Codable, Equatable {
    var exists: Bool?
    var mtime: String?
    var title: String?
    var summaryLine: String?
    var textExcerpt: String?
    var rowsPreview: [String]?

    enum CodingKeys: String, CodingKey {
        case exists, mtime, title
        case summaryLine = "summary_line"
        case textExcerpt = "text_excerpt"
        case rowsPreview = "rows_preview"
    }
}

struct ChartsPayload: Codable, Equatable {
    var rangeLabel: String?
    var overall: OverallStats?
    var equityCurve: [EquityPoint]?
    var daily: [DailyPoint]?
    var drawdown: [DrawdownPoint]?
    var maxDrawdown: Double?
    var bySport: [String: SportStats]?

    enum CodingKeys: String, CodingKey {
        case rangeLabel = "range_label"
        case overall
        case equityCurve = "equity_curve"
        case daily, drawdown
        case maxDrawdown = "max_drawdown"
        case bySport = "by_sport"
    }
}

struct OverallStats: Codable, Equatable {
    var nSettled: Double?
    var nPending: Double?
    var wins: Double?
    var losses: Double?
    var stake: Double?
    var pl: Double?
    var roi: Double?
    var winrate: Double?

    enum CodingKeys: String, CodingKey {
        case nSettled = "n_settled"
        case nPending = "n_pending"
        case wins, losses, stake, pl, roi, winrate
    }
}

struct EquityPoint: Codable, Equatable, Identifiable {
    var date: String?
    var equity: Double?
    var dayPl: Double?
    var cumPl: Double?
    var id: String { date ?? UUID().uuidString }

    enum CodingKeys: String, CodingKey {
        case date, equity
        case dayPl = "day_pl"
        case cumPl = "cum_pl"
    }
}

struct DailyPoint: Codable, Equatable, Identifiable {
    var date: String?
    var pl: Double?
    var equity: Double?
    var id: String { date ?? UUID().uuidString }
}

struct DrawdownPoint: Codable, Equatable, Identifiable {
    var date: String?
    var equity: Double?
    var drawdown: Double?
    var drawdownPct: Double?
    var peak: Double?
    var id: String { date ?? UUID().uuidString }

    enum CodingKeys: String, CodingKey {
        case date, equity, drawdown, peak
        case drawdownPct = "drawdown_pct"
    }
}

struct SportStats: Codable, Equatable {
    var n: Double?
    var wins: Double?
    var losses: Double?
    var stake: Double?
    var pl: Double?
    var roi: Double?
    var winrate: Double?
}
