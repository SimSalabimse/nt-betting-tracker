import XCTest
@testable import NTDesk

final class PrivateHostPolicyTests: XCTestCase {

    // MARK: - Allow cleartext

    func testCleartextAllowed_privateAndLoopback() {
        let allowed = [
            "192.168.1.1",
            "10.0.0.2",
            "172.16.0.1",
            "127.0.0.1",
            "100.64.1.2",
            "localhost",
            "host.ts.net",
            "foo.local",
            "169.254.1.1",
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
        ]
        for host in denied {
            XCTAssertFalse(
                PrivateHostPolicy.isCleartextAllowed(host: host),
                "expected deny: \(host)"
            )
        }
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

    func testNormalizeBaseURL_addsSchemeWhenMissing() {
        let url = PrivateHostPolicy.normalizeBaseURL("10.0.0.5:8787")
        XCTAssertEqual(url?.scheme, "http")
        XCTAssertEqual(url?.host, "10.0.0.5")
        XCTAssertEqual(url?.port, 8787)
    }
}
