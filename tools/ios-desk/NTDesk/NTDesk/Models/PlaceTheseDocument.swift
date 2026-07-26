import Foundation

/// Quality of a PLACE_THESE parse (excerpt or structured rows).
enum ParseQuality: String, Equatable {
    case full
    case partial
    case failed
}

/// Structured representation of PLACE_THESE for Slip UI.
struct PlaceTheseDocument: Equatable {
    var title: String
    var phaseLine: String?
    var phaseId: String?
    var equityNok: Double?
    var remainingRiskNok: Double?
    var dailyCapNok: Double?
    var notices: [String]
    var bets: [PlaceTheseBet]
    var notes: [String]
    var isEmptySlip: Bool
    var parseQuality: ParseQuality

    static let failed = PlaceTheseDocument(
        title: "PLACE_THESE",
        phaseLine: nil,
        phaseId: nil,
        equityNok: nil,
        remainingRiskNok: nil,
        dailyCapNok: nil,
        notices: [],
        bets: [],
        notes: [],
        isEmptySlip: false,
        parseQuality: .failed
    )
}

struct PlaceTheseBet: Identifiable, Equatable {
    var index: Int?
    var match: String
    var selection: String
    var decimalOdds: Double?
    var stakeNok: Double?
    var ev: Double?
    var grade: String?
    var band: String?

    var id: String { "\(index ?? -1)-\(match)-\(selection)" }
}

/// Future PC object-shaped `rows_preview` element (PR-8).
struct PlaceTheseRowPreview: Codable, Equatable {
    var index: Int?
    var match: String?
    var selection: String?
    var decimalOdds: Double?
    var stakeNok: Double?
    var ev: Double?
    var grade: String?
    var band: String?

    enum CodingKeys: String, CodingKey {
        case index, match, selection, grade, band, ev
        case decimalOdds = "decimal_odds"
        case stakeNok = "stake_nok"
    }

    func asBet() -> PlaceTheseBet? {
        let m = (match ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let s = (selection ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        guard !m.isEmpty, !s.isEmpty else { return nil }
        return PlaceTheseBet(
            index: index,
            match: m,
            selection: s,
            decimalOdds: decimalOdds,
            stakeNok: stakeNok,
            ev: ev,
            grade: grade,
            band: band
        )
    }
}

enum DeskPreferences {
    static let useStructuredSlipKey = "useStructuredSlip"

    /// Default ON when key is unset.
    static var useStructuredSlip: Bool {
        get {
            let defaults = UserDefaults.standard
            if defaults.object(forKey: useStructuredSlipKey) == nil { return true }
            return defaults.bool(forKey: useStructuredSlipKey)
        }
        set {
            UserDefaults.standard.set(newValue, forKey: useStructuredSlipKey)
        }
    }
}
