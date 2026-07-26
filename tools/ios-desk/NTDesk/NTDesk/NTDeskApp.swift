import SwiftUI

@main
struct NTDeskApp: App {
    @StateObject private var sync = SyncService()
    @StateObject private var appLock = AppLockService()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ZStack {
                deskRoot
                    // When locked, hide desk content from VoiceOver / Switch Control
                    // so equity and pending are not reachable under the gate.
                    .accessibilityHidden(appLock.isLocked)
                    .accessibilityElement(children: appLock.isLocked ? .ignore : .contain)

                if appLock.isLocked {
                    AppLockGateView(appLock: appLock)
                        .transition(.opacity)
                        .zIndex(1)
                }

                // Multitasking / app-switcher privacy: solid cover while lock is enabled
                // and the scene is not active (inactive snapshot or background).
                // Does not re-prompt Face ID on Control Center; background still re-locks.
                if appLock.isEnabled && scenePhase != .active {
                    DeskTheme.bg
                        .ignoresSafeArea()
                        .accessibilityHidden(true)
                        .zIndex(2)
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
                // Also invalidates any in-flight Face ID sheet (see AppLockService.lockIfNeeded).
                if phase == .background {
                    appLock.lockIfNeeded()
                }
            }
        }
    }

    @ViewBuilder
    private var deskRoot: some View {
        #if NTDESK_USE_LEGACY_UI
        LegacyRootView()
        #else
        AppRootView()
        #endif
    }
}
