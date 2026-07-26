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

    func testAddAndRemove_preservesSingleDefault() {
        let first = store.add(name: "A", baseURLString: "http://192.168.0.1:8787", makeDefault: true)
        _ = store.add(name: "B", baseURLString: "http://192.168.0.2:8787", makeDefault: true)
        XCTAssertEqual(store.profiles.count, 2)
        XCTAssertEqual(store.profiles.filter(\.isDefault).count, 1)
        XCTAssertNotEqual(store.defaultProfile?.id, first.id)

        store.remove(id: store.defaultProfile!.id)
        XCTAssertEqual(store.profiles.count, 1)
        XCTAssertTrue(store.profiles[0].isDefault)
    }

    func testPersistence_roundTrip() {
        store.seedDefault(from: "http://192.168.1.50:8787")
        _ = store.add(name: "Travel", baseURLString: "http://100.64.2.3:8787", makeDefault: false)

        let reloaded = ConnectionProfileStore(defaults: defaults)
        XCTAssertEqual(reloaded.profiles.count, 2)
        XCTAssertEqual(reloaded.defaultBaseURLString, "http://192.168.1.50:8787")
    }
}

// MARK: - SyncService facade

@MainActor
final class SyncServiceFacadeTests: XCTestCase {

    private var suiteName: String!
    private var defaults: UserDefaults!
    private var store: ConnectionProfileStore!
    private var sync: SyncService!

    override func setUp() {
        super.setUp()
        suiteName = "ntdesk.tests.syncfacade.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        store = ConnectionProfileStore(defaults: defaults)
        sync = SyncService(profileStore: store)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        sync = nil
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
        let service = SyncService(profileStore: freshStore)

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
}
