import SwiftUI

@main
struct NTDeskApp: App {
    @StateObject private var sync = SyncService()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(sync)
                .preferredColorScheme(.dark)
        }
    }
}
