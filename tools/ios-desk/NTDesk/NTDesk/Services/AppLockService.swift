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
    /// Bumped on every lock / new auth attempt so a late `evaluatePolicy` success cannot unlock.
    private var authGeneration: UInt = 0
    /// Active LA context so background re-lock can `invalidate()` in-flight prompts.
    private var activeContext: LAContext?

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
            invalidateInFlightAuthentication()
            isUnlocked = false
            CacheStore.applyFileProtectionToDefaultCacheIfPresent()
        } else {
            invalidateInFlightAuthentication()
            isUnlocked = true
        }
    }

    // MARK: - Lifecycle

    /// Call when app enters background so returning requires biometrics again.
    /// Cancels / invalidates any in-flight Face ID so a late success cannot unlock after lock.
    func lockIfNeeded() {
        guard isEnabled else { return }
        invalidateInFlightAuthentication()
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
        authGeneration &+= 1
        let generation = authGeneration
        authTask = Task { await performAuthentication(generation: generation) }
    }

    private func performAuthentication(generation: UInt) async {
        isAuthenticating = true
        lastError = nil
        defer {
            // Only clear the flag if this attempt is still current.
            if generation == authGeneration {
                isAuthenticating = false
            }
        }

        let context = LAContext()
        context.localizedCancelTitle = "Cancel"
        activeContext = context
        defer {
            if activeContext === context {
                activeContext = nil
            }
        }

        var error: NSError?
        // Prefer biometrics; fall back to device passcode when biometrics unavailable.
        let policy: LAPolicy
        if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) {
            policy = .deviceOwnerAuthenticationWithBiometrics
        } else if context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &error) {
            policy = .deviceOwnerAuthentication
        } else {
            guard generation == authGeneration, isEnabled else { return }
            lastError = error?.localizedDescription ?? "Biometrics unavailable on this device."
            return
        }

        let reason = "Unlock NT Desk to view your cached desk snapshot."
        do {
            let ok = try await context.evaluatePolicy(policy, localizedReason: reason)
            // Reject late success after background re-lock or a newer auth attempt.
            guard generation == authGeneration, isEnabled, !Task.isCancelled else { return }
            if ok {
                isUnlocked = true
                lastError = nil
            } else {
                lastError = "Authentication did not succeed."
            }
        } catch {
            guard generation == authGeneration, isEnabled else { return }
            // User cancel is common — keep locked without a loud error.
            let ns = error as NSError
            if ns.domain == LAErrorDomain,
               ns.code == LAError.userCancel.rawValue || ns.code == LAError.appCancel.rawValue {
                lastError = nil
            } else {
                lastError = error.localizedDescription
            }
        }
    }

    /// Cancel Task, invalidate LAContext, bump generation so in-flight success cannot unlock.
    private func invalidateInFlightAuthentication() {
        authGeneration &+= 1
        authTask?.cancel()
        authTask = nil
        activeContext?.invalidate()
        activeContext = nil
        isAuthenticating = false
    }

    // MARK: - Testing

    /// Test support: simulate a successful unlock without LocalAuthentication.
    /// Used by `AppLockServiceTests` to prove background `lockIfNeeded` after a session.
    func simulateUnlockedSessionForTesting() {
        guard isEnabled else { return }
        invalidateInFlightAuthentication()
        isUnlocked = true
        lastError = nil
    }
}
