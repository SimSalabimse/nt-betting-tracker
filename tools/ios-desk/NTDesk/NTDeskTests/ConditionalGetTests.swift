import XCTest
@testable import NTDesk

// MARK: - URLProtocol stub

/// In-memory HTTP stub for DeskAPIClient session injection.
final class DeskStubURLProtocol: URLProtocol {
    struct Stub {
        var statusCode: Int
        var headers: [String: String]
        var body: Data
    }

    /// Request path suffix → stub (e.g. "/api/desk").
    static var stubs: [String: Stub] = [:]
    /// Captured request headers per path (last request wins).
    static var lastRequestHeaders: [String: [String: String]] = [:]
    static var requestCount: [String: Int] = [:]

    static func reset() {
        stubs = [:]
        lastRequestHeaders = [:]
        requestCount = [:]
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let path = request.url?.path ?? ""
        Self.requestCount[path, default: 0] += 1
        var headers: [String: String] = [:]
        if let h = request.allHTTPHeaderFields {
            headers = h
        }
        Self.lastRequestHeaders[path] = headers

        guard let stub = Self.stubs[path] ?? Self.stubs.values.first else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }
        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: stub.statusCode,
            httpVersion: "HTTP/1.1",
            headerFields: stub.headers
        )!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        if !stub.body.isEmpty {
            client?.urlProtocol(self, didLoad: stub.body)
        }
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}

// MARK: - Content identity / skip preference

final class ContentUnchangedTests: XCTestCase {

    private func snap(hash: String? = nil, generated: String? = nil) -> DeskSnapshot {
        var s = DeskSnapshot()
        s.schemaVersion = 1
        s.contentHash = hash
        s.generatedAt = generated
        return s
    }

    func testPreferContentHash_sameHash_unchanged() {
        let applied = snap(hash: "aaa111", generated: "2026-01-01T00:00:00Z")
        let incoming = snap(hash: "aaa111", generated: "2026-01-02T00:00:00Z") // gen differs; hash wins
        XCTAssertTrue(
            SyncService.isContentUnchanged(incoming: incoming, applied: applied, freshness: .fresh)
        )
    }

    func testPreferContentHash_differentHash_changedEvenIfGeneratedSame() {
        let applied = snap(hash: "aaa111", generated: "2026-01-01T00:00:00Z")
        let incoming = snap(hash: "bbb222", generated: "2026-01-01T00:00:00Z")
        XCTAssertFalse(
            SyncService.isContentUnchanged(incoming: incoming, applied: applied, freshness: .fresh)
        )
    }

    func testFallbackGeneratedAt_whenHashMissing() {
        let applied = snap(generated: "2026-01-01T00:00:00Z")
        let same = snap(generated: "2026-01-01T00:00:00Z")
        let diff = snap(generated: "2026-01-02T00:00:00Z")
        XCTAssertTrue(SyncService.isContentUnchanged(incoming: same, applied: applied, freshness: .fresh))
        XCTAssertFalse(SyncService.isContentUnchanged(incoming: diff, applied: applied, freshness: .fresh))
    }

    func testNotUnchangedWhenNotFresh() {
        let applied = snap(hash: "aaa111", generated: "t")
        let incoming = snap(hash: "aaa111", generated: "t")
        XCTAssertFalse(SyncService.isContentUnchanged(incoming: incoming, applied: applied, freshness: .stale))
        XCTAssertFalse(SyncService.isContentUnchanged(incoming: incoming, applied: applied, freshness: .empty))
    }

    func testContentHashDecodesFromJSON() throws {
        let json = #"""
        {"schema_version":1,"content_hash":"a1b2c3d4e5f67890","generated_at":"2026-07-26T12:00:00Z"}
        """#
        let desk = try JSONDecoder().decode(DeskSnapshot.self, from: Data(json.utf8))
        XCTAssertEqual(desk.contentHash, "a1b2c3d4e5f67890")
        XCTAssertEqual(desk.generatedAt, "2026-07-26T12:00:00Z")
    }
}

// MARK: - DeskAPIClient 304 / If-None-Match

final class DeskAPIClientConditionalGetTests: XCTestCase {

    private var client: DeskAPIClient!

    override func setUp() {
        super.setUp()
        DeskStubURLProtocol.reset()
        let cfg = URLSessionConfiguration.ephemeral
        cfg.protocolClasses = [DeskStubURLProtocol.self]
        cfg.requestCachePolicy = .reloadIgnoringLocalCacheData
        cfg.urlCache = nil
        let session = URLSession(configuration: cfg)
        client = DeskAPIClient(pollSession: session, manualSession: session)
    }

    override func tearDown() {
        DeskStubURLProtocol.reset()
        client = nil
        super.tearDown()
    }

    private var base: URL { URL(string: "http://192.168.1.10:8787")! }

    private func deskJSON(hash: String = "abc123", generated: String = "2026-07-26T10:00:00Z") -> Data {
        Data("""
        {"schema_version":1,"api_version":"1.2.0","content_hash":"\(hash)","generated_at":"\(generated)","equity_nok":500}
        """.utf8)
    }

    func test304DoesNotThrow_notModifiedOutcome() async throws {
        DeskStubURLProtocol.stubs["/api/desk"] = .init(
            statusCode: 304,
            headers: ["ETag": "\"deadbeefcafebabe\"", "Cache-Control": "private, no-cache"],
            body: Data()
        )
        let fetch = try await client.fetchDesk(baseURL: base, ifNoneMatch: "\"deadbeefcafebabe\"")
        XCTAssertEqual(fetch.outcome, .notModified)
        XCTAssertNil(fetch.snap)
        XCTAssertNil(fetch.raw)
        XCTAssertEqual(fetch.etag, "\"deadbeefcafebabe\"")
        XCTAssertGreaterThanOrEqual(fetch.rttMs, 0)
    }

    func testIfNoneMatchHeaderSent() async throws {
        DeskStubURLProtocol.stubs["/api/desk"] = .init(
            statusCode: 304,
            headers: ["ETag": "\"tag1\""],
            body: Data()
        )
        _ = try await client.fetchDesk(baseURL: base, ifNoneMatch: "\"tag1\"")
        let headers = DeskStubURLProtocol.lastRequestHeaders["/api/desk"] ?? [:]
        // URLSession may normalize header names
        let inm = headers["If-None-Match"] ?? headers["if-none-match"]
        XCTAssertEqual(inm, "\"tag1\"")
    }

    func test200ReturnsAppliedWithBodyAndETag() async throws {
        let body = deskJSON()
        DeskStubURLProtocol.stubs["/api/desk"] = .init(
            statusCode: 200,
            headers: ["ETag": "\"etag200\"", "Content-Type": "application/json"],
            body: body
        )
        let fetch = try await client.fetchDesk(baseURL: base)
        XCTAssertEqual(fetch.outcome, .applied)
        XCTAssertEqual(fetch.snap?.contentHash, "abc123")
        XCTAssertEqual(fetch.snap?.schemaVersion, 1)
        XCTAssertNotNil(fetch.raw)
        XCTAssertEqual(fetch.etag, "\"etag200\"")
    }

    func test4xxThrowsHttp() async {
        DeskStubURLProtocol.stubs["/api/desk"] = .init(
            statusCode: 500,
            headers: [:],
            body: Data("err".utf8)
        )
        do {
            _ = try await client.fetchDesk(baseURL: base)
            XCTFail("expected throw")
        } catch let e as DeskAPIError {
            if case .http(let code) = e {
                XCTAssertEqual(code, 500)
            } else {
                XCTFail("wrong error \(e)")
            }
        } catch {
            XCTFail("unexpected \(error)")
        }
    }

    func testNoIfNoneMatchWhenNil() async throws {
        DeskStubURLProtocol.stubs["/api/desk"] = .init(
            statusCode: 200,
            headers: ["ETag": "\"x\"", "Content-Type": "application/json"],
            body: deskJSON()
        )
        _ = try await client.fetchDesk(baseURL: base, ifNoneMatch: nil)
        let headers = DeskStubURLProtocol.lastRequestHeaders["/api/desk"] ?? [:]
        let inm = headers["If-None-Match"] ?? headers["if-none-match"]
        XCTAssertNil(inm)
    }
}

// MARK: - SyncService contact clock / ETag / silent

@MainActor
final class SyncServiceConditionalGetTests: XCTestCase {

    private var suiteName: String!
    private var defaults: UserDefaults!
    private var cache: CacheStore!
    private var profileStore: ConnectionProfileStore!
    private var client: DeskAPIClient!
    private var sync: SyncService!

    override func setUp() {
        super.setUp()
        DeskStubURLProtocol.reset()
        suiteName = "ntdesk.tests.condget.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        let cacheName = "desk_cache_test_\(UUID().uuidString).json"
        cache = CacheStore(filename: cacheName)
        profileStore = ConnectionProfileStore(defaults: defaults)
        profileStore.migrateFromLegacyBaseURLIfNeeded()
        profileStore.setDefaultBaseURL("http://192.168.1.10:8787")

        let cfg = URLSessionConfiguration.ephemeral
        cfg.protocolClasses = [DeskStubURLProtocol.self]
        cfg.requestCachePolicy = .reloadIgnoringLocalCacheData
        cfg.urlCache = nil
        let session = URLSession(configuration: cfg)
        client = DeskAPIClient(pollSession: session, manualSession: session)

        sync = SyncService(
            profileStore: profileStore,
            cache: cache,
            defaults: defaults,
            client: client
        )
    }

    override func tearDown() {
        sync.stopPolling()
        cache.clear()
        DeskStubURLProtocol.reset()
        defaults.removePersistentDomain(forName: suiteName)
        sync = nil
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    private func deskBody(hash: String, generated: String, equity: Double = 500) -> Data {
        Data("""
        {"schema_version":1,"api_version":"1.2.0","content_hash":"\(hash)","generated_at":"\(generated)","equity_nok":\(equity)}
        """.utf8)
    }

    private func stubDesk200(hash: String, generated: String, etag: String, equity: Double = 500) {
        DeskStubURLProtocol.stubs["/api/desk"] = .init(
            statusCode: 200,
            headers: ["ETag": etag, "Content-Type": "application/json"],
            body: deskBody(hash: hash, generated: generated, equity: equity)
        )
    }

    private func stubDesk304(etag: String = "\"same\"") {
        DeskStubURLProtocol.stubs["/api/desk"] = .init(
            statusCode: 304,
            headers: ["ETag": etag, "Cache-Control": "private, no-cache"],
            body: Data()
        )
    }

    private func stubHealth() {
        DeskStubURLProtocol.stubs["/api/health"] = .init(
            statusCode: 200,
            headers: ["Content-Type": "application/json"],
            body: Data(#"{"ok":true,"api_version":"1.2.0","schema_version":1,"service":"mobile-view"}"#.utf8)
        )
    }

    func testApplyThen304UpdatesContactClockWithoutMutatingSnapshot() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "2026-07-26T10:00:00Z", etag: "\"e1\"", equity: 501)
        await sync.sync(waitForConnectivity: true, probeHealth: true)
        XCTAssertEqual(sync.freshness, .fresh)
        XCTAssertEqual(sync.snapshot?.equityNok, 501)
        XCTAssertEqual(sync.lastETag, "\"e1\"")
        let afterApply = sync.lastSuccessSyncAt
        XCTAssertNotNil(afterApply)
        let snapIdentity = sync.snapshot

        // Age contact clock artificially
        sync.lastSuccessSyncAt = "2020-01-01T00:00:00Z"
        XCTAssertEqual(sync.pollIntervalSeconds, 25) // age >> 300, fresh → 25

        stubDesk304(etag: "\"e1\"")
        await sync.sync(waitForConnectivity: false, probeHealth: false)

        XCTAssertNotEqual(sync.lastSuccessSyncAt, "2020-01-01T00:00:00Z")
        // Contact recent → poll stays 120 while fresh
        XCTAssertEqual(sync.pollIntervalSeconds, 120)
        XCTAssertEqual(sync.freshness, .fresh)
        XCTAssertEqual(sync.snapshot, snapIdentity)
        XCTAssertNil(sync.lastError)
        XCTAssertFalse(sync.isSyncing)
    }

    func testContentUnchanged200UpdatesContactClockNoCacheRewrite() async {
        stubHealth()
        stubDesk200(hash: "same", generated: "2026-07-26T10:00:00Z", etag: "\"e1\"")
        await sync.sync(waitForConnectivity: true, probeHealth: true)
        let cachedAt1 = cache.load()?.cachedAt
        XCTAssertNotNil(cachedAt1)
        let equity = sync.snapshot?.equityNok

        sync.lastSuccessSyncAt = "2020-01-01T00:00:00Z"

        // Same content_hash, different generated_at (should still skip via hash)
        stubDesk200(hash: "same", generated: "2026-07-26T11:00:00Z", etag: "\"e1\"", equity: 999)
        await sync.sync(waitForConnectivity: false, probeHealth: false)

        XCTAssertNotEqual(sync.lastSuccessSyncAt, "2020-01-01T00:00:00Z")
        XCTAssertEqual(sync.snapshot?.equityNok, equity) // not 999 — body ignored
        XCTAssertEqual(cache.load()?.cachedAt, cachedAt1) // no cache rewrite
        XCTAssertEqual(sync.pollIntervalSeconds, 120)
    }

    func testClearCacheClearsETag() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"clear-me\"")
        await sync.sync(waitForConnectivity: true, probeHealth: true)
        XCTAssertEqual(sync.lastETag, "\"clear-me\"")
        let key = SyncService.etagDefaultsKey(for: sync.baseURLString)
        XCTAssertEqual(defaults.string(forKey: key), "\"clear-me\"")

        sync.clearCache()
        XCTAssertNil(sync.lastETag)
        XCTAssertNil(defaults.string(forKey: key))
    }

    func testBaseURLChangeClearsInMemoryETag() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"host-a\"")
        await sync.sync(waitForConnectivity: true, probeHealth: true)
        XCTAssertEqual(sync.lastETag, "\"host-a\"")

        // Switch to another private host — must not keep prior ETag in memory.
        sync.baseURLString = "http://10.0.0.5:8787"
        XCTAssertNil(sync.lastETag)
    }

    func testSilentPollDoesNotSetIsSyncing() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"e\"")
        await sync.sync(waitForConnectivity: true, probeHealth: true)

        stubDesk304()
        // Observe isSyncing stays false around silent poll (completes quickly with stub).
        XCTAssertFalse(sync.isSyncing)
        await sync.sync(waitForConnectivity: false, probeHealth: false)
        XCTAssertFalse(sync.isSyncing)
    }

    func testIfNoneMatchSentOnSecondPoll() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"stored\"")
        await sync.sync(waitForConnectivity: true, probeHealth: true)

        stubDesk304(etag: "\"stored\"")
        await sync.sync(waitForConnectivity: false, probeHealth: false)
        let headers = DeskStubURLProtocol.lastRequestHeaders["/api/desk"] ?? [:]
        let inm = headers["If-None-Match"] ?? headers["if-none-match"]
        XCTAssertEqual(inm, "\"stored\"")
    }

    func testMinimumRequiredStill113() {
        XCTAssertEqual(MobileAPICompatibility.minimumRequired, "1.1.3")
        XCTAssertEqual(
            MobileAPICompatibility.evaluate(apiVersion: "1.1.3"),
            .current(running: "1.1.3")
        )
    }

    func testIdleOver5MinWith304sKeepsPoll120() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"e\"")
        await sync.sync(waitForConnectivity: true, probeHealth: true)

        // Simulate long idle with repeated successful 304s refreshing contact clock.
        for _ in 0..<3 {
            sync.lastSuccessSyncAt = ISO8601DateFormatter().string(
                from: Date().addingTimeInterval(-400) // would be 25s without refresh
            )
            XCTAssertEqual(sync.pollIntervalSeconds, 25)
            stubDesk304()
            await sync.sync(waitForConnectivity: false, probeHealth: false)
            XCTAssertEqual(sync.pollIntervalSeconds, 120)
            XCTAssertEqual(sync.freshness, .fresh)
        }
    }
}
