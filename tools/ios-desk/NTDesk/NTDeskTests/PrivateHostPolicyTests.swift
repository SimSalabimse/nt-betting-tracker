import XCTest
@testable import NTDesk

final class PrivateHostPolicyTests: XCTestCase {

    // MARK: - Allow cleartext

    func testCleartextAllowed_privateAndLoopback() {
        let allowed = [
            "192.168.1.1",
            "10.0.0.2",
            "172.16.0.1",
            "172.31.255.255",
            "127.0.0.1",
            "100.64.0.1",
            "100.64.1.2",
            "100.127.255.255",
            "localhost",
            "host.ts.net",
            "foo.local",
            "device.local",
            "169.254.1.1",
            "::1",
            "fc00::1",
            "fd12:3456:789a::1",
        ]
        for host in allowed {
            XCTAssertTrue(
                PrivateHostPolicy.isCleartextAllowed(host: host),
                "expected allow: \(host)"
            )
        }
    }

    func testCleartextDenied_publicHosts() {
        let denied = [
            "8.8.8.8",
            "1.1.1.1",
            "example.com",
            "google.com",
            "",
            "172.15.0.1",   // just outside 172.16/12
            "172.32.0.1",   // just outside 172.16/12
            "100.63.255.255", // just outside Tailscale CGNAT
            "100.128.0.1",   // just outside Tailscale CGNAT
            "11.0.0.1",
            "192.169.0.1",
        ]
        for host in denied {
            XCTAssertFalse(
                PrivateHostPolicy.isCleartextAllowed(host: host),
                "expected deny: \(host)"
            )
        }
    }

    /// Locks current production match: `host.contains(".ts.net")` (not `hasSuffix`).
    /// Tightening to suffix-only would be a deliberate policy change + regression test.
    func testCleartextAllowed_tsNetContainsSemantics() {
        XCTAssertTrue(PrivateHostPolicy.isCleartextAllowed(host: "my-pc.ts.net"))
        XCTAssertTrue(PrivateHostPolicy.isCleartextAllowed(host: "host.ts.net"))
        // contains (not suffix): middle-token hosts currently match.
        XCTAssertTrue(PrivateHostPolicy.isCleartextAllowed(host: "x.ts.net.y"))
        // No .ts.net substring → deny (public-ish hostname).
        XCTAssertFalse(PrivateHostPolicy.isCleartextAllowed(host: "tsnet.example.com"))
    }

    // MARK: - normalizeBaseURL

    func testNormalizeBaseURL_allowsPrivateHTTP() {
        let url = PrivateHostPolicy.normalizeBaseURL("http://192.168.1.10:8787")
        XCTAssertEqual(url?.absoluteString, "http://192.168.1.10:8787")
    }

    func testNormalizeBaseURL_rejectsPublicHTTP() {
        XCTAssertNil(PrivateHostPolicy.normalizeBaseURL("http://8.8.8.8:8787"))
        XCTAssertNil(PrivateHostPolicy.normalizeBaseURL("http://example.com:8787"))
    }

    func testNormalizeBaseURL_allowsPublicHTTPS() {
        // Public hosts may use https; only cleartext http is gated.
        let url = PrivateHostPolicy.normalizeBaseURL("https://example.com:443")
        XCTAssertEqual(url?.scheme, "https")
        XCTAssertEqual(url?.host, "example.com")
    }

    func testNormalizeBaseURL_addsSchemeWhenMissing() {
        let url = PrivateHostPolicy.normalizeBaseURL("10.0.0.5:8787")
        XCTAssertEqual(url?.scheme, "http")
        XCTAssertEqual(url?.host, "10.0.0.5")
        XCTAssertEqual(url?.port, 8787)
    }

    func testNormalizeBaseURL_emptyAndMalformed() {
        XCTAssertNil(PrivateHostPolicy.normalizeBaseURL(""))
        XCTAssertNil(PrivateHostPolicy.normalizeBaseURL("   "))
        XCTAssertNil(PrivateHostPolicy.normalizeBaseURL("not a url :::"))
    }

    func testNormalizeBaseURL_stripsTrailingSlashPathNoise() {
        let withSlash = PrivateHostPolicy.normalizeBaseURL("http://192.168.1.10:8787/")
        XCTAssertNotNil(withSlash)
        // path "/" is normalized to empty; absoluteString should not require trailing slash
        XCTAssertEqual(withSlash?.path, "")
        XCTAssertEqual(withSlash?.host, "192.168.1.10")
        XCTAssertEqual(withSlash?.port, 8787)

        let withExtra = PrivateHostPolicy.normalizeBaseURL("http://10.0.0.1:8787/api/")
        XCTAssertEqual(withExtra?.path, "/api")
    }
}
