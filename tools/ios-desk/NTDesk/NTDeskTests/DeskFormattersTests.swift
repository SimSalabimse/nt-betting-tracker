import XCTest
@testable import NTDesk

final class DeskFormattersTests: XCTestCase {

    func testParseISO8601_basicAndFractional() {
        XCTAssertNotNil(DeskFormatters.parseISO8601("2026-07-24T18:42:42Z"))
        XCTAssertNotNil(DeskFormatters.parseISO8601("2026-07-24T18:42:42.123Z"))
        XCTAssertNil(DeskFormatters.parseISO8601(nil))
        XCTAssertNil(DeskFormatters.parseISO8601(""))
        XCTAssertNil(DeskFormatters.parseISO8601("not-a-date"))
    }

    func testRelativeTime_nilAndEmpty() {
        XCTAssertEqual(DeskFormatters.relativeTime(nil), "—")
        XCTAssertEqual(DeskFormatters.relativeTime(""), "—")
    }

    func testRelativeTime_unparseableFallsBackToRaw() {
        XCTAssertEqual(
            DeskFormatters.relativeTime("garbage", fallbackToRaw: true),
            "garbage"
        )
        XCTAssertEqual(
            DeskFormatters.relativeTime("garbage", fallbackToRaw: false),
            "—"
        )
    }

    func testRelativeTime_knownOffsetIsNonEmptyAndNotRawISO() {
        let past = Date(timeIntervalSince1970: 1_721_847_762) // 2024-07-24-ish fixed
        let iso = ISO8601DateFormatter().string(from: past)
        let now = past.addingTimeInterval(120) // 2 minutes later
        let relative = DeskFormatters.relativeTime(iso, relativeTo: now)
        XCTAssertFalse(relative.isEmpty)
        XCTAssertNotEqual(relative, "—")
        // Should not echo the raw ISO string when parse succeeds.
        XCTAssertNotEqual(relative, iso)
    }

    func testRelativeTime_dateAPI() {
        let past = Date(timeIntervalSince1970: 1_721_847_762)
        let now = past.addingTimeInterval(3_600)
        let s = DeskFormatters.relativeTime(date: past, relativeTo: now)
        XCTAssertFalse(s.isEmpty)
        XCTAssertNotEqual(s, "—")
    }

    func testNokAndPctUnchangedContracts() {
        XCTAssertEqual(DeskFormatters.nok(nil), "—")
        XCTAssertEqual(DeskFormatters.nok(12.5), "12.50 NOK")
        XCTAssertEqual(DeskFormatters.nok(-1, signed: true), "-1.00 NOK")
        XCTAssertEqual(DeskFormatters.pct(0.125), "12.5%")
        XCTAssertEqual(DeskFormatters.int(3.9), "3")
    }
}
