import Foundation

/// Typed navigation value for Pending list → detail.
/// Prefer `betId` when present; carry a bet snapshot so detail stays stable if the list refreshes.
struct PendingBetRoute: Hashable, Identifiable {
    var id: String
    var bet: PendingBet

    static func make(from bet: PendingBet) -> PendingBetRoute {
        let id: String
        if let betId = bet.betId, !betId.isEmpty {
            id = betId
        } else {
            id = bet.id
        }
        return PendingBetRoute(id: id, bet: bet)
    }
}
