import XCTest
@testable import NTDesk

final class PendingBetRouteTests: XCTestCase {

    func testMake_prefersNonEmptyBetId() {
        var bet = PendingBet()
        bet.betId = "abc123"
        bet.match = "A vs B"
        bet.selection = "Home"
        bet.updatedAt = "2026-01-01T00:00:00Z"

        let route = PendingBetRoute.make(from: bet)
        XCTAssertEqual(route.id, "abc123")
        XCTAssertEqual(route.bet.betId, "abc123")
        XCTAssertEqual(route.bet.match, "A vs B")
    }

    func testMake_fallsBackToCompositeIdWhenBetIdMissing() {
        var bet = PendingBet()
        bet.betId = nil
        bet.match = "A vs B"
        bet.selection = "Home"
        bet.updatedAt = "t1"

        let route = PendingBetRoute.make(from: bet)
        XCTAssertEqual(route.id, bet.id)
        XCTAssertEqual(route.id, "A vs B-Home-t1")
    }

    func testMake_fallsBackWhenBetIdEmpty() {
        var bet = PendingBet()
        bet.betId = ""
        bet.match = "M"
        bet.selection = "S"
        bet.updatedAt = "U"

        let route = PendingBetRoute.make(from: bet)
        XCTAssertEqual(route.id, "M-S-U")
    }

    func testSearch_matchesMatchSelectionSportBetId() {
        var bet = PendingBet()
        bet.betId = "6dfdf58f2642"
        bet.match = "Brockmann vs Jacquemot"
        bet.selection = "Game handikap 3.5"
        bet.sport = "tennis"

        XCTAssertTrue(bet.matchesSearch(""))
        XCTAssertTrue(bet.matchesSearch("  "))
        XCTAssertTrue(bet.matchesSearch("brock"))
        XCTAssertTrue(bet.matchesSearch("HANDIKAP"))
        XCTAssertTrue(bet.matchesSearch("Tennis"))
        XCTAssertTrue(bet.matchesSearch("6dfdf"))
        XCTAssertFalse(bet.matchesSearch("darts"))
        XCTAssertFalse(bet.matchesSearch("nope"))
    }

    func testRoute_isHashableAndStable() {
        var bet = PendingBet()
        bet.betId = "x1"
        bet.match = "M"
        let a = PendingBetRoute.make(from: bet)
        let b = PendingBetRoute.make(from: bet)
        XCTAssertEqual(a, b)
        XCTAssertEqual(a.hashValue, b.hashValue)
        var set = Set<PendingBetRoute>()
        set.insert(a)
        set.insert(b)
        XCTAssertEqual(set.count, 1)
    }
}
