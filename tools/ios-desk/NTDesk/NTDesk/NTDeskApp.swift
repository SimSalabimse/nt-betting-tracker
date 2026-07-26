import SwiftUI

@main
struct NTDeskApp: App {
    @StateObject private var sync = SyncService()

    var body: some Scene {
        WindowGroup {
            #if NTDESK_USE_LEGACY_UI
            LegacyRootView()
                .environmentObject(sync)
                .preferredColorScheme(.dark)
            #else
            AppRootView()
                .environmentObject(sync)
                .preferredColorScheme(.dark)
            #endif
        }
    }
}
