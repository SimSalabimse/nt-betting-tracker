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
    /// Fast polling path — never hang waiting for the network path to appear.
    private let pollSession: URLSession = {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = 8
        cfg.timeoutIntervalForResource = 12
        cfg.waitsForConnectivity = false
        return URLSession(configuration: cfg)
    }()

    /// Manual Sync only — may wait for connectivity when the user explicitly asked.
    private let manualSession: URLSession = {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = 20
        cfg.timeoutIntervalForResource = 30
        cfg.waitsForConnectivity = true
        return URLSession(configuration: cfg)
    }()

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

    /// Returns raw JSON object as Foundation dictionary (for cache) + decoded UI model.
    func fetchDesk(baseURL: URL, waitForConnectivity: Bool = false) async throws -> (raw: [String: Any], snap: DeskSnapshot) {
        let url = baseURL.appendingPathComponent("api/desk")
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        let (data, resp) = try await session(waitForConnectivity: waitForConnectivity).data(for: req)
        guard let http = resp as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw DeskAPIError.http((resp as? HTTPURLResponse)?.statusCode ?? -1)
        }
        guard
            let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            throw DeskAPIError.notJSON
        }
        let schemaOK: Bool = {
            if let ver = obj["schema_version"] as? Int { return ver >= 1 }
            if let n = obj["schema_version"] as? NSNumber { return n.intValue >= 1 }
            return false
        }()
        guard schemaOK else { throw DeskAPIError.schema }
        let snap = try JSONDecoder().decode(DeskSnapshot.self, from: data)
        return (obj, snap)
    }
}
