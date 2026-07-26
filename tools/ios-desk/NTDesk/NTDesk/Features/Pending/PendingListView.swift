import SwiftUI
import UIKit

enum PendingSort: String, CaseIterable, Identifiable {
    case kickoff
    case stake

    var id: String { rawValue }
    var label: String {
        switch self {
        case .kickoff: return "Kickoff"
        case .stake: return "Stake"
        }
    }
}

struct PendingListView: View {
    @EnvironmentObject private var sync: SyncService
    @State private var searchText = ""
    @AppStorage("pending_sort") private var sortRaw: String = PendingSort.kickoff.rawValue
    @AppStorage("pending_sport_filter") private var sportFilter: String = ""

    private var sort: PendingSort {
        PendingSort(rawValue: sortRaw) ?? .kickoff
    }

    private var allBets: [PendingBet] {
        sync.snapshot?.pendingBets ?? []
    }

    private var sports: [String] {
        let set = Set(allBets.compactMap { b -> String? in
            let s = (b.sport ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            return s.isEmpty ? nil : s
        })
        return set.sorted()
    }

    private var sortedBets: [PendingBet] {
        let base: [PendingBet]
        if sportFilter.isEmpty {
            base = allBets
        } else {
            base = allBets.filter {
                ($0.sport ?? "").caseInsensitiveCompare(sportFilter) == .orderedSame
            }
        }
        switch sort {
        case .kickoff:
            return base.sorted { a, b in
                let ka = a.kickoff ?? a.date.map { "\($0) 23:59" } ?? "9999"
                let kb = b.kickoff ?? b.date.map { "\($0) 23:59" } ?? "9999"
                if ka != kb { return ka < kb }
                return (a.match ?? "") < (b.match ?? "")
            }
        case .stake:
            return base.sorted { a, b in
                let sa = a.stakeNok ?? -1
                let sb = b.stakeNok ?? -1
                if sa != sb { return sa > sb }
                return (a.match ?? "") < (b.match ?? "")
            }
        }
    }

    private var filteredBets: [PendingBet] {
        sortedBets.filter { $0.matchesSearch(searchText) }
    }

    var body: some View {
        DeskScreenChrome(title: "Pending") {
            Group {
                if sync.snapshot == nil {
                    ScrollView {
                        VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                            FreshnessBanner()
                            EmptyDeskView()
                                .frame(maxWidth: .infinity)
                                .padding(.top, DeskSpacing.s4)
                        }
                        .padding(DeskSpacing.contentPad)
                    }
                    .refreshable { await sync.sync(waitForConnectivity: true) }
                } else {
                    pendingList
                }
            }
            .background(DeskTheme.bg)
            .searchable(text: $searchText, prompt: "Match, selection, sport, bet id")
            .navigationDestination(for: PendingBetRoute.self) { route in
                PendingBetDetailView(bet: route.bet, desk: sync.snapshot)
            }
        }
    }

    private var pendingList: some View {
        List {
            FreshnessBanner()
                .listRowInsets(EdgeInsets(
                    top: DeskSpacing.s2,
                    leading: DeskSpacing.contentPad,
                    bottom: DeskSpacing.s2,
                    trailing: DeskSpacing.contentPad
                ))
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)

            Section {
                Picker("Sort", selection: $sortRaw) {
                    ForEach(PendingSort.allCases) { mode in
                        Text(mode.label).tag(mode.rawValue)
                    }
                }
                .pickerStyle(.segmented)
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)

                if !sports.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: DeskSpacing.s2) {
                            sportChip("All", selected: sportFilter.isEmpty) {
                                sportFilter = ""
                            }
                            ForEach(sports, id: \.self) { sp in
                                sportChip(sp, selected: sportFilter == sp) {
                                    sportFilter = sp
                                }
                            }
                        }
                    }
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                }
            }

            if allBets.isEmpty {
                Text("No open pending / confirmed bets")
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
            } else if filteredBets.isEmpty {
                Text("No bets match filters")
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
            } else {
                ForEach(filteredBets) { bet in
                    // Live countdown — recompute every 30s so "in 2h 15m" stays current.
                    TimelineView(.periodic(from: .now, by: 30)) { context in
                        NavigationLink(value: PendingBetRoute.make(from: bet)) {
                            PendingBetRow(
                                bet: bet,
                                countdown: KickoffCountdown.label(for: bet, now: context.date)
                            )
                        }
                        .buttonStyle(.plain)
                    }
                    .listRowInsets(EdgeInsets(
                        top: DeskSpacing.s2,
                        leading: DeskSpacing.contentPad,
                        bottom: DeskSpacing.s2,
                        trailing: DeskSpacing.contentPad
                    ))
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                    .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                        if let betId = bet.betId, !betId.isEmpty {
                            Button {
                                UIPasteboard.general.string = betId
                                Haptics.lightImpact()
                            } label: {
                                Label("Copy ID", systemImage: "doc.on.doc")
                            }
                            .tint(DeskTheme.accent)
                        }
                    }
                }
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(DeskTheme.bg)
        .refreshable { await sync.sync(waitForConnectivity: true) }
    }

    private func sportChip(_ title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.caption.weight(.semibold))
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(
                    Capsule()
                        .fill(selected ? DeskTheme.accent.opacity(0.25) : DeskTheme.surfaceElev)
                )
                .overlay(
                    Capsule()
                        .stroke(selected ? DeskTheme.accent : DeskTheme.borderSoft, lineWidth: 1)
                )
                .foregroundStyle(selected ? DeskTheme.accent : DeskTheme.textMuted)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Kickoff countdown

enum KickoffCountdown {
    /// Operator kickoff wall clock (notes `kickoff=…`) — Europe/Oslo.
    private static let oslo: TimeZone = TimeZone(identifier: "Europe/Oslo") ?? .current

    private static let kickoffFmt: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = oslo
        f.dateFormat = "yyyy-MM-dd HH:mm"
        f.isLenient = false
        return f
    }()

    private static let dayFmt: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = oslo
        f.dateFormat = "yyyy-MM-dd"
        f.isLenient = false
        return f
    }()

    private static let clockFmt: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.locale = Locale.current
        f.timeZone = oslo
        f.dateFormat = "HH:mm"
        return f
    }()

    /// Prefer full kickoff clock; fall back to match calendar date only.
    static func label(for bet: PendingBet, now: Date = Date()) -> String {
        if let ko = parseKickoff(bet.kickoff) {
            return relative(to: ko, now: now)
        }
        return dateOnlyLabel(bet.date, now: now)
    }

    /// Parse full `YYYY-MM-DD HH:MM` (Oslo wall). Date-only strings are rejected
    /// so we fall back to the calendar-day label instead of a false midnight clock.
    static func parseKickoff(_ raw: String?) -> Date? {
        guard let raw else { return nil }
        let s = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "T", with: " ")
        guard s.count >= 16 else { return nil }
        let head = String(s.prefix(16))
        // Require a space + time so we never treat bare dates as 00:00 kickoffs.
        guard head.contains(" ") else { return nil }
        return kickoffFmt.date(from: head)
    }

    static func relative(to kickoff: Date, now: Date = Date()) -> String {
        let seconds = kickoff.timeIntervalSince(now)
        if seconds <= -45 * 60 {
            return "Started"
        }
        if seconds <= 0 {
            return "Started · now"
        }
        let totalMin = Int((seconds / 60).rounded(.up))
        let days = totalMin / (60 * 24)
        let hours = (totalMin % (60 * 24)) / 60
        let mins = totalMin % 60
        let clock = clockFmt.string(from: kickoff)

        if days >= 2 {
            return "In \(days)d · \(clock)"
        }
        if days == 1 {
            return "Tomorrow · \(clock) · \(hours)h \(mins)m"
        }
        if hours >= 1 {
            return "In \(hours)h \(mins)m · \(clock)"
        }
        if mins > 0 {
            return "In \(mins)m · \(clock)"
        }
        return "Starting · \(clock)"
    }

    /// Date-only fallback when PC has no `kickoff=` in notes.
    static func dateOnlyLabel(_ dateString: String?, now: Date = Date()) -> String {
        guard let dateString,
              let day = dayFmt.date(from: dateString.trimmingCharacters(in: .whitespacesAndNewlines))
        else { return "—" }
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = oslo
        let startToday = cal.startOfDay(for: now)
        let startEvent = cal.startOfDay(for: day)
        let days = cal.dateComponents([.day], from: startToday, to: startEvent).day ?? 0
        if days < 0 { return "Started" }
        if days == 0 { return "Today" }
        if days == 1 { return "Tomorrow" }
        if days < 7 { return "In \(days)d" }
        return dayFmt.string(from: day)
    }
}
