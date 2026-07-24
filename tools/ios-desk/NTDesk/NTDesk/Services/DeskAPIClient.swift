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
    var session: URLSession = {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = 8
        cfg.timeoutIntervalForResource = 12
        cfg.waitsForConnectivity = false
        return URLSession(configuration: cfg)
    }()

    func health(baseURL: URL) async throws {
        let url = baseURL.appendingPathComponent("api/health")
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        let (_, resp) = try await session.data(for: req)
        guard let http = resp as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw DeskAPIError.http((resp as? HTTPURLResponse)?.statusCode ?? -1)
        }
    }

    /// Returns raw JSON object as Foundation dictionary (for cache) + decoded UI model.
    func fetchDesk(baseURL: URL) async throws -> (raw: [String: Any], snap: DeskSnapshot) {
        let url = baseURL.appendingPathComponent("api/desk")
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        let (data, resp) = try await session.data(for: req)
        guard let http = resp as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw DeskAPIError.http((resp as? HTTPURLResponse)?.statusCode ?? -1)
        }
        guard
            let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            throw DeskAPIError.notJSON
        }
        // schema_version required for cache write — missing fail closed
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
