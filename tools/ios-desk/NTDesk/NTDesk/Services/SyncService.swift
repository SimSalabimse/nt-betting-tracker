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
    /// UserDefaults key prefix for stored desk ETag (suffix = normalized base URL).
    /// `clearCache` clears only the **current** base URL’s key; other profiles’ etags remain.
    static let etagKeyPrefix = "desk_etag_"
    private static let maxRTTSamples = 5
    /// Throttle chrome RTT publish (D2.1 / C1).
    private static let rttPublishMinInterval: TimeInterval = 30
    private static let rttPublishMinDeltaMs = 10
    private static let rttPublishEveryNthSample = 3

    @Published var baseURLString: String {
        didSet {
            guard !isApplyingProfileURL else { return }
            profileStore.setDefaultBaseURL(baseURLString)
            if oldValue != baseURLString {
                // Never send prior host’s ETag to a new base URL.
                lastETag = nil
                loadStoredETag()
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
    private let client: DeskAPIClient
    private var timer: Timer?
    private var isApplyingProfileURL = false
    /// Separate from `isSyncing` so silent background polls can skip chrome while still serializing work.
    private var syncInFlight = false
    /// User tapped Sync (or probeHealth path) while a silent poll was in flight — run after.
    private var followUpUserSync = false
    private var profileCancellable: AnyCancellable?
    private let defaults: UserDefaults

    /// In-memory ETag for conditional GET (also mirrored to UserDefaults per base URL).
    private(set) var lastETag: String?
    private var lastRTTPublishAt: Date?
    private var rttSamplesSincePublish = 0

    init(
        profileStore: ConnectionProfileStore? = nil,
        cache: CacheStore? = nil,
        defaults: UserDefaults = .standard,
        client: DeskAPIClient = DeskAPIClient()
    ) {
        let store = profileStore ?? ConnectionProfileStore.shared
        self.profileStore = store
        self.cache = cache ?? CacheStore()
        self.defaults = defaults
        self.client = client
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
        loadStoredETag()
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
        lastETag = nil
        loadStoredETag()
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

    /// Battery-friendly adaptive poll (iPhone 14 Pro / 16 Pro).
    /// Fresh & recent → 2 min; fresh but aging → 45s; stale/empty → 25s.
    /// Contact clock (`lastSuccessSyncAt`) is refreshed on 304 / content-unchanged so idle PC stays at 120s.
    /// After a failed fetch, freshness becomes `.stale` → 25s (intentional faster retry); contact clock is preserved for UI.
    var pollIntervalSeconds: TimeInterval {
        if !network.isSatisfied { return 90 }
        if freshness == .fresh, let age = lastSuccessAgeSeconds {
            if age < 120 { return 120 }
            if age < 300 { return 45 }
        }
        return 25
    }

    private var lastSuccessAgeSeconds: TimeInterval? {
        guard let iso = lastSuccessSyncAt, let d = DeskFormatters.parseISO8601(iso) else { return nil }
        return Date().timeIntervalSince(d)
    }

    private func scheduleNextPoll(after seconds: TimeInterval) {
        timer?.invalidate()
        let t = Timer(timeInterval: seconds, repeats: false) { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                // Background polls: desk-only (RTT from desk), skip when offline.
                await self.sync(waitForConnectivity: false, probeHealth: false)
                self.scheduleNextPoll(after: self.pollIntervalSeconds)
            }
        }
        // Common modes: fire while scrolling lists/charts (otherwise polls stall).
        RunLoop.main.add(t, forMode: .common)
        timer = t
    }

    func loadCacheOnly() {
        guard let env = cache.load() else {
            snapshot = nil
            lastSuccessSyncAt = nil
            freshness = .empty
            return
        }
        // Cold start: no live contact yet — seed from cache wall clock.
        applyEnvelope(env, preferredURL: baseURLString, updateContactFromCache: true)
    }

    func clearCache() {
        cache.clear()
        snapshot = nil
        lastSuccessSyncAt = nil
        lastHealthRTTMs = nil
        serverApiVersion = nil
        apiCompatibility = .unknown
        freshness = .empty
        // Clears ETag for the **current** base URL only (other profiles keep theirs).
        clearETagStorage()
    }

    /// True when live (or cached) desk came from an old mobile-view package.
    var isServerAPIOutdated: Bool {
        apiCompatibility.isOutdated
    }

    func sync() async {
        await sync(waitForConnectivity: true, probeHealth: true)
    }

    /// - Parameters:
    ///   - waitForConnectivity: user-driven Sync may wait for path.
    ///   - probeHealth: when true, also hit `/api/health` (manual sync / first open).
    ///     Background polls set false and take RTT from the desk request only (half the
    ///     round-trips on the radio — matters on iPhone 14 Pro + LAN).
    func sync(waitForConnectivity: Bool, probeHealth: Bool = true) async {
        // Silent background poll: no isSyncing chrome / ProgressView spinner.
        let silent = !waitForConnectivity && !probeHealth

        if syncInFlight {
            // Coalesce: user Sync during silent poll → run a full sync after in-flight work.
            if !silent {
                followUpUserSync = true
            }
            return
        }

        // Don't burn battery probing when the path is down — show cache.
        if !waitForConnectivity, !network.isSatisfied {
            if snapshot == nil { loadCacheOnly() }
            return
        }

        syncInFlight = true
        if !silent { isSyncing = true }
        defer {
            syncInFlight = false
            if !silent { isSyncing = false }
            if followUpUserSync {
                followUpUserSync = false
                Task { @MainActor in
                    await self.sync(waitForConnectivity: true, probeHealth: true)
                }
            }
        }

        let syncedProfileID = profileStore.defaultProfile?.id
        let preferredURL = baseURLString

        guard let base = PrivateHostPolicy.normalizeBaseURL(preferredURL) else {
            lastError = DeskAPIError.cleartextDenied.localizedDescription
            loadCacheOnly()
            if waitForConnectivity { Haptics.error() }
            return
        }

        do {
            if probeHealth {
                let health = try await client.health(baseURL: base, waitForConnectivity: waitForConnectivity)
                recordRTT(health.rttMs)
                noteServerAPIVersion(health.apiVersion)
            }

            // Conditional GET only when local snapshot is trusted for this host.
            // On staleMismatch / empty: force full body (never 304-promote foreign cache).
            let ifNoneMatch = etagEligibleForConditionalGet ? lastETag : nil

            let fetch = try await client.fetchDesk(
                baseURL: base,
                waitForConnectivity: waitForConnectivity,
                ifNoneMatch: ifNoneMatch
            )
            // Desk RTT always recorded (poll path has no separate health).
            if !probeHealth {
                recordRTT(fetch.rttMs)
            }

            switch fetch.outcome {
            case .notModified:
                // 304 with host-mismatched / empty snapshot must not become .fresh.
                if !etagEligibleForConditionalGet {
                    // Should be rare (we omit If-None-Match); keep mismatch, no false-fresh.
                    lastError = nil
                    return
                }
                // D2.1 contact path — no snapshot / cache mutation.
                markContactSuccess(responseETag: fetch.etag, promoteFresh: true)
                if waitForConnectivity { Haptics.success() }
                return

            case .applied:
                guard let snap = fetch.snap, let raw = fetch.raw else {
                    throw DeskAPIError.schema
                }
                // Prefer desk body api_version; missing → outdated package.
                noteServerAPIVersion(snap.apiVersion)

                // Prefer content_hash over generated_at for skip when present.
                if isContentUnchanged(incoming: snap) {
                    markContactSuccess(responseETag: fetch.etag, promoteFresh: true)
                    if waitForConnectivity { Haptics.success() }
                    return
                }

                let sourceURL = base.absoluteString
                // Cache write off the main actor (file I/O).
                let cacheStore = cache
                do {
                    try await Task.detached(priority: .utility) {
                        try cacheStore.save(deskObject: raw, sourceBaseURL: sourceURL)
                    }.value
                    markContactSuccess(responseETag: fetch.etag, promoteFresh: true)
                    if let syncedProfileID {
                        profileStore.markSuccess(profileID: syncedProfileID, at: lastSuccessSyncAt ?? "")
                    }
                    rememberLastKnownGood(sourceURL)
                    if snapshot != snap {
                        snapshot = snap
                    }
                    freshness = .fresh
                    lastError = nil
                    if waitForConnectivity { Haptics.success() }
                } catch {
                    // Live body applied — still refresh contact clock + ETag; no disk envelope.
                    markContactSuccess(responseETag: fetch.etag, promoteFresh: false)
                    if snapshot != snap {
                        snapshot = snap
                    }
                    freshness = .liveNotPersisted
                    lastError = "Live data but cache write failed: \(error.localizedDescription)"
                    if waitForConnectivity { Haptics.warning() }
                }
            }
        } catch {
            lastError = error.localizedDescription
            // Preserve contact clock (lastSuccessSyncAt). Cache wall must not stomp a
            // recently refreshed live contact — that regressed adaptive-poll honesty.
            if let env = cache.load() {
                applyEnvelope(env, preferredURL: base.absoluteString, updateContactFromCache: false)
            } else if snapshot == nil {
                freshness = .empty
            }
            // Intentional: freshness → .stale (or mismatch) so pollInterval drops to 25s for
            // faster retry after failure; lastSuccessSyncAt stays at last real contact.
            if waitForConnectivity { Haptics.error() }
        }
    }

    // MARK: - Host affinity / conditional GET eligibility

    /// Snapshot is trusted for the active base URL (same-host cache or live).
    /// Not for `staleMismatch` (foreign host’s desk) or `empty`.
    private var etagEligibleForConditionalGet: Bool {
        switch freshness {
        case .fresh, .stale, .liveNotPersisted:
            return snapshot != nil
        case .staleMismatch, .empty:
            return false
        }
    }

    // MARK: - Content identity (skip)

    /// Prefer `content_hash` when present; else `generated_at`. Requires freshness `.fresh`.
    func isContentUnchanged(incoming: DeskSnapshot) -> Bool {
        Self.isContentUnchanged(incoming: incoming, applied: snapshot, freshness: freshness)
    }

    /// Pure helper for tests / skip path (nonisolated — no actor state).
    /// Prefer hash when both sides have one; if prior hash is empty, fall through to `generated_at`.
    nonisolated static func isContentUnchanged(
        incoming: DeskSnapshot,
        applied: DeskSnapshot?,
        freshness: Freshness
    ) -> Bool {
        guard freshness == .fresh, applied != nil else { return false }
        if let h = incoming.contentHash?.trimmingCharacters(in: .whitespacesAndNewlines), !h.isEmpty {
            let prior = applied?.contentHash?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if !prior.isEmpty {
                return h == prior
            }
            // Prior missing hash (old cache / pre-1.2.0 body) → fall through to generated_at.
        }
        if let g = incoming.generatedAt, !g.isEmpty {
            return g == applied?.generatedAt
        }
        return false
    }

    // MARK: - Contact clock + ETag

    /// Record successful desk contact + optional ETag store (304, content-unchanged, or applied).
    private func markContactSuccess(responseETag: String?, promoteFresh: Bool) {
        lastError = nil
        let when = ISO8601DateFormatter().string(from: Date())
        lastSuccessSyncAt = when
        if promoteFresh, snapshot != nil {
            // Never promote host-mismatched / empty snapshot to .fresh on 304.
            switch freshness {
            case .staleMismatch, .empty:
                break
            case .fresh, .stale, .liveNotPersisted:
                freshness = .fresh
            }
        }
        // 304 without ETag response: keep prior. New ETag: store.
        if let etag = responseETag?.trimmingCharacters(in: .whitespacesAndNewlines), !etag.isEmpty {
            storeETag(etag)
        }
    }

    static func etagDefaultsKey(for baseURLString: String) -> String {
        let norm = PrivateHostPolicy.normalizeBaseURL(baseURLString)?.absoluteString
            ?? baseURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        return etagKeyPrefix + norm
    }

    private func loadStoredETag() {
        let key = Self.etagDefaultsKey(for: baseURLString)
        lastETag = defaults.string(forKey: key)
    }

    private func storeETag(_ etag: String) {
        lastETag = etag
        defaults.set(etag, forKey: Self.etagDefaultsKey(for: baseURLString))
    }

    private func clearETagStorage() {
        lastETag = nil
        defaults.removeObject(forKey: Self.etagDefaultsKey(for: baseURLString))
    }

    private func recordRTT(_ ms: Int) {
        var next = rttSamplesMs
        next.append(ms)
        if next.count > Self.maxRTTSamples {
            next = Array(next.suffix(Self.maxRTTSamples))
        }
        rttSamplesMs = next
        if let data = try? JSONEncoder().encode(next) {
            defaults.set(data, forKey: Self.rttSamplesKey)
        }

        rttSamplesSincePublish += 1
        let shouldPublish: Bool
        if lastHealthRTTMs == nil {
            shouldPublish = true
        } else if abs(ms - (lastHealthRTTMs ?? 0)) >= Self.rttPublishMinDeltaMs {
            shouldPublish = true
        } else if rttSamplesSincePublish >= Self.rttPublishEveryNthSample {
            shouldPublish = true
        } else if let t = lastRTTPublishAt, Date().timeIntervalSince(t) >= Self.rttPublishMinInterval {
            shouldPublish = true
        } else if lastRTTPublishAt == nil {
            shouldPublish = true
        } else {
            shouldPublish = false
        }

        if shouldPublish {
            lastHealthRTTMs = ms
            lastRTTPublishAt = Date()
            rttSamplesSincePublish = 0
        }
    }

    private func rememberLastKnownGood(_ url: String) {
        lastKnownGoodBaseURL = url
        defaults.set(url, forKey: Self.lastKnownGoodURLKey)
    }

    /// Apply disk envelope for UI. Contact clock is the live success clock — only seed from
    /// `cached_at` when `updateContactFromCache` is true (cold load). Error fallback must pass false.
    private func applyEnvelope(
        _ env: CacheEnvelope,
        preferredURL: String,
        updateContactFromCache: Bool
    ) {
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
        if updateContactFromCache {
            lastSuccessSyncAt = env.cachedAt
        }
        // else: preserve existing lastSuccessSyncAt (contact clock honesty)
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
