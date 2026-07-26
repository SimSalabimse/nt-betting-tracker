import XCTest
@testable import NTDesk

final class PlaceTheseParserTests: XCTestCase {
    private func loadFixture(_ name: String, ext: String) throws -> String {
        let b = Bundle(for: PlaceTheseParserTests.self)
        let url = try XCTUnwrap(b.url(forResource: name, withExtension: ext, subdirectory: "Fixtures") ?? b.url(forResource: name, withExtension: ext))
        return try String(contentsOf: url, encoding: .utf8)
    }
    private func loadFixtureData(_ name: String, ext: String) throws -> Data {
        let b = Bundle(for: PlaceTheseParserTests.self)
        let url = try XCTUnwrap(b.url(forResource: name, withExtension: ext, subdirectory: "Fixtures") ?? b.url(forResource: name, withExtension: ext))
        return try Data(contentsOf: url)
    }

    func testParse_emptySlip_fromFixture() throws {
        let doc = PlaceTheseParser.parse(textExcerpt: try loadFixture("PLACE_THESE_empty", ext: "md"))
        XCTAssertEqual(doc.parseQuality, .full)
        XCTAssertTrue(doc.isEmptySlip)
        XCTAssertTrue(doc.bets.isEmpty)
        XCTAssertEqual(doc.phaseId, "1A")
        XCTAssertEqual(doc.equityNok!, 550.99, accuracy: 0.001)
        XCTAssertEqual(doc.remainingRiskNok!, 8.00, accuracy: 0.001)
        XCTAssertEqual(doc.dailyCapNok!, 42.00, accuracy: 0.001)
    }

    func testParse_emptySlip_fromDeskSampleJSON() throws {
        let desk = try JSONDecoder().decode(DeskSnapshot.self, from: try loadFixtureData("desk_sample_v1", ext: "json"))
        let place = try XCTUnwrap(desk.placeThese)
        let doc = PlaceTheseParser.parse(textExcerpt: place.textExcerpt, apiTitle: place.title, summaryLine: place.summaryLine)
        XCTAssertTrue(doc.isEmptySlip)
        XCTAssertEqual(doc.phaseId, "1A")
        XCTAssertTrue(place.rowsPreview.isEmpty)
    }

    func testParse_threeBets_withNotes() throws {
        let doc = PlaceTheseParser.parse(textExcerpt: try loadFixture("PLACE_THESE_2026-07-12", ext: "md"))
        XCTAssertEqual(doc.parseQuality, .full)
        XCTAssertFalse(doc.isEmptySlip)
        XCTAssertEqual(doc.bets.count, 3)
        XCTAssertEqual(doc.phaseId, "1B")
        XCTAssertEqual(doc.bets[0].index, 1)
        XCTAssertEqual(doc.bets[0].decimalOdds!, 2.30, accuracy: 0.001)
        XCTAssertEqual(doc.bets[0].stakeNok!, 18, accuracy: 0.001)
        XCTAssertEqual(doc.bets[0].ev!, 0.117, accuracy: 0.0001)
        XCTAssertEqual(doc.bets[0].grade, "A")
        XCTAssertEqual(doc.notes.count, 3)
    }

    func testParse_garbage_fails() {
        let doc = PlaceTheseParser.parse(textExcerpt: "hello world\nno table here")
        XCTAssertEqual(doc.parseQuality, .failed)
    }

    func testParse_missingOptionalColumns_stillParses() {
        let md = """
        # Bets to place — test
        Phase **2** | Equity **100.00** | Remaining risk **10.00** / cap **20.00**
        | # | Match | Selection | Odds | Stake NOK |
        |---|-------|-----------|------|-----------|
        | 1 | Team A vs Team B | Team A | 1.90 | 12 |
        """
        let doc = PlaceTheseParser.parse(textExcerpt: md)
        XCTAssertEqual(doc.bets.count, 1)
        XCTAssertNil(doc.bets[0].grade)
        XCTAssertEqual(doc.parseQuality, .full)
    }

    func testNormalizeCell_stripsBold() {
        XCTAssertEqual(PlaceTheseParser.normalizeCell("**NO BETS**"), "NO BETS")
    }

    func testResolve_prefersObjectRows() {
        let rows = [PlaceTheseRowPreview(index: 1, match: "A vs B", selection: "A", decimalOdds: 2.0, stakeNok: 10, ev: 0.05, grade: "A", band: "<1.5")]
        let doc = PlaceTheseParser.resolve(textExcerpt: "garbage", apiTitle: "From API", summaryLine: nil, rowsPreview: rows)
        XCTAssertEqual(doc.bets.count, 1)
        XCTAssertEqual(doc.bets[0].match, "A vs B")
    }
}
