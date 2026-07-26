import SwiftUI

@main
struct NTDeskApp: App {
    @StateObject private var sync = SyncService()
    @StateObject private var appLock = AppLockService()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ZStack {
                #if NTDESK_USE_LEGACY_UI
                LegacyRootView()
                #else
                AppRootView()
                #endif

                if appLock.isLocked {
                    AppLockGateView(appLock: appLock)
                        .transition(.opacity)
                        .zIndex(1)
                }
            }
            .environmentObject(sync)
            .environmentObject(appLock)
            .preferredColorScheme(.dark)
            .onAppear {
                DeskRuntime.sync = sync
            }
            .onChange(of: scenePhase) { _, phase in
                // Re-lock when leaving the app so return requires biometrics again.
                if phase == .background {
                    appLock.lockIfNeeded()
                }
            }
        }
    }
}
