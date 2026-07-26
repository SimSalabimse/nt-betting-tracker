import XCTest
@testable import NTDesk

@MainActor
final class AppLockServiceTests: XCTestCase {

    private var suiteName: String!
    private var defaults: UserDefaults!
    private var lock: AppLockService!

    override func setUp() {
        super.setUp()
        suiteName = "ntdesk.tests.applock.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        lock = AppLockService(defaults: defaults)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        lock = nil
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testDefaultIsOffAndUnlocked() {
        XCTAssertFalse(lock.isEnabled)
        XCTAssertFalse(lock.isLocked)
        XCTAssertTrue(lock.isUnlocked)
        XCTAssertNil(defaults.object(forKey: AppLockService.enabledKey))
    }

    func testEnableLocksImmediatelyAndPersists() {
        lock.setEnabled(true)
        XCTAssertTrue(lock.isEnabled)
        XCTAssertTrue(lock.isLocked)
        XCTAssertFalse(lock.isUnlocked)
        XCTAssertEqual(defaults.bool(forKey: AppLockService.enabledKey), true)
    }

    func testDisableUnlocksWithoutBiometrics() {
        lock.setEnabled(true)
        XCTAssertTrue(lock.isLocked)
        lock.setEnabled(false)
        XCTAssertFalse(lock.isEnabled)
        XCTAssertFalse(lock.isLocked)
        XCTAssertTrue(lock.isUnlocked)
        XCTAssertEqual(defaults.bool(forKey: AppLockService.enabledKey), false)
    }

    func testLockIfNeededOnlyWhenEnabled() {
        lock.lockIfNeeded()
        XCTAssertTrue(lock.isUnlocked)

        lock.setEnabled(true)
        // Enabling already locks; unlock via private state by disabling then re-enable cycle:
        // simulate unlocked session then background lock.
        lock.setEnabled(false)
        lock.setEnabled(true)
        XCTAssertTrue(lock.isLocked)

        // Simulate authenticated session by disabling lock semantics then re-reading:
        // When disabled, lockIfNeeded is a no-op for gate.
        lock.setEnabled(false)
        lock.lockIfNeeded()
        XCTAssertFalse(lock.isLocked)
    }

    func testRestoresEnabledFromDefaultsOnInit() {
        defaults.set(true, forKey: AppLockService.enabledKey)
        let restored = AppLockService(defaults: defaults)
        XCTAssertTrue(restored.isEnabled)
        XCTAssertTrue(restored.isLocked)
    }

    func testCacheStoreReadsAppLockFlag() {
        XCTAssertFalse(CacheStore.isAppLockEnabledInDefaults(defaults))
        defaults.set(true, forKey: AppLockService.enabledKey)
        XCTAssertTrue(CacheStore.isAppLockEnabledInDefaults(defaults))
    }
}
