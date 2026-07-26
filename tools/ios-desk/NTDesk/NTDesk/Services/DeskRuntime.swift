import Foundation

/// Lightweight in-process handle so App Intents can reuse the live `SyncService`
/// when the UI is running. Falls back to a fresh instance when the app is not active.
@MainActor
enum DeskRuntime {
    /// Weak so the app's `@StateObject` remains the owner.
    static weak var sync: SyncService?

    /// Prefer the live service; otherwise construct an ephemeral one for Shortcuts.
    static func syncForIntent() -> SyncService {
        if let sync {
            return sync
        }
        return SyncService()
    }
}
