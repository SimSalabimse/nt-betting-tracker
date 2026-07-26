import SwiftUI

/// Month grid of daily settled P/L — Book-style performance calendar (heatmap cells).
/// Uses full-era `charts.daily` day keys (UTC midnight); intensity scaled within the visible month.
struct PerformanceCalendarView: View {
    let points: [DailyChartPoint]
    @Binding var selectedRawDay: String?

    /// Month currently displayed (day component ignored; UTC calendar).
    @State private var visibleMonth: Date = Date()

    private static let utcCalendar: Calendar = {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!
        cal.firstWeekday = 2 // Monday first (Europe / Oslo operator habit)
        return cal
    }()

    private static let monthTitleFormatter: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.locale = .current
        f.timeZone = TimeZone(secondsFromGMT: 0)!
        f.dateFormat = "MMMM yyyy"
        return f
    }()

    private var plByDay: [String: DailyChartPoint] {
        Dictionary(uniqueKeysWithValues: points.map { ($0.day.raw, $0) })
    }

    private var monthStart: Date {
        Self.utcCalendar.date(from: Self.utcCalendar.dateComponents([.year, .month], from: visibleMonth))
            ?? visibleMonth
    }

    private var daysInMonth: Int {
        Self.utcCalendar.range(of: .day, in: .month, for: monthStart)?.count ?? 30
    }

    /// Leading blanks so day 1 lands on correct weekday column (Mon=0 … Sun=6).
    private var leadingBlanks: Int {
        let weekday = Self.utcCalendar.component(.weekday, from: monthStart) // Sun=1 … Sat=7
        // Convert to Mon-first index: Mon=0 … Sun=6
        return (weekday + 5) % 7
    }

    private var monthPoints: [DailyChartPoint] {
        points.filter { Self.utcCalendar.isDate($0.day.date, equalTo: monthStart, toGranularity: .month) }
    }

    private var monthPl: Double {
        monthPoints.reduce(0) { $0 + $1.pl }
    }

    private var maxAbsPl: Double {
        max(monthPoints.map { abs($0.pl) }.max() ?? 1, 1)
    }

    private var canGoPrev: Bool {
        guard let earliest = points.first?.day.date else { return false }
        return Self.utcCalendar.compare(monthStart, to: earliest, toGranularity: .month) == .orderedDescending
    }

    private var canGoNext: Bool {
        guard let latest = points.last?.day.date else { return false }
        return Self.utcCalendar.compare(monthStart, to: latest, toGranularity: .month) == .orderedAscending
    }

    var body: some View {
        if points.isEmpty {
            Text("No daily P/L for calendar")
                .font(DeskTypography.caption)
                .foregroundStyle(DeskTheme.textMuted)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.vertical, DeskSpacing.s3)
        } else {
            VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                header
                weekdayHeader
                dayGrid
                footer
            }
            .onAppear { clampVisibleMonth() }
            .onChange(of: points.map(\.day.raw).joined(separator: ",")) { _, _ in
                clampVisibleMonth()
            }
        }
    }

    // MARK: - Header

    private var header: some View {
        HStack(spacing: DeskSpacing.s2) {
            Button {
                shiftMonth(-1)
            } label: {
                Image(systemName: "chevron.left")
                    .font(.body.weight(.semibold))
                    .foregroundStyle(canGoPrev ? DeskTheme.accent : DeskTheme.textDim)
                    .frame(minWidth: 44, minHeight: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .disabled(!canGoPrev)
            .accessibilityLabel("Previous month")

            VStack(spacing: 2) {
                Text(Self.monthTitleFormatter.string(from: monthStart))
                    .font(DeskTypography.sectionLabel)
                    .foregroundStyle(DeskTheme.text)
                    .tracking(0.4)
                Text("Month \(DeskFormatters.nok(monthPl, signed: true)) · \(monthPoints.count) active day\(monthPoints.count == 1 ? "" : "s")")
                    .font(DeskTypography.caption)
                    .foregroundStyle(DeskTheme.pl(monthPl))
            }
            .frame(maxWidth: .infinity)

            Button {
                shiftMonth(1)
            } label: {
                Image(systemName: "chevron.right")
                    .font(.body.weight(.semibold))
                    .foregroundStyle(canGoNext ? DeskTheme.accent : DeskTheme.textDim)
                    .frame(minWidth: 44, minHeight: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .disabled(!canGoNext)
            .accessibilityLabel("Next month")
        }
    }

    private var weekdayHeader: some View {
        HStack(spacing: 4) {
            ForEach(Array(["M", "T", "W", "T", "F", "S", "S"].enumerated()), id: \.offset) { _, label in
                Text(label)
                    .font(DeskTypography.kpiLabel)
                    .foregroundStyle(DeskTheme.textDim)
                    .frame(maxWidth: .infinity)
            }
        }
        .accessibilityHidden(true)
    }

    // MARK: - Grid

    private var dayGrid: some View {
        let cells = buildCells()
        return LazyVGrid(
            columns: Array(repeating: GridItem(.flexible(), spacing: 4), count: 7),
            spacing: 4
        ) {
            ForEach(cells) { cell in
                dayCell(cell)
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Performance calendar")
    }

    private func dayCell(_ cell: CalCell) -> some View {
        Button {
            guard let raw = cell.rawDay else { return }
            if selectedRawDay == raw {
                selectedRawDay = nil
            } else {
                selectedRawDay = raw
                Haptics.lightImpact()
            }
        } label: {
            ZStack {
                RoundedRectangle(cornerRadius: 6)
                    .fill(cellBackground(cell))
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(
                                cell.rawDay != nil && cell.rawDay == selectedRawDay
                                    ? DeskTheme.accent
                                    : DeskTheme.borderSoft.opacity(cell.isPlaceholder ? 0 : 1),
                                lineWidth: cell.rawDay == selectedRawDay ? 2 : 1
                            )
                    )
                if !cell.isPlaceholder {
                    VStack(spacing: 1) {
                        Text("\(cell.dayNumber)")
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .foregroundStyle(cell.pl == nil ? DeskTheme.textDim : DeskTheme.text)
                        if let pl = cell.pl {
                            Text(shortPl(pl))
                                .font(.system(size: 9, weight: .medium, design: .monospaced))
                                .foregroundStyle(DeskTheme.pl(pl))
                                .lineLimit(1)
                                .minimumScaleFactor(0.6)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            .frame(minHeight: 44)
        }
        .buttonStyle(.plain)
        .disabled(cell.isPlaceholder || cell.pl == nil)
        .accessibilityLabel(cellAccessibility(cell))
        .accessibilityAddTraits(cell.rawDay == selectedRawDay ? .isSelected : [])
    }

    private var footer: some View {
        HStack(spacing: DeskSpacing.s3) {
            legendSwatch(DeskTheme.profit.opacity(0.85), "Win day")
            legendSwatch(DeskTheme.loss.opacity(0.85), "Loss day")
            legendSwatch(DeskTheme.surface3, "No bets")
            Spacer()
            if let raw = selectedRawDay, let p = plByDay[raw] {
                Text("\(raw) · \(DeskFormatters.nok(p.pl, signed: true))")
                    .font(DeskTypography.monoFootnote)
                    .foregroundStyle(DeskTheme.pl(p.pl))
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
            }
        }
    }

    private func legendSwatch(_ color: Color, _ label: String) -> some View {
        HStack(spacing: 4) {
            RoundedRectangle(cornerRadius: 3)
                .fill(color)
                .frame(width: 10, height: 10)
            Text(label)
                .font(DeskTypography.caption)
                .foregroundStyle(DeskTheme.textDim)
        }
    }

    // MARK: - Logic

    private func buildCells() -> [CalCell] {
        var cells: [CalCell] = []
        for _ in 0..<leadingBlanks {
            cells.append(CalCell(id: "pad-\(cells.count)", dayNumber: 0, rawDay: nil, pl: nil, isPlaceholder: true))
        }
        for day in 1...daysInMonth {
            guard let date = Self.utcCalendar.date(byAdding: .day, value: day - 1, to: monthStart) else { continue }
            let raw = dayRaw(date)
            let pt = plByDay[raw]
            cells.append(
                CalCell(
                    id: raw,
                    dayNumber: day,
                    rawDay: pt != nil ? raw : raw,
                    pl: pt?.pl,
                    isPlaceholder: false
                )
            )
        }
        // Trailing pads to complete last week row
        while cells.count % 7 != 0 {
            cells.append(CalCell(id: "pad-\(cells.count)", dayNumber: 0, rawDay: nil, pl: nil, isPlaceholder: true))
        }
        return cells
    }

    private func dayRaw(_ date: Date) -> String {
        let y = Self.utcCalendar.component(.year, from: date)
        let m = Self.utcCalendar.component(.month, from: date)
        let d = Self.utcCalendar.component(.day, from: date)
        return String(format: "%04d-%02d-%02d", y, m, d)
    }

    private func cellBackground(_ cell: CalCell) -> Color {
        if cell.isPlaceholder { return Color.clear }
        guard let pl = cell.pl else { return DeskTheme.surface3.opacity(0.55) }
        let intensity = min(1, abs(pl) / maxAbsPl)
        let base: Color = pl >= 0 ? DeskTheme.profit : DeskTheme.loss
        // Floor so tiny days stay readable; scale up for bigger P/L.
        let alpha = 0.22 + 0.65 * intensity
        return base.opacity(alpha)
    }

    private func shortPl(_ pl: Double) -> String {
        let absVal = abs(pl)
        if absVal >= 100 {
            return String(format: "%+.0f", pl)
        }
        if absVal >= 10 {
            return String(format: "%+.0f", pl)
        }
        return String(format: "%+.1f", pl)
    }

    private func cellAccessibility(_ cell: CalCell) -> String {
        if cell.isPlaceholder { return "Empty" }
        if let pl = cell.pl {
            return "Day \(cell.dayNumber), P/L \(DeskFormatters.nok(pl, signed: true))"
        }
        return "Day \(cell.dayNumber), no settled bets"
    }

    private func shiftMonth(_ delta: Int) {
        guard let next = Self.utcCalendar.date(byAdding: .month, value: delta, to: monthStart) else { return }
        visibleMonth = next
        Haptics.lightImpact()
    }

    private func clampVisibleMonth() {
        guard let latest = points.last?.day.date else { return }
        // Prefer month of most recent settled day when first appearing or when out of range.
        if points.isEmpty { return }
        let inRange = points.contains {
            Self.utcCalendar.isDate($0.day.date, equalTo: monthStart, toGranularity: .month)
        }
        if !inRange {
            visibleMonth = latest
        }
    }
}

// MARK: - Cell model

private struct CalCell: Identifiable {
    let id: String
    let dayNumber: Int
    let rawDay: String?
    let pl: Double?
    let isPlaceholder: Bool
}
