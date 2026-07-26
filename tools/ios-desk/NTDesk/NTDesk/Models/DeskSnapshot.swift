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

struct PendingBet: Codable, Equatable, Hashable, Identifiable {
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
        if let betId, !betId.isEmpty { return betId }
        return "\(match ?? "")-\(selection ?? "")-\(updatedAt ?? "")"
    }

    enum CodingKeys: String, CodingKey {
        case betId = "bet_id"
        case date, match, selection, result, sport
        case decimalOdds = "decimal_odds"
        case stakeNok = "stake_nok"
        case updatedAt = "updated_at"
    }

    /// Case-insensitive match against match / selection / sport / bet_id (PR-4 search).
    func matchesSearch(_ query: String) -> Bool {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return true }
        let fields = [match, selection, sport, betId]
        return fields.contains { ($0 ?? "").localizedCaseInsensitiveContains(q) }
    }
}

struct PlaceThese: Codable, Equatable {
    var exists: Bool?
    var mtime: String?
    var title: String?
    var summaryLine: String?
    var textExcerpt: String?
    /// Object-shaped rows when PC sends them (PR-8). Empty for `[]`, string arrays, or bad payloads.
    /// Never fails whole-desk decode — see custom `init(from:)`.
    var rowsPreview: [PlaceTheseRowPreview]

    enum CodingKeys: String, CodingKey {
        case exists, mtime, title
        case summaryLine = "summary_line"
        case textExcerpt = "text_excerpt"
        case rowsPreview = "rows_preview"
    }

    init(
        exists: Bool? = nil,
        mtime: String? = nil,
        title: String? = nil,
        summaryLine: String? = nil,
        textExcerpt: String? = nil,
        rowsPreview: [PlaceTheseRowPreview] = []
    ) {
        self.exists = exists
        self.mtime = mtime
        self.title = title
        self.summaryLine = summaryLine
        self.textExcerpt = textExcerpt
        self.rowsPreview = rowsPreview
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        exists = try c.decodeIfPresent(Bool.self, forKey: .exists)
        mtime = try c.decodeIfPresent(String.self, forKey: .mtime)
        title = try c.decodeIfPresent(String.self, forKey: .title)
        summaryLine = try c.decodeIfPresent(String.self, forKey: .summaryLine)
        textExcerpt = try c.decodeIfPresent(String.self, forKey: .textExcerpt)
        rowsPreview = Self.decodeRowsPreview(from: c)
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encodeIfPresent(exists, forKey: .exists)
        try c.encodeIfPresent(mtime, forKey: .mtime)
        try c.encodeIfPresent(title, forKey: .title)
        try c.encodeIfPresent(summaryLine, forKey: .summaryLine)
        try c.encodeIfPresent(textExcerpt, forKey: .textExcerpt)
        try c.encode(rowsPreview, forKey: .rowsPreview)
    }

    /// Tolerant: `[]`, `[String]`, `[{…}]`, missing, null, or junk → never throws; junk → `[]`.
    private static func decodeRowsPreview(from c: KeyedDecodingContainer<CodingKeys>) -> [PlaceTheseRowPreview] {
        guard c.contains(.rowsPreview) else { return [] }
        if (try? c.decodeNil(forKey: .rowsPreview)) == true { return [] }
        if let objects = try? c.decode([PlaceTheseRowPreview].self, forKey: .rowsPreview) {
            return objects
        }
        if (try? c.decode([String].self, forKey: .rowsPreview)) != nil {
            return []
        }
        if var unkeyed = try? c.nestedUnkeyedContainer(forKey: .rowsPreview) {
            var collected: [PlaceTheseRowPreview] = []
            while !unkeyed.isAtEnd {
                if let row = try? unkeyed.decode(PlaceTheseRowPreview.self) {
                    collected.append(row)
                } else if (try? unkeyed.decode(String.self)) != nil {
                    continue
                } else {
                    _ = try? unkeyed.decode(DropSelf.self)
                }
            }
            return collected
        }
        return []
    }
}

/// Decodes any single JSON value and discards it (lossy array walk).
private struct DropSelf: Decodable {
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { return }
        if (try? c.decode(Bool.self)) != nil { return }
        if (try? c.decode(Int.self)) != nil { return }
        if (try? c.decode(Double.self)) != nil { return }
        if (try? c.decode(String.self)) != nil { return }
        if (try? c.decode([String: DropSelf].self)) != nil { return }
        if (try? c.decode([DropSelf].self)) != nil { return }
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
