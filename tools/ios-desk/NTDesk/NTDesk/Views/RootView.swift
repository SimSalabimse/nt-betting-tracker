import SwiftUI

struct RootView: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.scenePhase) private var scenePhase
    @State private var tab = 0

    var body: some View {
        TabView(selection: $tab) {
            DeskView()
                .tabItem { Label("Desk", systemImage: "gauge.with.dots.needle.33percent") }
                .tag(0)
            ChartsView()
                .tabItem { Label("Charts", systemImage: "chart.xyaxis.line") }
                .tag(1)
            PendingListView()
                .tabItem { Label("Pending", systemImage: "list.bullet") }
                .tag(2)
            SlipView()
                .tabItem { Label("Slip", systemImage: "doc.plaintext") }
                .tag(3)
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gear") }
                .tag(4)
        }
        .background(DeskTheme.bg)
        .task {
            await sync.sync()
            sync.startPolling()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                Task { await sync.sync() }
                sync.startPolling()
            } else {
                sync.stopPolling()
            }
        }
    }
}
