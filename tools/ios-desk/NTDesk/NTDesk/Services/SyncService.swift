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
    @Published var baseURLString: String {
        didSet {
            UserDefaults.standard.set(baseURLString, forKey: "baseURL")
        }
    }

    private let cache = CacheStore()
    private let client = DeskAPIClient()
    private var timer: Timer?

    init() {
        baseURLString = UserDefaults.standard.string(forKey: "baseURL") ?? "http://127.0.0.1:8787"
        loadCacheOnly()
    }

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
                lastSuccessSyncAt = ISO8601DateFormatter().string(from: Date())
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
