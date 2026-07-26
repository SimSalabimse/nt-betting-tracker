import Foundation

/// Builds typed chart series from `/api/desk` → `charts` wire models.
/// Display-only: no recompute of equity/P/L/drawdown.
enum ChartDataBuilder {

    // MARK: - Day parse (UTC midnight)

    /// Shared formatter: `yyyy-MM-dd` in UTC / Gregorian / en_US_POSIX.
    /// **Main-thread only** — `DateFormatter` is not thread-safe; call from UI / tests.
    private static let dayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(secondsFromGMT: 0)!
        f.dateFormat = "yyyy-MM-dd"
        f.isLenient = false
        return f
    }()

    private static let utcCalendar: Calendar = {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!
        return cal
    }()

    /// Parse ledger day string → `ChartDay` at UTC midnight. Rejects garbage / empty.
    static func parseDay(_ raw: String?) -> ChartDay? {
        guard let raw else { return nil }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        // Strict yyyy-MM-dd shape before formatter (rejects alternate separators).
        guard trimmed.range(of: #"^\d{4}-\d{2}-\d{2}$"#, options: .regularExpression) != nil else {
            return nil
        }
        guard let date = dayFormatter.date(from: trimmed) else { return nil }
        // Reject rollover of invalid calendar days even if formatter is lenient.
        guard dayFormatter.string(from: date) == trimmed else { return nil }
        return ChartDay(raw: trimmed, date: date)
    }

    // MARK: - Series map

    /// Skip points with unparsable day or missing required numeric field.
    static func equity(_ pts: [EquityPoint]) -> [EquityChartPoint] {
        pts.compactMap { p in
            guard let day = parseDay(p.date), let equity = p.equity else { return nil }
            return EquityChartPoint(day: day, equity: equity, dayPl: p.dayPl, cumPl: p.cumPl)
        }
        .sorted { $0.day.date < $1.day.date }
    }

    static func daily(_ pts: [DailyPoint]) -> [DailyChartPoint] {
        pts.compactMap { p in
            guard let day = parseDay(p.date), let pl = p.pl else { return nil }
            return DailyChartPoint(day: day, pl: pl, equity: p.equity)
        }
        .sorted { $0.day.date < $1.day.date }
    }

    static func drawdown(_ pts: [DrawdownPoint]) -> [DrawdownChartPoint] {
        pts.compactMap { p in
            guard let day = parseDay(p.date), let dd = p.drawdown else { return nil }
            return DrawdownChartPoint(
                day: day,
                drawdown: dd,
                drawdownPct: p.drawdownPct,
                equity: p.equity,
                peak: p.peak
            )
        }
        .sorted { $0.day.date < $1.day.date }
    }

    static func sports(_ bySport: [String: SportStats]?) -> [SportChartPoint] {
        (bySport ?? [:])
            .map { name, stats in
                SportChartPoint(
                    name: name,
                    pl: stats.pl ?? 0,
                    roi: stats.roi ?? 0,
                    n: stats.n ?? 0
                )
            }
            .sorted { $0.pl > $1.pl }
    }

    // MARK: - Selection resolve (nearest raw by day)

    static func nearestRawDay(to date: Date?, in points: [EquityChartPoint]) -> String? {
        nearest(to: date, in: points, day: \.day)
    }

    static func nearestRawDay(to date: Date?, in points: [DailyChartPoint]) -> String? {
        nearest(to: date, in: points, day: \.day)
    }

    static func nearestRawDay(to date: Date?, in points: [DrawdownChartPoint]) -> String? {
        nearest(to: date, in: points, day: \.day)
    }

    /// Closest day by absolute interval; ties break to the **earlier** day (stable).
    private static func nearest<T>(
        to date: Date?,
        in points: [T],
        day: (T) -> ChartDay
    ) -> String? {
        guard let date, !points.isEmpty else { return nil }
        return points.min(by: { a, b in
            let da = abs(day(a).date.timeIntervalSince(date))
            let db = abs(day(b).date.timeIntervalSince(date))
            if da != db { return da < db }
            return day(a).date < day(b).date
        }).map { day($0).raw }
    }

    // MARK: - Display downsample (61+ only; never invent aggregates)

    static func lastOfWeekDisplay(_ points: [EquityChartPoint]) -> [EquityChartPoint] {
        guard points.count >= 61 else { return points }
        return lastOfWeek(points, day: \.day)
    }

    static func lastOfWeekDisplay(_ points: [DrawdownChartPoint]) -> [DrawdownChartPoint] {
        guard points.count >= 61 else { return points }
        return lastOfWeek(points, day: \.day)
    }

    static func maxAbsDayWithinWeek(_ points: [DailyChartPoint]) -> [DailyChartPoint] {
        guard points.count >= 61 else { return points }
        var buckets: [String: DailyChartPoint] = [:]
        var order: [String] = []
        for p in points {
            let week = isoWeekKey(for: p.day.date)
            if buckets[week] == nil { order.append(week) }
            if let existing = buckets[week] {
                if abs(p.pl) > abs(existing.pl) {
                    buckets[week] = p
                }
            } else {
                buckets[week] = p
            }
        }
        return order.compactMap { buckets[$0] }
    }

    static func displayEquity(_ raw: [EquityChartPoint]) -> [EquityChartPoint] {
        switch ChartAxisDensity.forPointCount(raw.count) {
        case .weeklyDisplay: return lastOfWeekDisplay(raw)
        default: return raw
        }
    }

    static func displayDaily(_ raw: [DailyChartPoint]) -> [DailyChartPoint] {
        switch ChartAxisDensity.forPointCount(raw.count) {
        case .weeklyDisplay: return maxAbsDayWithinWeek(raw)
        default: return raw
        }
    }

    static func displayDrawdown(_ raw: [DrawdownChartPoint]) -> [DrawdownChartPoint] {
        switch ChartAxisDensity.forPointCount(raw.count) {
        case .weeklyDisplay: return lastOfWeekDisplay(raw)
        default: return raw
        }
    }

    static func axisTickDates(from days: [ChartDay], density: ChartAxisDensity) -> [Date]? {
        switch density {
        case .empty:
            return []
        case .allLabels:
            return days.map(\.date)
        case .thinnedLabels:
            return nil
        case .weeklyDisplay:
            let monthStarts = days.filter { isMonthStart($0.date) }.map(\.date)
            if monthStarts.count >= 2 { return monthStarts }
            return lastOfWeek(days, day: { $0 }).map(\.date)
        }
    }

    static func equityDetailLines(_ pts: [EquityChartPoint], selected raw: String?) -> [String] {
        guard let raw, let p = pts.first(where: { $0.day.raw == raw }) else { return [] }
        var lines: [String] = []
        lines.append("Equity  \(DeskFormatters.nok(p.equity))")
        if p.dayPl != nil {
            lines.append("Day P/L \(DeskFormatters.nok(p.dayPl, signed: true))")
        }
        if p.cumPl != nil {
            lines.append("Cum P/L \(DeskFormatters.nok(p.cumPl, signed: true))")
        }
        return lines
    }

    static func dailyDetailLines(_ pts: [DailyChartPoint], selected raw: String?) -> [String] {
        guard let raw, let p = pts.first(where: { $0.day.raw == raw }) else { return [] }
        var lines: [String] = []
        lines.append("P/L     \(DeskFormatters.nok(p.pl, signed: true))")
        if p.equity != nil {
            lines.append("Equity  \(DeskFormatters.nok(p.equity))")
        }
        return lines
    }

    static func drawdownDetailLines(_ pts: [DrawdownChartPoint], selected raw: String?) -> [String] {
        guard let raw, let p = pts.first(where: { $0.day.raw == raw }) else { return [] }
        var lines: [String] = []
        lines.append("Drawdown \(DeskFormatters.nok(p.drawdown))")
        if let pct = p.drawdownPct {
            lines.append("DD %     \(DeskFormatters.pct(pct))")
        }
        if p.equity != nil {
            lines.append("Equity   \(DeskFormatters.nok(p.equity))")
        }
        if p.peak != nil {
            lines.append("Peak     \(DeskFormatters.nok(p.peak))")
        }
        return lines
    }

    static func sportDetailLines(_ sports: [SportChartPoint], selected name: String?) -> [String] {
        guard let name, let s = sports.first(where: { $0.name == name }) else { return [] }
        return [
            "P/L  \(DeskFormatters.nok(s.pl, signed: true))",
            "ROI  \(DeskFormatters.pct(s.roi))",
            "n    \(DeskFormatters.int(s.n))",
        ]
    }

    static func equitySummary(_ pts: [EquityChartPoint]) -> String {
        let lastStr = pts.last.map { DeskFormatters.nok($0.equity) } ?? "—"
        return "Equity curve, \(pts.count) points, latest \(lastStr)"
    }

    static func dailySummary(_ pts: [DailyChartPoint]) -> String {
        let total = pts.map(\.pl).reduce(0, +)
        return "Daily P/L, \(pts.count) days, total \(DeskFormatters.nok(total, signed: true))"
    }

    static func drawdownSummary(_ pts: [DrawdownChartPoint]) -> String {
        let worst = pts.map(\.drawdown).max()
        let worstStr = worst.map { DeskFormatters.nok($0) } ?? "—"
        return "Drawdown series, \(pts.count) points, worst \(worstStr)"
    }

    static func sportSummary(_ sports: [SportChartPoint]) -> String {
        "By sport P/L, \(sports.count) sports"
    }

    private static func lastOfWeek<T>(_ points: [T], day: (T) -> ChartDay) -> [T] {
        var buckets: [String: T] = [:]
        var order: [String] = []
        for p in points {
            let d = day(p).date
            let week = isoWeekKey(for: d)
            if buckets[week] == nil { order.append(week) }
            if let existing = buckets[week] {
                let existingDay = day(existing).date
                let preferNew = isFriday(d) || (!isFriday(existingDay) && d > existingDay)
                if preferNew { buckets[week] = p }
            } else {
                buckets[week] = p
            }
        }
        return order.compactMap { buckets[$0] }
    }

    private static func isoWeekKey(for date: Date) -> String {
        let y = utcCalendar.component(.yearForWeekOfYear, from: date)
        let w = utcCalendar.component(.weekOfYear, from: date)
        return String(format: "%04d-W%02d", y, w)
    }

    private static func isFriday(_ date: Date) -> Bool {
        utcCalendar.component(.weekday, from: date) == 6
    }

    private static func isMonthStart(_ date: Date) -> Bool {
        utcCalendar.component(.day, from: date) == 1
    }
}
