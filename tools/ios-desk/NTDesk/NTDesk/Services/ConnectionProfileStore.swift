import Foundation
import Combine

/// UserDefaults-backed connection profiles (`connection_profiles` JSON array).
/// Injectable `UserDefaults` for unit tests; production uses `.standard` via `shared`.
@MainActor
final class ConnectionProfileStore: ObservableObject {
    static let shared = ConnectionProfileStore()

    static let profilesKey = "connection_profiles"
    /// Legacy single-URL key — dual-written whenever the default profile URL changes.
    static let legacyBaseURLKey = "baseURL"
    static let defaultFallbackURL = "http://127.0.0.1:8787"

    @Published private(set) var profiles: [ConnectionProfile] = []

    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        load()
    }

    // MARK: - Queries

    var defaultProfile: ConnectionProfile? {
        profiles.first(where: \.isDefault) ?? profiles.first
    }

    var defaultBaseURLString: String {
        defaultProfile?.baseURLString
            ?? defaults.string(forKey: Self.legacyBaseURLKey)
            ?? Self.defaultFallbackURL
    }

    // MARK: - Persistence

    func load() {
        guard let data = defaults.data(forKey: Self.profilesKey) else {
            profiles = []
            return
        }
        do {
            profiles = try JSONDecoder().decode([ConnectionProfile].self, from: data)
            normalizeDefaultFlag()
        } catch {
            profiles = []
        }
    }

    private func save() {
        guard let data = try? JSONEncoder().encode(profiles) else { return }
        defaults.set(data, forKey: Self.profilesKey)
    }

    /// Ensure exactly one default when any profiles exist.
    private func normalizeDefaultFlag() {
        guard !profiles.isEmpty else { return }
        let defaultCount = profiles.filter(\.isDefault).count
        if defaultCount == 1 { return }
        if defaultCount == 0 {
            profiles[0].isDefault = true
            save()
            return
        }
        // Multiple defaults — keep first, clear rest.
        var seen = false
        for i in profiles.indices {
            if profiles[i].isDefault {
                if seen {
                    profiles[i].isDefault = false
                } else {
                    seen = true
                }
            }
        }
        save()
    }

    // MARK: - Mutators

    @discardableResult
    func add(name: String, baseURLString: String, makeDefault: Bool = false) -> ConnectionProfile {
        let profile = ConnectionProfile(
            name: name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                ? Self.displayName(for: baseURLString)
                : name.trimmingCharacters(in: .whitespacesAndNewlines),
            baseURLString: baseURLString.trimmingCharacters(in: .whitespacesAndNewlines),
            isDefault: profiles.isEmpty || makeDefault
        )
        if profile.isDefault {
            for i in profiles.indices {
                profiles[i].isDefault = false
            }
        }
        profiles.append(profile)
        save()
        if profile.isDefault {
            dualWriteLegacyBaseURL(profile.baseURLString)
        }
        return profile
    }

    func remove(id: UUID) {
        guard let idx = profiles.firstIndex(where: { $0.id == id }) else { return }
        let wasDefault = profiles[idx].isDefault
        profiles.remove(at: idx)
        if wasDefault, let first = profiles.indices.first {
            profiles[first].isDefault = true
            dualWriteLegacyBaseURL(profiles[first].baseURLString)
        }
        save()
    }

    func setDefault(id: UUID) {
        guard profiles.contains(where: { $0.id == id }) else { return }
        for i in profiles.indices {
            profiles[i].isDefault = (profiles[i].id == id)
        }
        save()
        if let url = profiles.first(where: { $0.id == id })?.baseURLString {
            dualWriteLegacyBaseURL(url)
        }
    }

    /// Update name and/or URL of an existing profile. Dual-writes `"baseURL"` when it is the default.
    func update(id: UUID, name: String? = nil, baseURLString: String? = nil) {
        guard let idx = profiles.firstIndex(where: { $0.id == id }) else { return }
        if let name {
            let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                profiles[idx].name = trimmed
            }
        }
        if let baseURLString {
            profiles[idx].baseURLString = baseURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        }
        save()
        if profiles[idx].isDefault {
            dualWriteLegacyBaseURL(profiles[idx].baseURLString)
        }
    }

    /// Set default profile's URL (or create a default profile). Dual-writes `"baseURL"`.
    func setDefaultBaseURL(_ url: String) {
        let trimmed = url.trimmingCharacters(in: .whitespacesAndNewlines)
        if let idx = profiles.firstIndex(where: \.isDefault) {
            profiles[idx].baseURLString = trimmed
            save()
        } else if let idx = profiles.indices.first {
            profiles[idx].baseURLString = trimmed
            profiles[idx].isDefault = true
            for i in profiles.indices where i != idx {
                profiles[i].isDefault = false
            }
            save()
        } else {
            seedDefault(from: trimmed)
            return
        }
        dualWriteLegacyBaseURL(trimmed)
    }

    func markDefaultSuccess(at iso8601: String) {
        guard let idx = profiles.firstIndex(where: \.isDefault) else { return }
        profiles[idx].lastSuccessAt = iso8601
        save()
    }

    // MARK: - Migration

    /// Seed a single default profile from the legacy `"baseURL"` (or provided URL) when store is empty.
    func seedDefault(from legacyURL: String) {
        guard profiles.isEmpty else { return }
        let url = legacyURL.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolved = url.isEmpty ? Self.defaultFallbackURL : url
        let profile = ConnectionProfile(
            name: Self.displayName(for: resolved),
            baseURLString: resolved,
            isDefault: true
        )
        profiles = [profile]
        save()
        dualWriteLegacyBaseURL(resolved)
    }

    /// First-launch: if profiles empty, migrate `"baseURL"` or seed fallback.
    func migrateFromLegacyBaseURLIfNeeded() {
        guard profiles.isEmpty else { return }
        let legacy = defaults.string(forKey: Self.legacyBaseURLKey) ?? Self.defaultFallbackURL
        seedDefault(from: legacy)
    }

    // MARK: - Helpers

    func dualWriteLegacyBaseURL(_ url: String) {
        defaults.set(url, forKey: Self.legacyBaseURLKey)
    }

    static func displayName(for baseURLString: String) -> String {
        if let host = PrivateHostPolicy.normalizeBaseURL(baseURLString)?.host, !host.isEmpty {
            return host
        }
        let trimmed = baseURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "PC" : trimmed
    }

    /// Test helper: wipe store keys in the injected suite.
    func resetForTesting() {
        defaults.removeObject(forKey: Self.profilesKey)
        profiles = []
    }
}
