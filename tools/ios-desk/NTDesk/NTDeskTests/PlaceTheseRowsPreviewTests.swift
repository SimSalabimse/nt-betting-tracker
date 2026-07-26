import XCTest
@testable import NTDesk

final class PlaceTheseRowsPreviewTests: XCTestCase {
    private func decodeDesk(_ json: String) throws -> DeskSnapshot {
        try JSONDecoder().decode(DeskSnapshot.self, from: Data(json.utf8))
    }
    private func minimalDesk(rowsPreviewJSON: String) -> String {
        """
        {"schema_version":1,"place_these":{"exists":true,"title":"T","summary_line":"S","text_excerpt":"# x","rows_preview":\(rowsPreviewJSON)}}
        """
    }

    func testRowsPreview_emptyArray() throws {
        XCTAssertEqual(try decodeDesk(minimalDesk(rowsPreviewJSON: "[]")).placeThese?.rowsPreview.count, 0)
    }
    func testRowsPreview_stringArray_noOp() throws {
        XCTAssertEqual(try decodeDesk(minimalDesk(rowsPreviewJSON: #"[ "a", "b" ]"#)).placeThese?.rowsPreview.count, 0)
    }
    func testRowsPreview_objectArray() throws {
        let rows = """
        [{"index":1,"match":"A vs B","selection":"A","decimal_odds":2.3,"stake_nok":18,"ev":0.117,"grade":"A","band":"2.2-2.5"}]
        """
        let preview = try XCTUnwrap(try decodeDesk(minimalDesk(rowsPreviewJSON: rows)).placeThese?.rowsPreview)
        XCTAssertEqual(preview.count, 1)
        XCTAssertEqual(preview[0].match, "A vs B")
        XCTAssertEqual(preview[0].decimalOdds!, 2.3, accuracy: 0.001)
    }
    func testRowsPreview_mixedArray_keepsObjects() throws {
        let rows = """
        ["legacy",{"index":2,"match":"X vs Y","selection":"X","decimal_odds":1.5,"stake_nok":5},42]
        """
        let preview = try XCTUnwrap(try decodeDesk(minimalDesk(rowsPreviewJSON: rows)).placeThese?.rowsPreview)
        XCTAssertEqual(preview.count, 1)
        XCTAssertEqual(preview[0].match, "X vs Y")
    }
    func testRowsPreview_missingKey() throws {
        let json = """
        {"schema_version":1,"place_these":{"exists":true,"text_excerpt":"# x"}}
        """
        XCTAssertEqual(try decodeDesk(json).placeThese?.rowsPreview.count, 0)
    }
    func testRowsPreview_null() throws {
        XCTAssertEqual(try decodeDesk(minimalDesk(rowsPreviewJSON: "null")).placeThese?.rowsPreview.count, 0)
    }
    func testDeskSample_stillDecodes() throws {
        let b = Bundle(for: PlaceTheseRowsPreviewTests.self)
        let url = try XCTUnwrap(b.url(forResource: "desk_sample_v1", withExtension: "json", subdirectory: "Fixtures") ?? b.url(forResource: "desk_sample_v1", withExtension: "json"))
        let desk = try JSONDecoder().decode(DeskSnapshot.self, from: try Data(contentsOf: url))
        XCTAssertEqual(desk.placeThese?.rowsPreview.count, 0)
        XCTAssertEqual(desk.equityNok!, 550.99, accuracy: 0.001)
    }
}
