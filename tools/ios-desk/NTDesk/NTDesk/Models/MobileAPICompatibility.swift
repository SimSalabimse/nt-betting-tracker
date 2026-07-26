import Foundation

/// Whether the connected PC mobile-view is new enough for this app build.
enum MobileAPICompatibility: Equatable {
    /// Have not seen a live desk/health yet (or empty).
    case unknown
    /// PC reports `api_version` ≥ app minimum.
    case current(running: String)
    /// Missing `api_version` or version below minimum (old mobile-view).
    case outdated(running: String?)

    /// Minimum `api_version` this app expects (settlement equity, kickoff, product map).
    static let minimumRequired = "1.1.1"

    var isOutdated: Bool {
        if case .outdated = self { return true }
        return false
    }

    /// Short banner / settings copy.
    var warningTitle: String {
        "PC API outdated"
    }

    var warningDetail: String {
        switch self {
        case .unknown:
            return ""
        case .current:
            return ""
        case .outdated(let running):
            let need = Self.minimumRequired
            if let running, !running.isEmpty {
                return "Connected mobile-view \(running) — need ≥ \(need). On the PC: update tools/mobile-view and restart."
            }
            return "This PC has an old mobile-view (no api_version). On the PC: update tools/mobile-view to ≥ \(need) and restart."
        }
    }

    /// Compare two dotted semver-ish strings (1.1.0, 1.1.1). Non-numeric parts → 0.
    static func compareVersions(_ a: String, _ b: String) -> ComparisonResult {
        let pa = a.split(separator: ".").map { Int($0) ?? 0 }
        let pb = b.split(separator: ".").map { Int($0) ?? 0 }
        let n = max(pa.count, pb.count)
        for i in 0..<n {
            let x = i < pa.count ? pa[i] : 0
            let y = i < pb.count ? pb[i] : 0
            if x < y { return .orderedAscending }
            if x > y { return .orderedDescending }
        }
        return .orderedSame
    }

    static func evaluate(apiVersion: String?) -> MobileAPICompatibility {
        let trimmed = apiVersion?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if trimmed.isEmpty {
            return .outdated(running: nil)
        }
        if compareVersions(trimmed, minimumRequired) == .orderedAscending {
            return .outdated(running: trimmed)
        }
        return .current(running: trimmed)
    }
}
