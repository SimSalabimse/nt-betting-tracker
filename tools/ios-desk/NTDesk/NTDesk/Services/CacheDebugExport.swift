import Foundation

enum CacheDebugExportError: Error, LocalizedError {
    case noCache
    case zipFailed(String)

    var errorDescription: String? {
        switch self {
        case .noCache: return "No cache file on device"
        case .zipFailed(let m): return m
        }
    }
}

/// Builds a zip of on-device desk cache + small metadata for debugging sync issues.
enum CacheDebugExport {
    /// Returns a temporary .zip URL ready for share sheet.
    @MainActor
    static func buildZip(
        cache: CacheStore = CacheStore(),
        sync: SyncService
    ) throws -> URL {
        let envelope = cache.load()
        let cacheURL = CacheStore.defaultCacheFileURL
        guard FileManager.default.fileExists(atPath: cacheURL.path) || envelope != nil else {
            throw CacheDebugExportError.noCache
        }

        let stamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let work = FileManager.default.temporaryDirectory
            .appendingPathComponent("ntdesk-debug-\(stamp)", isDirectory: true)
        try? FileManager.default.removeItem(at: work)
        try FileManager.default.createDirectory(at: work, withIntermediateDirectories: true)

        if FileManager.default.fileExists(atPath: cacheURL.path) {
            try FileManager.default.copyItem(
                at: cacheURL,
                to: work.appendingPathComponent("desk_cache_envelope.json")
            )
        }

        let meta: [String: Any] = [
            "exported_at": ISO8601DateFormatter().string(from: Date()),
            "app_version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "",
            "build": Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "",
            "base_url": sync.baseURLString,
            "freshness": sync.freshness.rawValue,
            "last_success_sync_at": sync.lastSuccessSyncAt as Any,
            "last_error": sync.lastError as Any,
            "last_rtt_ms": sync.lastHealthRTTMs as Any,
            "is_syncing": sync.isSyncing,
            "pending_count": sync.snapshot?.pendingCount as Any,
            "equity_nok": sync.snapshot?.equityNok as Any,
            "freeze": sync.snapshot?.freeze as Any,
            "stopped": sync.snapshot?.stopped as Any,
            "can_bet": sync.snapshot?.canBet as Any,
        ]
        let metaData = try JSONSerialization.data(withJSONObject: meta, options: [.prettyPrinted, .sortedKeys])
        try metaData.write(to: work.appendingPathComponent("debug_meta.json"))

        let zipURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("ntdesk-debug-\(stamp).zip")
        try? FileManager.default.removeItem(at: zipURL)
        try zipDirectory(work, to: zipURL)
        try? FileManager.default.removeItem(at: work)
        return zipURL
    }

    /// Minimal zip (store method) without third-party deps.
    private static func zipDirectory(_ dir: URL, to zipURL: URL) throws {
        let coordinator = NSFileCoordinator()
        var coordError: NSError?
        var writeError: Error?
        coordinator.coordinate(readingItemAt: dir, options: [.forUploading], error: &coordError) { tempZip in
            do {
                if FileManager.default.fileExists(atPath: zipURL.path) {
                    try FileManager.default.removeItem(at: zipURL)
                }
                try FileManager.default.copyItem(at: tempZip, to: zipURL)
            } catch {
                writeError = error
            }
        }
        if let coordError { throw CacheDebugExportError.zipFailed(coordError.localizedDescription) }
        if let writeError { throw writeError }
        guard FileManager.default.fileExists(atPath: zipURL.path) else {
            throw CacheDebugExportError.zipFailed("Zip file was not created")
        }
    }
}
