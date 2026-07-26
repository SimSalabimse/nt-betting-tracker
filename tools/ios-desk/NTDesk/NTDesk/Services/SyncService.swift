import Foundation
import Combine

enum Freshness: String {
    case fresh
    case stale
    case staleMismatch
    case liveNotPersisted
    case empty
}

@MainActor
final class SyncService: ObservableObject {
    @Published var snapshot: DeskSnapshot?
    @Published var freshness: Freshness = .empty
    @Published var lastError: String?
    @Published var lastSuccessSyncAt: String?
    @Published var isSyncing = false

    /// Public get/set facade over the default `ConnectionProfile`.
    /// Legacy `LegacySettingsView` binds/saves this; dual-writes UserDefaults `"baseURL"`.
    @Published var baseURLString: String {
        didSet {
            guard !isApplyingProfileURL else { return }
            profileStore.setDefaultBaseURL(baseURLString)
        }
    }

    /// Additive multi-profile surface (redesign). Same array as the store.
    var profiles: [ConnectionProfile] {
        profileStore.profiles
    }

    let profileStore: ConnectionProfileStore

    private let cache = CacheStore()
    private let client = DeskAPIClient()
    private var timer: Timer?
    /// Prevents recursive baseURLString ↔ profile store updates.
    private var isApplyingProfileURL = false
    private var profileCancellable: AnyCancellable?

    init(profileStore: ConnectionProfileStore? = nil) {
        let store = profileStore ?? ConnectionProfileStore.shared
        self.profileStore = store
        store.migrateFromLegacyBaseURLIfNeeded()
        // didSet is not invoked during init assignment — dual-write already handled by migrate/seed.
        self.baseURLString = store.defaultBaseURLString
        // Forward profile mutations so Settings / ProfilesListView re-render.
        profileCancellable = store.objectWillChange.sink { [weak self] _ in
            self?.objectWillChange.send()
        }
        loadCacheOnly()
    }

    // MARK: - Multi-profile (additive)

    func setDefaultProfile(id: UUID) {
        profileStore.setDefault(id: id)
        applyDefaultURLFromStore()
    }

    @discardableResult
    func addProfile(name: String, baseURLString: String, makeDefault: Bool = true) -> ConnectionProfile {
        let profile = profileStore.add(name: name, baseURLString: baseURLString, makeDefault: makeDefault)
        if makeDefault || profile.isDefault {
            applyDefaultURLFromStore()
        }
        return profile
    }

    func removeProfile(id: UUID) {
        profileStore.remove(id: id)
        applyDefaultURLFromStore()
    }

    func updateProfile(id: UUID, name: String? = nil, baseURLString: String? = nil) {
        profileStore.update(id: id, name: name, baseURLString: baseURLString)
        if profileStore.defaultProfile?.id == id {
            applyDefaultURLFromStore()
        }
    }

    private func applyDefaultURLFromStore() {
        let url = profileStore.defaultBaseURLString
        guard url != baseURLString else { return }
        isApplyingProfileURL = true
        baseURLString = url
        isApplyingProfileURL = false
    }

    // MARK: - Polling / cache / sync (unchanged signatures)

    func startPolling() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 20, repeats: true) { [weak self] _ in
            Task { @MainActor in
                await self?.sync()
            }
        }
    }

    func stopPolling() {
        timer?.invalidate()
        timer = nil
    }

    func loadCacheOnly() {
        guard let env = cache.load() else {
            freshness = .empty
            return
        }
        lastSuccessSyncAt = env.cachedAt
        applyEnvelope(env, preferredURL: baseURLString)
    }

    func clearCache() {
        cache.clear()
        snapshot = nil
        lastSuccessSyncAt = nil
        freshness = .empty
    }

    func sync() async {
        guard !isSyncing else { return }
        isSyncing = true
        defer { isSyncing = false }

        guard let base = PrivateHostPolicy.normalizeBaseURL(baseURLString) else {
            lastError = DeskAPIError.cleartextDenied.localizedDescription
            loadCacheOnly()
            return
        }

        // Mismatch check before network
        if let env = cache.load(), !urlsMatch(env.sourceBaseURL, base.absoluteString) {
            // still try network; if fail, show staleMismatch
        }

        do {
            try await client.health(baseURL: base)
            let (raw, snap) = try await client.fetchDesk(baseURL: base)
            do {
                try cache.save(deskObject: raw, sourceBaseURL: base.absoluteString)
                let when = ISO8601DateFormatter().string(from: Date())
                lastSuccessSyncAt = when
                profileStore.markDefaultSuccess(at: when)
                snapshot = snap
                freshness = .fresh
                lastError = nil
            } catch {
                snapshot = snap
                freshness = .liveNotPersisted
                lastError = "Live data but cache write failed: \(error.localizedDescription)"
            }
        } catch {
            lastError = error.localizedDescription
            if let env = cache.load() {
                applyEnvelope(env, preferredURL: base.absoluteString)
            } else {
                freshness = .empty
            }
        }
    }

    private func applyEnvelope(_ env: CacheEnvelope, preferredURL: String) {
        let data = try? JSONSerialization.data(withJSONObject: env.desk.toFoundation())
        if let data, let snap = try? JSONDecoder().decode(DeskSnapshot.self, from: data) {
            snapshot = snap
        }
        if urlsMatch(env.sourceBaseURL, preferredURL) {
            freshness = .stale
        } else {
            freshness = .staleMismatch
        }
        lastSuccessSyncAt = env.cachedAt
    }

    private func urlsMatch(_ a: String, _ b: String) -> Bool {
        let na = PrivateHostPolicy.normalizeBaseURL(a)?.absoluteString
        let nb = PrivateHostPolicy.normalizeBaseURL(b)?.absoluteString
        return na != nil && na == nb
    }
}
