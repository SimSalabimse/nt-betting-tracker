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
    /// Last successful health RTT in milliseconds.
    @Published var lastHealthRTTMs: Int?
    /// Rolling RTT samples (newest last), max 5.
    @Published private(set) var rttSamplesMs: [Int] = []
    /// Last URL that completed a full desk sync successfully (UserDefaults-backed).
    @Published private(set) var lastKnownGoodBaseURL: String?
    /// Last `api_version` from live health or desk (nil if server omitted it).
    @Published private(set) var serverApiVersion: String?
    /// Whether the connected PC mobile-view is new enough for this app.
    @Published private(set) var apiCompatibility: MobileAPICompatibility = .unknown

    static let lastKnownGoodURLKey = "last_known_good_base_url"
    static let rttSamplesKey = "health_rtt_samples_ms"
    private static let maxRTTSamples = 5

    @Published var baseURLString: String {
        didSet {
            guard !isApplyingProfileURL else { return }
            profileStore.setDefaultBaseURL(baseURLString)
            if oldValue != baseURLString {
                loadCacheOnly()
            }
        }
    }

    var profiles: [ConnectionProfile] {
        profileStore.profiles
    }

    /// True when we can offer “use last known good PC” (different from current + non-empty).
    var canRestoreLastKnownGood: Bool {
        guard let good = lastKnownGoodBaseURL, !good.isEmpty else { return false }
        return PrivateHostPolicy.normalizeBaseURL(good)?.absoluteString
            != PrivateHostPolicy.normalizeBaseURL(baseURLString)?.absoluteString
    }

    let profileStore: ConnectionProfileStore
    let network = NetworkPathMonitor.shared

    private let cache: CacheStore
    private let client = DeskAPIClient()
    private var timer: Timer?
    private var isApplyingProfileURL = false
    private var profileCancellable: AnyCancellable?
    private let defaults: UserDefaults

    init(
        profileStore: ConnectionProfileStore? = nil,
        cache: CacheStore? = nil,
        defaults: UserDefaults = .standard
    ) {
        let store = profileStore ?? ConnectionProfileStore.shared
        self.profileStore = store
        self.cache = cache ?? CacheStore()
        self.defaults = defaults
        store.migrateFromLegacyBaseURLIfNeeded()
        self.baseURLString = store.defaultBaseURLString
        self.lastKnownGoodBaseURL = defaults.string(forKey: Self.lastKnownGoodURLKey)
        if let data = defaults.data(forKey: Self.rttSamplesKey),
           let arr = try? JSONDecoder().decode([Int].self, from: data) {
            rttSamplesMs = Array(arr.suffix(Self.maxRTTSamples))
        }
        profileCancellable = store.objectWillChange.sink { [weak self] _ in
            self?.objectWillChange.send()
        }
        Haptics.prepare()
        loadCacheOnly()
    }

    // MARK: - Multi-profile

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

    /// Switch active URL to the last PC that fully synced (creates/updates default profile).
    func restoreLastKnownGoodBaseURL() {
        guard let good = lastKnownGoodBaseURL, !good.isEmpty else { return }
        profileStore.setDefaultBaseURL(good)
        applyDefaultURLFromStore()
        Haptics.mediumImpact()
    }

    private func applyDefaultURLFromStore() {
        let url = profileStore.defaultBaseURLString
        guard url != baseURLString else { return }
        isApplyingProfileURL = true
        baseURLString = url
        isApplyingProfileURL = false
        loadCacheOnly()
    }

    // MARK: - Polling (adaptive when fresh)

    func startPolling() {
        scheduleNextPoll(after: pollIntervalSeconds)
    }

    func stopPolling() {
        timer?.invalidate()
        timer = nil
    }

    /// 60s while still fresh & recent; else 20s.
    var pollIntervalSeconds: TimeInterval {
        if freshness == .fresh, let age = lastSuccessAgeSeconds, age < 90 {
            return 60
        }
        return 20
    }

    private var lastSuccessAgeSeconds: TimeInterval? {
        guard let iso = lastSuccessSyncAt, let d = DeskFormatters.parseISO8601(iso) else { return nil }
        return Date().timeIntervalSince(d)
    }

    private func scheduleNextPoll(after seconds: TimeInterval) {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: seconds, repeats: false) { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                await self.sync(waitForConnectivity: false)
                self.scheduleNextPoll(after: self.pollIntervalSeconds)
            }
        }
    }

    func loadCacheOnly() {
        guard let env = cache.load() else {
            snapshot = nil
            lastSuccessSyncAt = nil
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
        lastHealthRTTMs = nil
        serverApiVersion = nil
        apiCompatibility = .unknown
        freshness = .empty
    }

    /// True when live (or cached) desk came from an old mobile-view package.
    var isServerAPIOutdated: Bool {
        apiCompatibility.isOutdated
    }

    func sync() async {
        await sync(waitForConnectivity: true)
    }

    func sync(waitForConnectivity: Bool) async {
        guard !isSyncing else { return }
        isSyncing = true
        defer { isSyncing = false }

        let syncedProfileID = profileStore.defaultProfile?.id
        let preferredURL = baseURLString

        guard let base = PrivateHostPolicy.normalizeBaseURL(preferredURL) else {
            lastError = DeskAPIError.cleartextDenied.localizedDescription
            loadCacheOnly()
            if waitForConnectivity { Haptics.error() }
            return
        }

        do {
            let health = try await client.health(baseURL: base, waitForConnectivity: waitForConnectivity)
            recordRTT(health.rttMs)
            // Prefer health.api_version; desk body is a second source (same package).
            noteServerAPIVersion(health.apiVersion)
            let (raw, snap) = try await client.fetchDesk(baseURL: base, waitForConnectivity: waitForConnectivity)
            if let fromDesk = snap.apiVersion {
                noteServerAPIVersion(fromDesk)
            } else if health.apiVersion == nil {
                // Live desk with no version field → definitely pre-1.1 mobile-view.
                noteServerAPIVersion(nil)
            }
            do {
                try cache.save(deskObject: raw, sourceBaseURL: base.absoluteString)
                let when = ISO8601DateFormatter().string(from: Date())
                lastSuccessSyncAt = when
                if let syncedProfileID {
                    profileStore.markSuccess(profileID: syncedProfileID, at: when)
                }
                rememberLastKnownGood(base.absoluteString)
                snapshot = snap
                freshness = .fresh
                lastError = nil
                if waitForConnectivity { Haptics.success() }
            } catch {
                snapshot = snap
                freshness = .liveNotPersisted
                lastError = "Live data but cache write failed: \(error.localizedDescription)"
                if waitForConnectivity { Haptics.warning() }
            }
        } catch {
            lastError = error.localizedDescription
            if let env = cache.load() {
                applyEnvelope(env, preferredURL: base.absoluteString)
            } else {
                freshness = .empty
            }
            if waitForConnectivity { Haptics.error() }
        }
    }

    private func recordRTT(_ ms: Int) {
        lastHealthRTTMs = ms
        var next = rttSamplesMs
        next.append(ms)
        if next.count > Self.maxRTTSamples {
            next = Array(next.suffix(Self.maxRTTSamples))
        }
        rttSamplesMs = next
        if let data = try? JSONEncoder().encode(next) {
            defaults.set(data, forKey: Self.rttSamplesKey)
        }
    }

    private func rememberLastKnownGood(_ url: String) {
        lastKnownGoodBaseURL = url
        defaults.set(url, forKey: Self.lastKnownGoodURLKey)
    }

    private func applyEnvelope(_ env: CacheEnvelope, preferredURL: String) {
        let data = try? JSONSerialization.data(withJSONObject: env.desk.toFoundation())
        if let data, let snap = try? JSONDecoder().decode(DeskSnapshot.self, from: data) {
            snapshot = snap
            // Cached desk still tells us if the last PC was an old API.
            noteServerAPIVersion(snap.apiVersion)
        }
        if urlsMatch(env.sourceBaseURL, preferredURL) {
            freshness = .stale
        } else {
            freshness = .staleMismatch
        }
        lastSuccessSyncAt = env.cachedAt
    }

    private func noteServerAPIVersion(_ version: String?) {
        let trimmed = version?.trimmingCharacters(in: .whitespacesAndNewlines)
        serverApiVersion = (trimmed?.isEmpty == false) ? trimmed : nil
        apiCompatibility = MobileAPICompatibility.evaluate(apiVersion: serverApiVersion)
    }

    private func urlsMatch(_ a: String, _ b: String) -> Bool {
        let na = PrivateHostPolicy.normalizeBaseURL(a)?.absoluteString
        let nb = PrivateHostPolicy.normalizeBaseURL(b)?.absoluteString
        return na != nil && na == nb
    }
}
