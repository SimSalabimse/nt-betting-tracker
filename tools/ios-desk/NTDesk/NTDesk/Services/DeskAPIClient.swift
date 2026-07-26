import Foundation

enum DeskAPIError: Error, LocalizedError {
    case badURL
    case http(Int)
    case notJSON
    case schema
    case cleartextDenied

    var errorDescription: String? {
        switch self {
        case .badURL: return "Invalid base URL"
        case .http(let c): return "HTTP \(c)"
        case .notJSON: return "Response is not JSON object"
        case .schema: return "Missing or invalid schema_version"
        case .cleartextDenied: return "Host not allowed for cleartext HTTP"
        }
    }
}

struct DeskAPIClient {
    /// Shared decoder (thread-safe for concurrent use with separate instances is fine;
    /// we keep one for this client used from the main actor / short tasks).
    private let decoder = JSONDecoder()

    private let pollSession: URLSession
    private let manualSession: URLSession

    init(pollSession: URLSession? = nil, manualSession: URLSession? = nil) {
        self.pollSession = pollSession ?? Self.makePollSession()
        self.manualSession = manualSession ?? Self.makeManualSession()
    }

    /// Fast polling path — never hang waiting for the network path to appear.
    private static func makePollSession() -> URLSession {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = 8
        cfg.timeoutIntervalForResource = 12
        cfg.waitsForConnectivity = false
        cfg.httpMaximumConnectionsPerHost = 2
        cfg.requestCachePolicy = .reloadIgnoringLocalCacheData
        cfg.urlCache = nil
        // Slightly friendlier on cellular / constrained paths (iPhone 14/16).
        cfg.allowsExpensiveNetworkAccess = true
        cfg.allowsConstrainedNetworkAccess = true
        return URLSession(configuration: cfg)
    }

    /// Manual Sync only — may wait for connectivity when the user explicitly asked.
    private static func makeManualSession() -> URLSession {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = 18
        cfg.timeoutIntervalForResource = 28
        cfg.waitsForConnectivity = true
        cfg.httpMaximumConnectionsPerHost = 2
        cfg.requestCachePolicy = .reloadIgnoringLocalCacheData
        cfg.urlCache = nil
        return URLSession(configuration: cfg)
    }

    private func session(waitForConnectivity: Bool) -> URLSession {
        waitForConnectivity ? manualSession : pollSession
    }

    /// Result of `GET /api/health` (RTT + optional version identity).
    struct HealthProbe: Sendable {
        var rttMs: Int
        /// Present on mobile-view ≥ 1.1.0.
        var apiVersion: String?
        var schemaVersion: Int?
        var service: String?
    }

    /// Desk fetch with RTT (so polls can skip a separate `/api/health` round-trip).
    struct DeskFetch {
        enum Outcome: Equatable {
            /// HTTP 304 — empty body; keep applied snapshot.
            case notModified
            /// HTTP 200 with body. SyncService may reclassify as content-unchanged.
            case applied
        }

        var outcome: Outcome
        var raw: [String: Any]?
        var snap: DeskSnapshot?
        var rttMs: Int
        /// Response `ETag` when present (also on 304).
        var etag: String?
    }

    /// Health probe. Returns RTT + `api_version` when the body includes it.
    @discardableResult
    func health(baseURL: URL, waitForConnectivity: Bool = false) async throws -> HealthProbe {
        let url = baseURL.appendingPathComponent("api/health")
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        let start = CFAbsoluteTimeGetCurrent()
        let (data, resp) = try await session(waitForConnectivity: waitForConnectivity).data(for: req)
        let rttMs = Int(((CFAbsoluteTimeGetCurrent() - start) * 1000.0).rounded())
        guard let http = resp as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw DeskAPIError.http((resp as? HTTPURLResponse)?.statusCode ?? -1)
        }
        var apiVersion: String?
        var schemaVersion: Int?
        var service: String?
        // Prefer ok==true when JSON body present (discovery contract); accept empty 200 for older servers.
        if let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            if let ok = obj["ok"] as? Bool, !ok {
                throw DeskAPIError.http(http.statusCode)
            }
            if let n = obj["ok"] as? NSNumber, !n.boolValue {
                throw DeskAPIError.http(http.statusCode)
            }
            apiVersion = obj["api_version"] as? String
            if apiVersion == nil, let n = obj["api_version"] as? NSNumber {
                apiVersion = n.stringValue
            }
            if let s = obj["schema_version"] as? Int {
                schemaVersion = s
            } else if let n = obj["schema_version"] as? NSNumber {
                schemaVersion = n.intValue
            }
            service = obj["service"] as? String
        }
        return HealthProbe(
            rttMs: max(0, rttMs),
            apiVersion: apiVersion,
            schemaVersion: schemaVersion,
            service: service
        )
    }

    /// Returns outcome + optional raw/snap + RTT. **304 does not throw.**
    /// - Parameter ifNoneMatch: prior ETag for conditional GET (`If-None-Match`).
    func fetchDesk(
        baseURL: URL,
        waitForConnectivity: Bool = false,
        ifNoneMatch: String? = nil
    ) async throws -> DeskFetch {
        let url = baseURL.appendingPathComponent("api/desk")
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.cachePolicy = .reloadIgnoringLocalCacheData
        if let etag = ifNoneMatch?.trimmingCharacters(in: .whitespacesAndNewlines), !etag.isEmpty {
            req.setValue(etag, forHTTPHeaderField: "If-None-Match")
        }
        let start = CFAbsoluteTimeGetCurrent()
        let (data, resp) = try await session(waitForConnectivity: waitForConnectivity).data(for: req)
        let rttMs = Int(((CFAbsoluteTimeGetCurrent() - start) * 1000.0).rounded())
        guard let http = resp as? HTTPURLResponse else {
            throw DeskAPIError.http(-1)
        }

        let responseETag = http.value(forHTTPHeaderField: "ETag")

        // 304 Not Modified — success path (must not throw DeskAPIError.http).
        if http.statusCode == 304 {
            return DeskFetch(
                outcome: .notModified,
                raw: nil,
                snap: nil,
                rttMs: max(0, rttMs),
                etag: responseETag
            )
        }

        guard (200...299).contains(http.statusCode) else {
            throw DeskAPIError.http(http.statusCode)
        }

        // Decode typed model first (one JSON pass via Decoder).
        let snap: DeskSnapshot
        do {
            snap = try decoder.decode(DeskSnapshot.self, from: data)
        } catch {
            throw DeskAPIError.schema
        }
        guard (snap.schemaVersion ?? 0) >= 1 else { throw DeskAPIError.schema }
        // Second pass only for cache envelope (AnyJSON). Avoided on schema failure.
        guard let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw DeskAPIError.notJSON
        }
        return DeskFetch(
            outcome: .applied,
            raw: obj,
            snap: snap,
            rttMs: max(0, rttMs),
            etag: responseETag
        )
    }
}
