import Foundation
import SwiftUI

/// 0–5 star connection score derived from desk sync state (display only).
struct ConnectionQuality: Equatable {
    var stars: Int
    var title: String
    var detail: String
    var tint: Color

    static let maxStars = 5

    static func evaluate(
        freshness: Freshness,
        isSyncing: Bool,
        lastSuccessSyncAt: String?,
        lastError: String?,
        baseURL: String,
        lastRTTMs: Int? = nil,
        now: Date = Date()
    ) -> ConnectionQuality {
        if isSyncing {
            return ConnectionQuality(
                stars: 3,
                title: "Syncing…",
                detail: "Refreshing desk snapshot from \(displayHost(baseURL)).",
                tint: DeskTheme.accent
            )
        }

        let age = ageSeconds(since: lastSuccessSyncAt, now: now)
        let rttNote = lastRTTMs.map { " · RTT \($0) ms" } ?? ""

        switch freshness {
        case .fresh:
            var stars = 5
            if let rtt = lastRTTMs {
                if rtt > 800 { stars = min(stars, 3) }
                else if rtt > 400 { stars = min(stars, 4) }
            }
            if let age, age > 120 { stars = min(stars, 4) }
            if let age, age > 300 { stars = min(stars, 3) }
            return ConnectionQuality(
                stars: stars,
                title: stars >= 5 ? "Excellent" : (stars >= 4 ? "Good" : "Connected"),
                detail: "Live · last sync \(age.map(relative) ?? "unknown")\(rttNote).",
                tint: DeskTheme.profit
            )

        case .liveNotPersisted:
            return ConnectionQuality(
                stars: 3,
                title: "Live, not saved",
                detail: (lastError ?? "PC responded but cache write failed.") + rttNote,
                tint: DeskTheme.pending
            )

        case .stale:
            return ConnectionQuality(
                stars: age.map { $0 <= 3600 ? 2 : 1 } ?? 1,
                title: "Offline cache",
                detail: "Showing last good snapshot · \(age.map { relative($0) + " ago" } ?? "unknown age").",
                tint: DeskTheme.pending
            )

        case .staleMismatch:
            return ConnectionQuality(
                stars: 1,
                title: "URL mismatch",
                detail: "Cache is from a different base URL than the active profile.",
                tint: DeskTheme.loss
            )

        case .empty:
            return ConnectionQuality(
                stars: 0,
                title: "No connection",
                detail: lastError ?? "No cache yet · set a PC base URL and sync.",
                tint: DeskTheme.textMuted
            )
        }
    }

    private static func displayHost(_ baseURL: String) -> String {
        PrivateHostPolicy.normalizeBaseURL(baseURL)?.host ?? baseURL
    }

    private static func ageSeconds(since iso: String?, now: Date) -> TimeInterval? {
        guard let iso, let date = DeskFormatters.parseISO8601(iso) else { return nil }
        return max(0, now.timeIntervalSince(date))
    }

    private static func relative(_ seconds: TimeInterval) -> String {
        if seconds < 5 { return "just now" }
        if seconds < 60 { return "\(Int(seconds))s ago" }
        if seconds < 3600 { return "\(Int(seconds / 60))m ago" }
        if seconds < 86_400 { return "\(Int(seconds / 3600))h ago" }
        return "\(Int(seconds / 86_400))d ago"
    }
}

struct ConnectionStarsView: View {
    let quality: ConnectionQuality
    var starSize: Font = .title3

    var body: some View {
        HStack(spacing: 6) {
            ForEach(1...ConnectionQuality.maxStars, id: \.self) { i in
                Image(systemName: i <= quality.stars ? "star.fill" : "star")
                    .font(starSize)
                    .foregroundStyle(i <= quality.stars ? quality.tint : DeskTheme.border)
                    .symbolRenderingMode(.hierarchical)
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(quality.stars) of \(ConnectionQuality.maxStars) stars, \(quality.title)")
    }
}
