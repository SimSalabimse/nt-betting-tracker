import Foundation
import LocalAuthentication
import Combine

/// Optional UI app lock via Face ID / Touch ID / device passcode.
/// Default **off** (`app_lock_enabled`). Does not encrypt the cache by itself;
/// when enabled, `CacheStore` also applies explicit file protection after writes.
@MainActor
final class AppLockService: ObservableObject {
    /// Design key: `app_lock_enabled`, default false.
    static let enabledKey = "app_lock_enabled"

    @Published private(set) var isEnabled: Bool
    /// When lock is enabled, content is hidden until biometrics succeed.
    @Published private(set) var isUnlocked: Bool
    @Published var lastError: String?
    /// Transient flag while the system sheet is up.
    @Published private(set) var isAuthenticating = false

    private let defaults: UserDefaults
    private var authTask: Task<Void, Never>?

    /// Content should be covered by the lock gate.
    var isLocked: Bool { isEnabled && !isUnlocked }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        // Missing key → false (default OFF).
        let enabled = defaults.object(forKey: Self.enabledKey) as? Bool ?? false
        self.isEnabled = enabled
        // Start locked when feature is on so cold launch always authenticates.
        self.isUnlocked = !enabled
    }

    // MARK: - Preference

    /// Enable/disable app lock. Enabling re-locks immediately and applies cache file protection.
    /// Disabling clears the lock gate without requiring biometrics.
    func setEnabled(_ enabled: Bool) {
        guard enabled != isEnabled else { return }
        isEnabled = enabled
        defaults.set(enabled, forKey: Self.enabledKey)
        lastError = nil
        if enabled {
            isUnlocked = false
            CacheStore.applyFileProtectionToDefaultCacheIfPresent()
        } else {
            isUnlocked = true
            authTask?.cancel()
            isAuthenticating = false
        }
    }

    // MARK: - Lifecycle

    /// Call when app enters background so returning requires biometrics again.
    func lockIfNeeded() {
        guard isEnabled else { return }
        isUnlocked = false
        lastError = nil
    }

    // MARK: - Biometrics

    /// Whether the device can evaluate biometrics or device passcode.
    var canAuthenticate: Bool {
        let context = LAContext()
        var error: NSError?
        return context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &error)
    }

    /// Human label for the primary biometric (Face ID / Touch ID / passcode).
    var biometryLabel: String {
        let context = LAContext()
        var error: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            return "Device Passcode"
        }
        switch context.biometryType {
        case .faceID:
            return "Face ID"
        case .touchID:
            return "Touch ID"
        case .opticID:
            return "Optic ID"
        @unknown default:
            return "Biometrics"
        }
    }

    /// Prompt Face ID / Touch ID / passcode. No-op when lock is off.
    func authenticate() {
        guard isEnabled else {
            isUnlocked = true
            return
        }
        guard !isAuthenticating else { return }

        authTask?.cancel()
        authTask = Task { await performAuthentication() }
    }

    private func performAuthentication() async {
        isAuthenticating = true
        lastError = nil
        defer { isAuthenticating = false }

        let context = LAContext()
        context.localizedCancelTitle = "Cancel"
        var error: NSError?
        // Prefer biometrics; fall back to device passcode when biometrics unavailable.
        let policy: LAPolicy
        if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) {
            policy = .deviceOwnerAuthenticationWithBiometrics
        } else if context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &error) {
            policy = .deviceOwnerAuthentication
        } else {
            lastError = error?.localizedDescription ?? "Biometrics unavailable on this device."
            return
        }

        let reason = "Unlock NT Desk to view your cached desk snapshot."
        do {
            let ok = try await context.evaluatePolicy(policy, localizedReason: reason)
            if ok {
                isUnlocked = true
                lastError = nil
            } else {
                lastError = "Authentication did not succeed."
            }
        } catch {
            // User cancel is common — keep locked without a loud error.
            let ns = error as NSError
            if ns.domain == LAErrorDomain, ns.code == LAError.userCancel.rawValue {
                lastError = nil
            } else {
                lastError = error.localizedDescription
            }
        }
    }
}
