import XCTest
@testable import NTDesk

final class ChartDataBuilderTests: XCTestCase {

    // MARK: - parseDay → UTC midnight

    func testParseDay_validUTCMidnight() {
        let day = ChartDataBuilder.parseDay("2026-07-18")
        XCTAssertNotNil(day)
        XCTAssertEqual(day?.raw, "2026-07-18")

        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!
        let comps = cal.dateComponents([.year, .month, .day, .hour, .minute, .second], from: day!.date)
        XCTAssertEqual(comps.year, 2026)
        XCTAssertEqual(comps.month, 7)
        XCTAssertEqual(comps.day, 18)
        XCTAssertEqual(comps.hour, 0)
        XCTAssertEqual(comps.minute, 0)
        XCTAssertEqual(comps.second, 0)
    }

    func testParseDay_rejectsGarbage() {
        XCTAssertNil(ChartDataBuilder.parseDay(nil))
        XCTAssertNil(ChartDataBuilder.parseDay(""))
        XCTAssertNil(ChartDataBuilder.parseDay("   "))
        XCTAssertNil(ChartDataBuilder.parseDay("not-a-date"))
        XCTAssertNil(ChartDataBuilder.parseDay("2026/07/18"))
        XCTAssertNil(ChartDataBuilder.parseDay("07-18-2026"))
        XCTAssertNil(ChartDataBuilder.parseDay("2026-13-01"))
        XCTAssertNil(ChartDataBuilder.parseDay("2026-07-32"))
    }

    func testParseDay_trimsWhitespace() {
        let day = ChartDataBuilder.parseDay("  2026-07-21  ")
        XCTAssertEqual(day?.raw, "2026-07-21")
    }

    // MARK: - Series mapping

    func testEquity_mapsFieldsAndSkipsBad() {
        let wire: [EquityPoint] = [
            EquityPoint(date: "2026-07-18", equity: 496.92, dayPl: -3.08, cumPl: -3.08),
            EquityPoint(date: "bad", equity: 100, dayPl: 1, cumPl: 1),
            EquityPoint(date: "2026-07-19", equity: nil, dayPl: 1, cumPl: 1),
            EquityPoint(date: "2026-07-20", equity: 525.11, dayPl: 3.48, cumPl: 25.11),
        ]
        let pts = ChartDataBuilder.equity(wire)
        XCTAssertEqual(pts.count, 2)
        XCTAssertEqual(pts[0].day.raw, "2026-07-18")
        XCTAssertEqual(pts[0].equity, 496.92)
        XCTAssertEqual(pts[0].dayPl, -3.08)
        XCTAssertEqual(pts[0].cumPl, -3.08)
        XCTAssertEqual(pts[1].day.raw, "2026-07-20")
        XCTAssertEqual(pts[1].equity, 525.11)
    }

    func testDaily_mapsFields() {
        let wire: [DailyPoint] = [
            DailyPoint(date: "2026-07-19", pl: 24.71, equity: 521.63),
            DailyPoint(date: "2026-07-18", pl: -3.08, equity: 496.92),
        ]
        let pts = ChartDataBuilder.daily(wire)
        XCTAssertEqual(pts.map(\.day.raw), ["2026-07-18", "2026-07-19"])
        XCTAssertEqual(pts[0].pl, -3.08)
        XCTAssertEqual(pts[1].equity, 521.63)
    }

    func testDrawdown_mapsFields() {
        let wire: [DrawdownPoint] = [
            DrawdownPoint(
                date: "2026-07-18",
                equity: 496.92,
                drawdown: 0,
                drawdownPct: 0,
                peak: 496.92
            ),
            DrawdownPoint(
                date: "2026-07-19",
                equity: 480,
                drawdown: 16.92,
                drawdownPct: 0.034,
                peak: 496.92
            ),
        ]
        let pts = ChartDataBuilder.drawdown(wire)
        XCTAssertEqual(pts.count, 2)
        XCTAssertEqual(pts[1].drawdown, 16.92)
        XCTAssertEqual(pts[1].drawdownPct, 0.034)
        XCTAssertEqual(pts[1].peak, 496.92)
        XCTAssertEqual(pts[1].equity, 480)
    }

    func testSports_sortsByPLDescending() {
        let stats: [String: SportStats] = [
            "tennis": SportStats(n: 10, wins: nil, losses: nil, stake: nil, pl: 5, roi: 0.1, winrate: nil),
            "darts": SportStats(n: 5, wins: nil, losses: nil, stake: nil, pl: 20, roi: 0.3, winrate: nil),
            "football": SportStats(n: 2, wins: nil, losses: nil, stake: nil, pl: -3, roi: -0.1, winrate: nil),
        ]
        let pts = ChartDataBuilder.sports(stats)
        XCTAssertEqual(pts.map(\.name), ["darts", "tennis", "football"])
        XCTAssertEqual(pts[0].pl, 20)
        XCTAssertEqual(pts[0].n, 5)
    }

    // MARK: - Density policy

    func testAxisDensityThresholds() {
        XCTAssertEqual(ChartAxisDensity.forPointCount(0), .empty)
        XCTAssertEqual(ChartAxisDensity.forPointCount(1), .allLabels)
        XCTAssertEqual(ChartAxisDensity.forPointCount(14), .allLabels)
        XCTAssertEqual(ChartAxisDensity.forPointCount(15), .thinnedLabels)
        XCTAssertEqual(ChartAxisDensity.forPointCount(60), .thinnedLabels)
        XCTAssertEqual(ChartAxisDensity.forPointCount(61), .weeklyDisplay)
        XCTAssertEqual(ChartAxisDensity.forPointCount(200), .weeklyDisplay)
    }

    // MARK: - Nearest selection

    func testNearestRawDay_picksClosest() {
        let pts = ChartDataBuilder.equity([
            EquityPoint(date: "2026-07-18", equity: 100, dayPl: nil, cumPl: nil),
            EquityPoint(date: "2026-07-20", equity: 110, dayPl: nil, cumPl: nil),
            EquityPoint(date: "2026-07-22", equity: 120, dayPl: nil, cumPl: nil),
        ])
        let mid = ChartDataBuilder.parseDay("2026-07-19")!.date
        // 19 is closer to 18 than 20 at midnight boundaries; either 18 or 20 acceptable by distance.
        // Explicitly test exact hit and between.
        XCTAssertEqual(ChartDataBuilder.nearestRawDay(to: pts[1].day.date, in: pts), "2026-07-20")
        let justAfter18 = pts[0].day.date.addingTimeInterval(12 * 3600)
        XCTAssertEqual(ChartDataBuilder.nearestRawDay(to: justAfter18, in: pts), "2026-07-18")
        _ = mid
    }

    // MARK: - Display downsample (61+)

    func testLastOfWeekDisplay_onlyWhen61Plus() {
        var wire: [EquityPoint] = []
        // 10 days — no downsample
        for i in 0..<10 {
            wire.append(EquityPoint(
                date: String(format: "2026-01-%02d", i + 1),
                equity: Double(i),
                dayPl: 0,
                cumPl: Double(i)
            ))
        }
        let short = ChartDataBuilder.equity(wire)
        XCTAssertEqual(ChartDataBuilder.displayEquity(short).count, 10)

        // 70 consecutive days → weekly reduction
        wire = []
        let start = ChartDataBuilder.parseDay("2025-01-01")!.date
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!
        let fmt = DateFormatter()
        fmt.calendar = cal
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.timeZone = TimeZone(secondsFromGMT: 0)!
        fmt.dateFormat = "yyyy-MM-dd"
        for i in 0..<70 {
            let d = cal.date(byAdding: .day, value: i, to: start)!
            wire.append(EquityPoint(date: fmt.string(from: d), equity: Double(i), dayPl: 0, cumPl: Double(i)))
        }
        let long = ChartDataBuilder.equity(wire)
        XCTAssertEqual(long.count, 70)
        let display = ChartDataBuilder.displayEquity(long)
        XCTAssertLessThan(display.count, 70)
        XCTAssertGreaterThan(display.count, 5)
        // Selection still resolves against full raw
        XCTAssertEqual(
            ChartDataBuilder.nearestRawDay(to: long[35].day.date, in: long),
            long[35].day.raw
        )
    }

    func testMaxAbsDayWithinWeek_picksLargestAbsPL() {
        // Build 70 days with a known spike
        var wire: [DailyPoint] = []
        let start = ChartDataBuilder.parseDay("2025-01-01")!.date
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!
        let fmt = DateFormatter()
        fmt.calendar = cal
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.timeZone = TimeZone(secondsFromGMT: 0)!
        fmt.dateFormat = "yyyy-MM-dd"
        for i in 0..<70 {
            let d = cal.date(byAdding: .day, value: i, to: start)!
            let pl: Double = (i == 10) ? -99 : Double(i % 5)
            wire.append(DailyPoint(date: fmt.string(from: d), pl: pl, equity: 500 + Double(i)))
        }
        let pts = ChartDataBuilder.daily(wire)
        let display = ChartDataBuilder.displayDaily(pts)
        XCTAssertLessThan(display.count, 70)
        XCTAssertTrue(display.contains(where: { $0.pl == -99 }), "max-abs week should keep the -99 day")
    }

    // MARK: - Callout / a11y helpers

    func testEquityDetailLines() {
        let pts = ChartDataBuilder.equity([
            EquityPoint(date: "2026-07-18", equity: 496.92, dayPl: -3.08, cumPl: -3.08),
        ])
        let lines = ChartDataBuilder.equityDetailLines(pts, selected: "2026-07-18")
        XCTAssertEqual(lines.count, 3)
        XCTAssertTrue(lines[0].contains("496.92"))
        XCTAssertTrue(lines[1].contains("-3.08"))
        XCTAssertEqual(ChartDataBuilder.equityDetailLines(pts, selected: nil), [])
        XCTAssertEqual(ChartDataBuilder.equityDetailLines(pts, selected: "2099-01-01"), [])
    }

    func testSummaries() {
        let equity = ChartDataBuilder.equity([
            EquityPoint(date: "2026-07-18", equity: 500, dayPl: nil, cumPl: nil),
            EquityPoint(date: "2026-07-19", equity: 550, dayPl: nil, cumPl: nil),
        ])
        XCTAssertTrue(ChartDataBuilder.equitySummary(equity).contains("2 points"))
        XCTAssertTrue(ChartDataBuilder.equitySummary(equity).contains("550.00"))

        let daily = ChartDataBuilder.daily([
            DailyPoint(date: "2026-07-18", pl: -3, equity: nil),
            DailyPoint(date: "2026-07-19", pl: 5, equity: nil),
        ])
        XCTAssertTrue(ChartDataBuilder.dailySummary(daily).contains("2 days"))

        let dd = ChartDataBuilder.drawdown([
            DrawdownPoint(date: "2026-07-18", equity: 100, drawdown: 0, drawdownPct: 0, peak: 100),
            DrawdownPoint(date: "2026-07-19", equity: 90, drawdown: 10, drawdownPct: 0.1, peak: 100),
        ])
        XCTAssertTrue(ChartDataBuilder.drawdownSummary(dd).contains("worst"))
    }
}


