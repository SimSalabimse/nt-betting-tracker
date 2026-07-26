import AppIntents
import Foundation

/// Read-only Shortcuts / Siri action: fetch desk from the configured PC and refresh the cache.
/// Does not place, settle, or mutate engine state — only `SyncService.sync()`.
struct SyncDeskIntent: AppIntent {
    static var title: LocalizedStringResource = "Sync Desk"
    static var description = IntentDescription(
        "Fetches the latest read-only desk snapshot from the configured PC and updates the on-device cache."
    )

    /// Keep work in-process; do not force a full UI launch for a background sync.
    static var openAppWhenRun: Bool = false

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let sync = DeskRuntime.syncForIntent()
        await sync.sync()

        if sync.freshness == .fresh {
            let when = sync.lastSuccessSyncAt ?? "just now"
            return .result(dialog: IntentDialog("Desk synced (\(when))."))
        }

        if sync.freshness == .liveNotPersisted {
            return .result(dialog: IntentDialog("Desk fetched live but cache write failed."))
        }

        if let err = sync.lastError, sync.freshness == .empty {
            return .result(dialog: IntentDialog("Sync failed: \(err)"))
        }

        if sync.freshness == .stale || sync.freshness == .staleMismatch {
            let detail = sync.lastError.map { " (\($0))" } ?? ""
            return .result(dialog: IntentDialog("Could not reach PC; cached desk kept\(detail)."))
        }

        if let err = sync.lastError {
            return .result(dialog: IntentDialog("Sync note: \(err)"))
        }

        return .result(dialog: IntentDialog("No desk data yet. Set a base URL in Settings."))
    }
}

/// Surfaces "Sync Desk" in the Shortcuts app suggestions.
struct NTDeskShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: SyncDeskIntent(),
            phrases: [
                "Sync \(.applicationName) desk",
                "Refresh \(.applicationName) desk",
                "Sync desk in \(.applicationName)"
            ],
            shortTitle: "Sync Desk",
            systemImageName: "arrow.triangle.2.circlepath"
        )
    }
}
