import Foundation

/// File-backed desk cache. Marked unchecked-Sendable so saves can leave the main actor.
final class CacheStore: @unchecked Sendable {
    private let fileURL: URL
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()
    private let ioLock = NSLock()

    init(filename: String = "desk_cache_envelope.json") {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        let appDir = dir.appendingPathComponent("NTDesk", isDirectory: true)
        try? FileManager.default.createDirectory(at: appDir, withIntermediateDirectories: true)
        fileURL = appDir.appendingPathComponent(filename)
    }

    /// Default production cache path (Application Support / NTDesk / desk_cache_envelope.json).
    static var defaultCacheFileURL: URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        return dir
            .appendingPathComponent("NTDesk", isDirectory: true)
            .appendingPathComponent("desk_cache_envelope.json")
    }

    func load() -> CacheEnvelope? {
        ioLock.lock()
        defer { ioLock.unlock() }
        guard let data = try? Data(contentsOf: fileURL) else { return nil }
        return try? decoder.decode(CacheEnvelope.self, from: data)
    }

    /// Persist envelope only after successful validation. Atomic write.
    /// When app lock is enabled, applies explicit file protection after the replace.
    func save(deskObject: [String: Any], sourceBaseURL: String) throws {
        let envelope = CacheEnvelope(
            envelopeVersion: 1,
            cachedAt: ISO8601DateFormatter().string(from: Date()),
            sourceBaseURL: sourceBaseURL,
            desk: .fromJSONObject(deskObject)
        )
        let data = try encoder.encode(envelope)
        ioLock.lock()
        defer { ioLock.unlock() }
        let tmp = fileURL.appendingPathExtension("tmp")
        try data.write(to: tmp, options: .atomic)
        if FileManager.default.fileExists(atPath: fileURL.path) {
            try FileManager.default.removeItem(at: fileURL)
        }
        try FileManager.default.moveItem(at: tmp, to: fileURL)
        applyFileProtectionIfAppLockEnabled()
    }

    func clear() {
        ioLock.lock()
        defer { ioLock.unlock() }
        try? FileManager.default.removeItem(at: fileURL)
    }

    // MARK: - File protection (optional app lock)

    /// Design: when app lock is on, set protection on the cache file URL after write.
    /// Does not claim "encrypted because Application Support" without this call.
    func applyFileProtectionIfAppLockEnabled() {
        guard Self.isAppLockEnabledInDefaults() else { return }
        Self.applyFileProtection(to: fileURL)
    }

    /// Apply protection to the default cache path if the file exists (e.g. toggle turned on).
    static func applyFileProtectionToDefaultCacheIfPresent() {
        guard isAppLockEnabledInDefaults() else { return }
        let url = defaultCacheFileURL
        guard FileManager.default.fileExists(atPath: url.path) else { return }
        applyFileProtection(to: url)
    }

    static func isAppLockEnabledInDefaults(_ defaults: UserDefaults = .standard) -> Bool {
        // Missing key → false (default OFF). Literal key avoids MainActor isolation on AppLockService.
        defaults.object(forKey: "app_lock_enabled") as? Bool ?? false
    }

    static func applyFileProtection(to fileURL: URL) {
        try? (fileURL as NSURL).setResourceValue(
            URLFileProtection.completeUntilFirstUserAuthentication,
            forKey: .fileProtectionKey
        )
    }
}
