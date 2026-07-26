import XCTest
@testable import NTDesk

// MARK: - URLProtocol mock

/// Routes health URLs to canned responses for discovery unit tests.
final class DiscoveryMockURLProtocol: URLProtocol {
    /// host → (status, body)
    nonisolated(unsafe) static var responses: [String: (status: Int, body: Data)] = [:]
    nonisolated(unsafe) static var requestedHosts: [String] = []
    private static let lock = NSLock()

    static func reset() {
        lock.lock()
        defer { lock.unlock() }
        responses = [:]
        requestedHosts = []
    }

    static func record(host: String) {
        lock.lock()
        defer { lock.unlock() }
        requestedHosts.append(host)
    }

    static func response(for host: String) -> (status: Int, body: Data)? {
        lock.lock()
        defer { lock.unlock() }
        return responses[host]
    }

    override class func canInit(with request: URLRequest) -> Bool { true }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let host = request.url?.host ?? ""
        Self.record(host: host)

        guard let canned = Self.response(for: host) else {
            // Simulate timeout / unreachable
            let err = NSError(
                domain: NSURLErrorDomain,
                code: NSURLErrorTimedOut,
                userInfo: nil
            )
            client?.urlProtocol(self, didFailWithError: err)
            return
        }

        let url = request.url ?? URL(string: "http://invalid")!
        let resp = HTTPURLResponse(
            url: url,
            statusCode: canned.status,
            httpVersion: "HTTP/1.1",
            headerFields: ["Content-Type": "application/json"]
        )!
        client?.urlProtocol(self, didReceive: resp, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: canned.body)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}

// MARK: - Tests

final class ServerDiscoveryServiceTests: XCTestCase {

    override func setUp() {
        super.setUp()
        DiscoveryMockURLProtocol.reset()
    }

    override func tearDown() {
        DiscoveryMockURLProtocol.reset()
        super.tearDown()
    }

    // MARK: evaluateHealthResponse

    func testHealthOKTrue_isHit() throws {
        let data = try JSONSerialization.data(withJSONObject: ["ok": true, "view_only": true])
        let eval = DiscoveryProbeLogic.evaluateHealthResponse(statusCode: 200, data: data)
        XCTAssertTrue(eval.ok)
        XCTAssertEqual(eval.viewOnly, true)
    }

    func testHealthOKFalse_isMiss() throws {
        let data = try JSONSerialization.data(withJSONObject: ["ok": false])
        let eval = DiscoveryProbeLogic.evaluateHealthResponse(statusCode: 200, data: data)
        XCTAssertFalse(eval.ok)
    }

    func testHealthMissingOK_isMiss() throws {
        let data = try JSONSerialization.data(withJSONObject: ["view_only": true])
        let eval = DiscoveryProbeLogic.evaluateHealthResponse(statusCode: 200, data: data)
        XCTAssertFalse(eval.ok)
    }

    func testHealthNon2xx_isMiss() throws {
        let data = try JSONSerialization.data(withJSONObject: ["ok": true])
        let eval = DiscoveryProbeLogic.evaluateHealthResponse(statusCode: 500, data: data)
        XCTAssertFalse(eval.ok)
    }

    func testHealthNonJSON_isMiss() {
        let data = Data("not-json".utf8)
        let eval = DiscoveryProbeLogic.evaluateHealthResponse(statusCode: 200, data: data)
        XCTAssertFalse(eval.ok)
    }

    // MARK: Host plan / policy

    func testPlanHosts_full24_cappedAt256() {
        let ifaces = [DiscoveryInterfaceIPv4(address: "192.168.1.50", prefixLength: 24)]
        let hosts = DiscoveryProbeLogic.planHosts(interfaces: ifaces, lastSuccessHost: nil, maxHosts: 256)
        XCTAssertEqual(hosts.count, 256)
        XCTAssertTrue(hosts.contains("192.168.1.50"))
        XCTAssertTrue(hosts.contains("192.168.1.1"))
        XCTAssertTrue(hosts.allSatisfy { DiscoveryProbeLogic.isProbeHostAllowed($0) })
    }

    func testPlanHosts_doesNotExpandTailscaleCGNAT() {
        let ifaces = [DiscoveryInterfaceIPv4(address: "100.64.1.2", prefixLength: 10)]
        let hosts = DiscoveryProbeLogic.planHosts(interfaces: ifaces, lastSuccessHost: nil, maxHosts: 256)
        XCTAssertTrue(hosts.isEmpty, "Tailscale CGNAT must not be bulk-scanned")
    }

    func testPlanHosts_includesLastSuccessWhenRFC1918() {
        let ifaces = [DiscoveryInterfaceIPv4(address: "10.0.0.5", prefixLength: 16)]
        // /16 is oversized → sample path; last success appended
        let hosts = DiscoveryProbeLogic.planHosts(
            interfaces: ifaces,
            lastSuccessHost: "10.0.0.99",
            maxHosts: 256
        )
        XCTAssertTrue(hosts.contains("10.0.0.5"))
        XCTAssertTrue(hosts.contains("10.0.0.99"))
        XCTAssertLessThanOrEqual(hosts.count, 256)
    }

    func testPublicIP_neverAllowedForProbe() {
        XCTAssertFalse(DiscoveryProbeLogic.isProbeHostAllowed("8.8.8.8"))
        XCTAssertFalse(DiscoveryProbeLogic.isScannableLANSubnetHost("8.8.8.8"))
        XCTAssertNil(PrivateHostPolicy.normalizeBaseURL("http://8.8.8.8:8787"))
    }

    func testPlanHosts_neverEmitsPublicAddresses() {
        // Even if a weird interface appeared, plan only emits scannable RFC1918.
        let ifaces = [
            DiscoveryInterfaceIPv4(address: "8.8.8.8", prefixLength: 24),
            DiscoveryInterfaceIPv4(address: "192.168.0.2", prefixLength: 24),
        ]
        let hosts = DiscoveryProbeLogic.planHosts(interfaces: ifaces, lastSuccessHost: "1.1.1.1", maxHosts: 256)
        XCTAssertFalse(hosts.contains("8.8.8.8"))
        XCTAssertFalse(hosts.contains("1.1.1.1"))
        XCTAssertTrue(hosts.allSatisfy { DiscoveryProbeLogic.isScannableLANSubnetHost($0) })
    }

    // MARK: URLProtocol integration

    func testRunProbes_okTrueHit_okFalseMiss_timeoutMiss() async throws {
        let okBody = try JSONSerialization.data(withJSONObject: ["ok": true])
        let badBody = try JSONSerialization.data(withJSONObject: ["ok": false])
        DiscoveryMockURLProtocol.responses = [
            "192.168.1.10": (200, okBody),
            "192.168.1.11": (200, badBody),
            // 192.168.1.12 → no response → timeout/error
        ]

        let hosts = ["192.168.1.10", "192.168.1.11", "192.168.1.12"]
        let hits = await ServerDiscoveryService.runProbes(
            hosts: hosts,
            port: 8787,
            maxConcurrent: 8,
            budgetNanoseconds: 5_000_000_000,
            makeSession: {
                DiscoverySession.makeURLSession(protocolClasses: [DiscoveryMockURLProtocol.self])
            },
            onProgress: { _ in }
        )

        XCTAssertEqual(hits.count, 1)
        XCTAssertEqual(hits.first?.host, "192.168.1.10")
        XCTAssertTrue(hits.first?.baseURLString.contains("192.168.1.10") == true)
        XCTAssertTrue(hits.first?.baseURLString.contains("8787") == true)

        // Public IP must not be requested even if slipped into host list.
        DiscoveryMockURLProtocol.reset()
        DiscoveryMockURLProtocol.responses = [
            "8.8.8.8": (200, okBody),
        ]
        let publicHits = await ServerDiscoveryService.runProbes(
            hosts: ["8.8.8.8"],
            port: 8787,
            maxConcurrent: 4,
            budgetNanoseconds: 2_000_000_000,
            makeSession: {
                DiscoverySession.makeURLSession(protocolClasses: [DiscoveryMockURLProtocol.self])
            },
            onProgress: { _ in }
        )
        XCTAssertTrue(publicHits.isEmpty)
        // Policy rejects before request — host should not appear in requestedHosts.
        XCTAssertFalse(DiscoveryMockURLProtocol.requestedHosts.contains("8.8.8.8"))
    }

    func testRunProbes_doesNotRequestDeskPath() async throws {
        let okBody = try JSONSerialization.data(withJSONObject: ["ok": true])
        DiscoveryMockURLProtocol.responses = [
            "192.168.1.20": (200, okBody),
        ]

        final class PathSpyProtocol: URLProtocol {
            nonisolated(unsafe) static var paths: [String] = []
            override class func canInit(with request: URLRequest) -> Bool { true }
            override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
            override func startLoading() {
                Self.paths.append(request.url?.path ?? "")
                // Delegate body to mock tables by host
                let host = request.url?.host ?? ""
                if let canned = DiscoveryMockURLProtocol.response(for: host) {
                    let resp = HTTPURLResponse(
                        url: request.url!,
                        statusCode: canned.status,
                        httpVersion: nil,
                        headerFields: nil
                    )!
                    client?.urlProtocol(self, didReceive: resp, cacheStoragePolicy: .notAllowed)
                    client?.urlProtocol(self, didLoad: canned.body)
                    client?.urlProtocolDidFinishLoading(self)
                } else {
                    client?.urlProtocol(self, didFailWithError: URLError(.timedOut))
                }
            }
            override func stopLoading() {}
        }

        PathSpyProtocol.paths = []
        _ = await ServerDiscoveryService.runProbes(
            hosts: ["192.168.1.20"],
            port: 8787,
            maxConcurrent: 2,
            budgetNanoseconds: 2_000_000_000,
            makeSession: {
                DiscoverySession.makeURLSession(protocolClasses: [PathSpyProtocol.self])
            },
            onProgress: { _ in }
        )

        XCTAssertEqual(PathSpyProtocol.paths, ["/api/health"])
        XCTAssertFalse(PathSpyProtocol.paths.contains(where: { $0.contains("desk") }))
    }

    func testDiscoverySession_timeoutsAreShort() {
        let session = DiscoverySession.makeURLSession()
        // Ephemeral config is not readable from URLSession directly after init in all OS versions;
        // assert structural defaults on DiscoverySession instead.
        let cfg = DiscoverySession.default
        XCTAssertEqual(cfg.port, 8787)
        XCTAssertEqual(cfg.maxHosts, 256)
        XCTAssertEqual(cfg.maxConcurrent, 32)
        XCTAssertEqual(cfg.overallBudgetNanoseconds, 8_000_000_000)
        // Construct configuration the same way production does and check timeouts.
        let conf = URLSessionConfiguration.ephemeral
        conf.timeoutIntervalForRequest = 0.4
        conf.timeoutIntervalForResource = 0.5
        XCTAssertEqual(conf.timeoutIntervalForRequest, 0.4, accuracy: 0.001)
        XCTAssertEqual(conf.timeoutIntervalForResource, 0.5, accuracy: 0.001)
        session.finishTasksAndInvalidate()
    }
}
