import XCTest
@testable import NTDesk

@MainActor
final class ConnectionProfileStoreTests: XCTestCase {

    private var suiteName: String!
    private var defaults: UserDefaults!
    private var store: ConnectionProfileStore!

    override func setUp() {
        super.setUp()
        suiteName = "ntdesk.tests.profiles.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        store = ConnectionProfileStore(defaults: defaults)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        store = nil
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    // MARK: - Migrate

    func testMigrateFromLegacyBaseURL_seedsDefaultProfile() {
        defaults.set("http://192.168.1.10:8787", forKey: ConnectionProfileStore.legacyBaseURLKey)
        store.migrateFromLegacyBaseURLIfNeeded()

        XCTAssertEqual(store.profiles.count, 1)
        XCTAssertEqual(store.defaultProfile?.baseURLString, "http://192.168.1.10:8787")
        XCTAssertTrue(store.defaultProfile?.isDefault == true)
        // Dual-write keeps legacy key
        XCTAssertEqual(
            defaults.string(forKey: ConnectionProfileStore.legacyBaseURLKey),
            "http://192.168.1.10:8787"
        )
    }

    func testMigrate_isNoOpWhenProfilesExist() {
        store.seedDefault(from: "http://10.0.0.1:8787")
        defaults.set("http://should-not-use:8787", forKey: ConnectionProfileStore.legacyBaseURLKey)
        store.migrateFromLegacyBaseURLIfNeeded()

        XCTAssertEqual(store.profiles.count, 1)
        XCTAssertEqual(store.defaultBaseURLString, "http://10.0.0.1:8787")
    }

    func testMigrate_emptyLegacyUsesFallback() {
        store.migrateFromLegacyBaseURLIfNeeded()
        XCTAssertEqual(store.profiles.count, 1)
        XCTAssertEqual(store.defaultBaseURLString, ConnectionProfileStore.defaultFallbackURL)
    }

    // MARK: - Dual-write

    func testSetDefaultBaseURL_dualWritesLegacyKey() {
        store.seedDefault(from: "http://127.0.0.1:8787")
        store.setDefaultBaseURL("http://100.64.1.2:8787")

        XCTAssertEqual(store.defaultBaseURLString, "http://100.64.1.2:8787")
        XCTAssertEqual(
            defaults.string(forKey: ConnectionProfileStore.legacyBaseURLKey),
            "http://100.64.1.2:8787"
        )
    }

    func testSetDefault_dualWritesLegacyKey() {
        let a = store.add(name: "Home", baseURLString: "http://192.168.1.1:8787", makeDefault: true)
        let b = store.add(name: "Office", baseURLString: "http://10.0.0.5:8787", makeDefault: false)
        XCTAssertEqual(a.id, store.defaultProfile?.id)

        store.setDefault(id: b.id)

        XCTAssertEqual(store.defaultProfile?.id, b.id)
        XCTAssertEqual(
            defaults.string(forKey: ConnectionProfileStore.legacyBaseURLKey),
            "http://10.0.0.5:8787"
        )
        XCTAssertTrue(store.profiles.first(where: { $0.id == b.id })?.isDefault == true)
        XCTAssertTrue(store.profiles.first(where: { $0.id == a.id })?.isDefault == false)
    }

    // MARK: - Add / remove

    func testAddAndRemove_preservesSingleDefaultAndDualWritesPromotedURL() {
        let first = store.add(name: "A", baseURLString: "http://192.168.0.1:8787", makeDefault: true)
        _ = store.add(name: "B", baseURLString: "http://192.168.0.2:8787", makeDefault: true)
        XCTAssertEqual(store.profiles.count, 2)
        XCTAssertEqual(store.profiles.filter(\.isDefault).count, 1)
        XCTAssertNotEqual(store.defaultProfile?.id, first.id)

        let defaultID = store.defaultProfile!.id
        store.remove(id: defaultID)

        XCTAssertEqual(store.profiles.count, 1)
        XCTAssertTrue(store.profiles[0].isDefault)
        // Remove-default must dual-write the promoted profile's URL to `"baseURL"`.
        XCTAssertEqual(
            defaults.string(forKey: ConnectionProfileStore.legacyBaseURLKey),
            store.profiles[0].baseURLString
        )
        XCTAssertEqual(store.profiles[0].baseURLString, "http://192.168.0.1:8787")
    }

    func testPersistence_roundTrip() {
        store.seedDefault(from: "http://192.168.1.50:8787")
        _ = store.add(name: "Travel", baseURLString: "http://100.64.2.3:8787", makeDefault: false)

        let reloaded = ConnectionProfileStore(defaults: defaults)
        XCTAssertEqual(reloaded.profiles.count, 2)
        XCTAssertEqual(reloaded.defaultBaseURLString, "http://192.168.1.50:8787")
    }

    func testMarkSuccess_attributesToProfileIDNotCurrentDefault() {
        let home = store.add(name: "Home", baseURLString: "http://192.168.1.1:8787", makeDefault: true)
        let office = store.add(name: "Office", baseURLString: "http://10.0.0.5:8787", makeDefault: false)
        // Stamp success on home while office is default.
        store.setDefault(id: office.id)
        store.markSuccess(profileID: home.id, at: "2026-07-26T12:00:00Z")

        XCTAssertEqual(
            store.profiles.first(where: { $0.id == home.id })?.lastSuccessAt,
            "2026-07-26T12:00:00Z"
        )
        XCTAssertNil(store.profiles.first(where: { $0.id == office.id })?.lastSuccessAt)
    }
}

// MARK: - SyncService facade

@MainActor
final class SyncServiceFacadeTests: XCTestCase {

    private var suiteName: String!
    private var defaults: UserDefaults!
    private var store: ConnectionProfileStore!
    private var cache: CacheStore!
    private var sync: SyncService!

    override func setUp() {
        super.setUp()
        suiteName = "ntdesk.tests.syncfacade.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        store = ConnectionProfileStore(defaults: defaults)
        cache = CacheStore(filename: "desk_cache_test_\(suiteName!).json")
        cache.clear()
        sync = SyncService(profileStore: store, cache: cache)
    }

    override func tearDown() {
        cache.clear()
        defaults.removePersistentDomain(forName: suiteName)
        sync = nil
        cache = nil
        store = nil
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testInit_migratesLegacyBaseURL() {
        // Fresh store + pre-seeded legacy key before SyncService init
        defaults.removePersistentDomain(forName: suiteName)
        defaults.set("http://192.168.9.9:8787", forKey: "baseURL")
        let freshStore = ConnectionProfileStore(defaults: defaults)
        let service = SyncService(profileStore: freshStore, cache: CacheStore(filename: "desk_cache_mig_\(suiteName!).json"))

        XCTAssertEqual(service.baseURLString, "http://192.168.9.9:8787")
        XCTAssertEqual(freshStore.profiles.count, 1)
        XCTAssertEqual(freshStore.defaultProfile?.baseURLString, "http://192.168.9.9:8787")
    }

    func testBaseURLStringSetter_updatesDefaultProfileAndDualWrites() {
        XCTAssertFalse(store.profiles.isEmpty, "init should seed a default profile")

        sync.baseURLString = "http://10.0.0.42:8787"

        XCTAssertEqual(store.defaultBaseURLString, "http://10.0.0.42:8787")
        XCTAssertEqual(defaults.string(forKey: "baseURL"), "http://10.0.0.42:8787")
        XCTAssertEqual(sync.baseURLString, "http://10.0.0.42:8787")
    }

    func testSetDefaultProfile_updatesFacadeURL() {
        _ = sync.addProfile(name: "Home", baseURLString: "http://192.168.1.1:8787", makeDefault: true)
        let office = sync.addProfile(
            name: "Office",
            baseURLString: "http://10.1.1.1:8787",
            makeDefault: false
        )

        sync.setDefaultProfile(id: office.id)

        XCTAssertEqual(sync.baseURLString, "http://10.1.1.1:8787")
        XCTAssertEqual(defaults.string(forKey: "baseURL"), "http://10.1.1.1:8787")
    }

    func testLegacyFacadePath_settingBaseURLStringAloneIsSufficient() {
        // Mirrors LegacySettingsView: only assign baseURLString then sync.
        sync.baseURLString = "http://100.64.10.10:8787"
        XCTAssertEqual(store.defaultProfile?.baseURLString, "http://100.64.10.10:8787")
        XCTAssertEqual(defaults.string(forKey: "baseURL"), "http://100.64.10.10:8787")
    }

    func testRemoveProfile_dualWritesPromotedDefaultURL() {
        // Init already seeded a fallback default. Add a second profile as default, then remove it —
        // the remaining profile is promoted and dual-written to `"baseURL"`.
        let office = sync.addProfile(
            name: "Office",
            baseURLString: "http://10.1.1.1:8787",
            makeDefault: true
        )
        let remaining = store.profiles.first(where: { $0.id != office.id })!
        let remainingURL = remaining.baseURLString

        sync.removeProfile(id: office.id)

        XCTAssertEqual(sync.baseURLString, remainingURL)
        XCTAssertEqual(defaults.string(forKey: "baseURL"), remainingURL)
        XCTAssertEqual(store.defaultProfile?.id, remaining.id)
        XCTAssertEqual(store.profiles.count, 1)
    }

    func testSetDefaultProfile_rebindsFreshnessAgainstCachedSourceURL() throws {
        // Cache envelope from host A while default becomes host B → staleMismatch.
        let home = sync.addProfile(name: "Home", baseURLString: "http://192.168.1.1:8787", makeDefault: true)
        let office = sync.addProfile(
            name: "Office",
            baseURLString: "http://10.1.1.1:8787",
            makeDefault: false
        )
        XCTAssertEqual(sync.baseURLString, home.baseURLString)

        try cache.save(
            deskObject: ["schema_version": 1, "equity_nok": 500.0],
            sourceBaseURL: "http://192.168.1.1:8787"
        )
        // Simulate a successful sync state for host A.
        sync.loadCacheOnly()
        XCTAssertEqual(sync.freshness, .stale)
        XCTAssertNotNil(sync.snapshot)

        sync.setDefaultProfile(id: office.id)

        XCTAssertEqual(sync.baseURLString, "http://10.1.1.1:8787")
        XCTAssertEqual(sync.freshness, .staleMismatch)
        // Snapshot may still show cached desk from A, but must not claim `.fresh` for B.
        XCTAssertNotEqual(sync.freshness, .fresh)
    }

    func testBaseURLStringChange_rebindsFreshness() throws {
        try cache.save(
            deskObject: ["schema_version": 1, "equity_nok": 100.0],
            sourceBaseURL: "http://192.168.1.1:8787"
        )
        sync.baseURLString = "http://192.168.1.1:8787"
        sync.loadCacheOnly()
        XCTAssertEqual(sync.freshness, .stale)

        // Legacy-style URL change without network yet.
        sync.baseURLString = "http://10.0.0.99:8787"
        XCTAssertEqual(sync.freshness, .staleMismatch)
    }
}
