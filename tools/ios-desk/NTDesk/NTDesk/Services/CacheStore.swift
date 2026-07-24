import Foundation

final class CacheStore {
    private let fileURL: URL
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init(filename: String = "desk_cache_envelope.json") {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        let appDir = dir.appendingPathComponent("NTDesk", isDirectory: true)
        try? FileManager.default.createDirectory(at: appDir, withIntermediateDirectories: true)
        fileURL = appDir.appendingPathComponent(filename)
    }

    func load() -> CacheEnvelope? {
        guard let data = try? Data(contentsOf: fileURL) else { return nil }
        return try? decoder.decode(CacheEnvelope.self, from: data)
    }

    /// Persist envelope only after successful validation. Atomic write.
    func save(deskObject: [String: Any], sourceBaseURL: String) throws {
        let envelope = CacheEnvelope(
            envelopeVersion: 1,
            cachedAt: ISO8601DateFormatter().string(from: Date()),
            sourceBaseURL: sourceBaseURL,
            desk: .fromJSONObject(deskObject)
        )
        let data = try encoder.encode(envelope)
        let tmp = fileURL.appendingPathExtension("tmp")
        try data.write(to: tmp, options: .atomic)
        if FileManager.default.fileExists(atPath: fileURL.path) {
            try FileManager.default.removeItem(at: fileURL)
        }
        try FileManager.default.moveItem(at: tmp, to: fileURL)
    }

    func clear() {
        try? FileManager.default.removeItem(at: fileURL)
    }
}
