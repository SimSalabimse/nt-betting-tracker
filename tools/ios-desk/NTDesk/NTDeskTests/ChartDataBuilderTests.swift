import XCTest
@testable import NTDesk

final class ChartDataBuilderTests: XCTestCase {

    // MARK: - parseDay → Europe/Oslo noon

    func testParseDay_validOsloNoon() {
        let day = ChartDataBuilder.parseDay("2026-07-18")
        XCTAssertNotNil(day)
        XCTAssertEqual(day?.raw, "2026-07-18")

        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "Europe/Oslo") ?? TimeZone(secondsFromGMT: 0)!
        let comps = cal.dateComponents([.year, .month, .day, .hour, .minute, .second], from: day!.date)
        XCTAssertEqual(comps.year, 2026)
        XCTAssertEqual(comps.month, 7)
        XCTAssertEqual(comps.day, 18)
        XCTAssertEqual(comps.hour, 12)
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
        XCTAssertEqual(lines.count, 4)
        XCTAssertTrue(lines[0].contains("496.92"))
        XCTAssertTrue(lines[1].contains("-3.08"))
        XCTAssertTrue(lines[3].localizedCaseInsensitiveContains("match date"))
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

    // MARK: - Parse edges

    func testParseDay_rejectsNonLeapFeb29() {
        XCTAssertNil(ChartDataBuilder.parseDay("2023-02-29"))
        XCTAssertNotNil(ChartDataBuilder.parseDay("2024-02-29"))
    }

    // MARK: - Axis tick policy

    func testAxisTickDates_allLabelsAndThinned() {
        let days = ["2026-07-18", "2026-07-19", "2026-07-20"].compactMap(ChartDataBuilder.parseDay)
        XCTAssertEqual(ChartDataBuilder.axisTickDates(from: days, density: .empty), [])
        XCTAssertEqual(
            ChartDataBuilder.axisTickDates(from: days, density: .allLabels)?.count,
            3
        )
        XCTAssertNil(ChartDataBuilder.axisTickDates(from: days, density: .thinnedLabels))
    }

    func testAxisTickDates_weeklyPrefersMonthStarts() {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!
        let fmt = DateFormatter()
        fmt.calendar = cal
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.timeZone = TimeZone(secondsFromGMT: 0)!
        fmt.dateFormat = "yyyy-MM-dd"
        // Two months of daily keys → at least two month-starts present.
        let start = ChartDataBuilder.parseDay("2025-01-01")!.date
        var days: [ChartDay] = []
        for i in 0..<70 {
            let d = cal.date(byAdding: .day, value: i, to: start)!
            days.append(ChartDataBuilder.parseDay(fmt.string(from: d))!)
        }
        let ticks = ChartDataBuilder.axisTickDates(from: days, density: .weeklyDisplay)
        XCTAssertNotNil(ticks)
        XCTAssertGreaterThanOrEqual(ticks!.count, 2)
        // Month starts only (day == 1 in UTC).
        for t in ticks! {
            XCTAssertEqual(cal.component(.day, from: t), 1)
        }
    }

    // MARK: - Nearest / selection vs display

    func testNearestRawDay_equidistantPrefersEarlier() {
        let pts = ChartDataBuilder.equity([
            EquityPoint(date: "2026-07-18", equity: 100, dayPl: nil, cumPl: nil),
            EquityPoint(date: "2026-07-20", equity: 110, dayPl: nil, cumPl: nil),
        ])
        // Exactly 12h after 18 midnight = 12h before 20 midnight.
        let mid = pts[0].day.date.addingTimeInterval(24 * 3600) // 2026-07-19 00:00 UTC
        // mid is 24h from each — equidistant; earlier day wins.
        XCTAssertEqual(ChartDataBuilder.nearestRawDay(to: mid, in: pts), "2026-07-18")
    }

    func testNearestRawDay_canReturnDayAbsentFromWeeklyDisplay() {
        var wire: [EquityPoint] = []
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
        let raw = ChartDataBuilder.equity(wire)
        let display = ChartDataBuilder.displayEquity(raw)
        XCTAssertEqual(raw.count, 70)
        XCTAssertLessThan(display.count, 70)

        // Pick a mid-week day that is typically not last-of-week display.
        let candidate = raw[3] // 2025-01-04 (Sat after Jan 1 Wed) — may or may not be display
        let selected = ChartDataBuilder.nearestRawDay(to: candidate.day.date, in: raw)
        XCTAssertEqual(selected, candidate.day.raw)
        // Selection is allowed even when not in display set.
        if !display.contains(where: { $0.day.raw == candidate.day.raw }) {
            XCTAssertFalse(display.contains(where: { $0.day.raw == selected }))
        }

        // Daily path: force a non-max-abs mid-week day under 61+ downsample.
        var dailyWire: [DailyPoint] = []
        for i in 0..<70 {
            let d = cal.date(byAdding: .day, value: i, to: start)!
            // Spike only on index 0 of each week-ish; most days have small pl.
            let pl: Double = (i % 7 == 0) ? 50 : 1
            dailyWire.append(DailyPoint(date: fmt.string(from: d), pl: pl, equity: nil))
        }
        let dailyRaw = ChartDataBuilder.daily(dailyWire)
        let dailyDisplay = ChartDataBuilder.displayDaily(dailyRaw)
        let midWeek = dailyRaw.first(where: { $0.pl == 1 })!
        let dailySelected = ChartDataBuilder.nearestRawDay(to: midWeek.day.date, in: dailyRaw)
        XCTAssertEqual(dailySelected, midWeek.day.raw)
        XCTAssertFalse(
            dailyDisplay.contains(where: { $0.day.raw == midWeek.day.raw }),
            "expected mid-week pl=1 day to be absent from max-abs weekly display"
        )
    }
}


