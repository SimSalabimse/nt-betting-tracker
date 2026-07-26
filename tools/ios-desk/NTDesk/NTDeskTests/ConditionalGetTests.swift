import XCTest
@testable import NTDesk

// MARK: - URLProtocol stub

/// In-memory HTTP stub for DeskAPIClient session injection.
final class DeskStubURLProtocol: URLProtocol {
    struct Stub {
        var statusCode: Int
        var headers: [String: String]
        var body: Data
        /// When true, pause after `onRequestStarted` until `resumeHeldRequest()` (mid-flight asserts).
        var holdUntilResume = false
    }

    /// Request path suffix → stub (e.g. "/api/desk").
    static var stubs: [String: Stub] = [:]
    /// Captured request headers per path (last request wins).
    static var lastRequestHeaders: [String: [String: String]] = [:]
    static var requestCount: [String: Int] = [:]
    /// Fired when a held request is ready for mid-flight checks.
    static var onRequestStarted: ((String) -> Void)?
    /// Completes the held request (set while holding; call `resumeHeldRequest()`).
    private static var resumeHeld: (() -> Void)?
    private static let lock = NSLock()

    static func reset() {
        lock.lock()
        stubs = [:]
        lastRequestHeaders = [:]
        requestCount = [:]
        onRequestStarted = nil
        resumeHeld = nil
        lock.unlock()
    }

    /// Resume a request that used `holdUntilResume` (safe from MainActor tests).
    static func resumeHeldRequest() {
        lock.lock()
        let finish = resumeHeld
        resumeHeld = nil
        lock.unlock()
        finish?()
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let path = request.url?.path ?? ""
        Self.lock.lock()
        Self.requestCount[path, default: 0] += 1
        var headers: [String: String] = [:]
        if let h = request.allHTTPHeaderFields {
            headers = h
        }
        Self.lastRequestHeaders[path] = headers
        let stub = Self.stubs[path] ?? Self.stubs.values.first
        let onStarted = Self.onRequestStarted
        Self.lock.unlock()

        guard let stub else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }

        let complete: () -> Void = { [weak self] in
            guard let self else { return }
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: stub.statusCode,
                httpVersion: "HTTP/1.1",
                headerFields: stub.headers
            )!
            self.client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            if !stub.body.isEmpty {
                self.client?.urlProtocol(self, didLoad: stub.body)
            }
            self.client?.urlProtocolDidFinishLoading(self)
        }

        if stub.holdUntilResume {
            Self.lock.lock()
            Self.resumeHeld = complete
            Self.lock.unlock()
            onStarted?(path)
            return
        }
        complete()
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

    /// Prior cache without content_hash + incoming with hash + same generated_at → fall through → unchanged.
    func testPriorHashEmpty_fallsThroughToGeneratedAt() {
        let applied = snap(hash: nil, generated: "2026-01-01T00:00:00Z")
        let incoming = snap(hash: "newhashfromserver", generated: "2026-01-01T00:00:00Z")
        XCTAssertTrue(
            SyncService.isContentUnchanged(incoming: incoming, applied: applied, freshness: .fresh)
        )
        let differentGen = snap(hash: "newhashfromserver", generated: "2026-01-02T00:00:00Z")
        XCTAssertFalse(
            SyncService.isContentUnchanged(incoming: differentGen, applied: applied, freshness: .fresh)
        )
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
        // Release any held request so URLSession cannot hang the next test.
        DeskStubURLProtocol.resumeHeldRequest()
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

    private func stubDesk200(hash: String, generated: String, etag: String, equity: Double = 500, hold: Bool = false) {
        DeskStubURLProtocol.stubs["/api/desk"] = .init(
            statusCode: 200,
            headers: ["ETag": etag, "Content-Type": "application/json"],
            body: deskBody(hash: hash, generated: generated, equity: equity),
            holdUntilResume: hold
        )
    }

    private func stubDesk304(etag: String? = "\"same\"", hold: Bool = false) {
        var headers: [String: String] = ["Cache-Control": "private, no-cache"]
        if let etag {
            headers["ETag"] = etag
        }
        DeskStubURLProtocol.stubs["/api/desk"] = .init(
            statusCode: 304,
            headers: headers,
            body: Data(),
            holdUntilResume: hold
        )
    }

    private func stubDeskError(_ code: Int = 503) {
        DeskStubURLProtocol.stubs["/api/desk"] = .init(
            statusCode: code,
            headers: [:],
            body: Data("err".utf8)
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

    func testBaseURLChangeClearsInMemoryETag_preservesPriorHostDefaults() async {
        let hostA = "http://192.168.1.10:8787"
        let hostB = "http://10.0.0.5:8787"
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"host-a\"")
        await sync.sync(waitForConnectivity: true, probeHealth: true)
        XCTAssertEqual(sync.lastETag, "\"host-a\"")
        let keyA = SyncService.etagDefaultsKey(for: hostA)
        XCTAssertEqual(defaults.string(forKey: keyA), "\"host-a\"")

        // Switch to another private host — must not keep prior ETag in memory.
        sync.baseURLString = hostB
        XCTAssertNil(sync.lastETag)
        // Prior host’s UserDefaults etag remains (per-URL keys).
        XCTAssertEqual(defaults.string(forKey: keyA), "\"host-a\"")

        // Poll on B with no stored etag → no If-None-Match.
        stubDesk200(hash: "hb", generated: "tb", etag: "\"host-b\"")
        await sync.sync(waitForConnectivity: false, probeHealth: false)
        let headers = DeskStubURLProtocol.lastRequestHeaders["/api/desk"] ?? [:]
        let inm = headers["If-None-Match"] ?? headers["if-none-match"]
        XCTAssertNil(inm)
        XCTAssertEqual(sync.lastETag, "\"host-b\"")
    }

    func testSilentPollDoesNotSetIsSyncing_midFlight() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"e\"")
        await sync.sync(waitForConnectivity: true, probeHealth: true)

        stubDesk304(etag: "\"e\"", hold: true)
        let started = expectation(description: "silent desk held")
        DeskStubURLProtocol.onRequestStarted = { path in
            if path == "/api/desk" { started.fulfill() }
        }

        let task = Task { await sync.sync(waitForConnectivity: false, probeHealth: false) }
        await fulfillment(of: [started], timeout: 2)
        XCTAssertFalse(sync.isSyncing, "silent poll must not flip isSyncing mid-flight")
        DeskStubURLProtocol.resumeHeldRequest()
        await task.value
        XCTAssertFalse(sync.isSyncing)
    }

    func testManualSyncSetsIsSyncingMidFlight() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"e\"", hold: true)

        let started = expectation(description: "manual desk held")
        DeskStubURLProtocol.onRequestStarted = { path in
            if path == "/api/desk" { started.fulfill() }
        }

        let task = Task { await sync.sync(waitForConnectivity: true, probeHealth: true) }
        await fulfillment(of: [started], timeout: 2)
        XCTAssertTrue(sync.isSyncing, "manual sync should show spinner mid-flight")
        DeskStubURLProtocol.resumeHeldRequest()
        await task.value
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

    // MARK: - Issue 1: error path must not stomp contact clock

    func testErrorPathPreservesContactClock() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"e\"", equity: 100)
        await sync.sync(waitForConnectivity: true, probeHealth: true)
        XCTAssertEqual(sync.freshness, .fresh)

        stubDesk304(etag: "\"e\"")
        await sync.sync(waitForConnectivity: false, probeHealth: false)
        let contactFresh = sync.lastSuccessSyncAt
        XCTAssertNotNil(contactFresh)
        XCTAssertEqual(sync.pollIntervalSeconds, 120)

        // Force fetch error with cache present — must not rewrite contact from cached_at.
        stubDeskError(503)
        await sync.sync(waitForConnectivity: false, probeHealth: false)

        XCTAssertEqual(sync.lastSuccessSyncAt, contactFresh, "contact clock must survive error + cache fallback")
        XCTAssertEqual(sync.freshness, .stale)
        // Intentional: stale → faster retry (25s), not contact-age adaptive schedule.
        XCTAssertEqual(sync.pollIntervalSeconds, 25)
        XCTAssertNotNil(sync.lastError)
        XCTAssertEqual(sync.snapshot?.equityNok, 100)
    }

    // MARK: - Issue 2: staleMismatch forces full GET (no false-fresh via 304)

    func testStaleMismatchDoesNotSendIfNoneMatch() async {
        // Host A apply
        stubHealth()
        stubDesk200(hash: "ha", generated: "ta", etag: "\"etag-a\"", equity: 111)
        await sync.sync(waitForConnectivity: true, probeHealth: true)
        XCTAssertEqual(sync.freshness, .fresh)
        XCTAssertEqual(sync.snapshot?.equityNok, 111)

        // Pre-store host B etag (as if we synced B before)
        let hostB = "http://10.0.0.5:8787"
        defaults.set("\"etag-b\"", forKey: SyncService.etagDefaultsKey(for: hostB))

        // Switch to B → single global cache is still A → staleMismatch; load B’s etag into memory
        sync.baseURLString = hostB
        XCTAssertEqual(sync.freshness, .staleMismatch)
        XCTAssertEqual(sync.lastETag, "\"etag-b\"")
        XCTAssertEqual(sync.snapshot?.equityNok, 111) // still A’s desk

        // Poll B: must NOT send If-None-Match (force full body despite stored B etag)
        stubDesk200(hash: "hb", generated: "tb", etag: "\"etag-b-new\"", equity: 222)
        await sync.sync(waitForConnectivity: false, probeHealth: false)
        let headers = DeskStubURLProtocol.lastRequestHeaders["/api/desk"] ?? [:]
        let inm = headers["If-None-Match"] ?? headers["if-none-match"]
        XCTAssertNil(inm, "staleMismatch must force unconditional GET")
        XCTAssertEqual(sync.freshness, .fresh)
        XCTAssertEqual(sync.snapshot?.equityNok, 222)
    }

    func test304WithoutResponseETagKeepsPrior() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"keep-me\"")
        await sync.sync(waitForConnectivity: true, probeHealth: true)
        XCTAssertEqual(sync.lastETag, "\"keep-me\"")

        stubDesk304(etag: nil) // no ETag header on 304
        await sync.sync(waitForConnectivity: false, probeHealth: false)
        XCTAssertEqual(sync.lastETag, "\"keep-me\"")
        XCTAssertEqual(sync.freshness, .fresh)
        XCTAssertNotNil(sync.lastSuccessSyncAt)
    }

    func testUserSyncQueuedDuringSilentPoll() async {
        stubHealth()
        stubDesk200(hash: "h1", generated: "t1", etag: "\"e\"")
        await sync.sync(waitForConnectivity: true, probeHealth: true)

        stubDesk304(etag: "\"e\"", hold: true)
        let silentStarted = expectation(description: "silent held")
        DeskStubURLProtocol.onRequestStarted = { path in
            if path == "/api/desk" { silentStarted.fulfill() }
        }
        let silentTask = Task { await sync.sync(waitForConnectivity: false, probeHealth: false) }
        await fulfillment(of: [silentStarted], timeout: 2)

        // Queue user Sync while silent is in flight.
        await sync.sync(waitForConnectivity: true, probeHealth: true)

        // Prepare follow-up body before releasing silent.
        stubHealth()
        stubDesk200(hash: "h2", generated: "t2", etag: "\"e2\"", equity: 777)
        DeskStubURLProtocol.onRequestStarted = nil
        DeskStubURLProtocol.resumeHeldRequest()
        await silentTask.value

        // Follow-up Task is scheduled from defer — wait for content apply.
        let deadline = Date().addingTimeInterval(3)
        while Date() < deadline {
            if sync.snapshot?.contentHash == "h2" { break }
            try? await Task.sleep(nanoseconds: 30_000_000)
        }
        XCTAssertEqual(sync.snapshot?.contentHash, "h2", "queued user sync should apply after silent poll")
        XCTAssertEqual(sync.snapshot?.equityNok, 777)
        XCTAssertFalse(sync.isSyncing)
    }
}
