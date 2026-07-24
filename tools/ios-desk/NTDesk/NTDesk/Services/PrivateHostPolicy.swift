import Foundation

enum PrivateHostPolicy {
    /// Allow cleartext http only for private / Tailscale / loopback hosts.
    static func isCleartextAllowed(host: String) -> Bool {
        let h = host.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        if h.isEmpty { return false }
        if h == "localhost" || h.hasSuffix(".local") || h.contains(".ts.net") {
            return true
        }
        // IPv6 loopback / ULA rough check
        if h == "::1" || h.hasPrefix("fc") || h.hasPrefix("fd") {
            return true
        }
        let parts = h.split(separator: ".").compactMap { Int($0) }
        guard parts.count == 4, parts.allSatisfy({ (0...255).contains($0) }) else {
            return false
        }
        let a = parts[0], b = parts[1]
        // loopback 127.0.0.0/8
        if a == 127 { return true }
        // RFC1918
        if a == 10 { return true }
        if a == 192 && b == 168 { return true }
        if a == 172 && (16...31).contains(b) { return true }
        // link-local 169.254.0.0/16
        if a == 169 && b == 254 { return true }
        // Tailscale CGNAT 100.64.0.0/10 → 100.64.0.0 – 100.127.255.255
        if a == 100 && (64...127).contains(b) { return true }
        return false
    }

    static func normalizeBaseURL(_ raw: String) -> URL? {
        var s = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if s.isEmpty { return nil }
        if !s.contains("://") {
            s = "http://\(s)"
        }
        guard var comp = URLComponents(string: s) else { return nil }
        if comp.scheme == nil { comp.scheme = "http" }
        // strip trailing slash path noise
        if comp.path.hasSuffix("/") && comp.path.count > 1 {
            comp.path = String(comp.path.dropLast())
        }
        if comp.path == "/" { comp.path = "" }
        guard let url = comp.url, let host = comp.host else { return nil }
        if comp.scheme == "http" && !isCleartextAllowed(host: host) {
            return nil
        }
        return url
    }
}
