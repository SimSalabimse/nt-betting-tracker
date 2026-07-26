import SwiftUI

/// Frozen pre-HIG root shell. Uses `LegacyDeskTab` (five tabs including Settings).
struct LegacyRootView: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.scenePhase) private var scenePhase
    @State private var selectedTab: LegacyDeskTab = .desk

    var body: some View {
        TabView(selection: $selectedTab) {
            LegacyDeskView(selectedTab: $selectedTab)
                .tabItem { Label("Desk", systemImage: "gauge.with.dots.needle.33percent") }
                .tag(LegacyDeskTab.desk)
            LegacyChartsView()
                .tabItem { Label("Charts", systemImage: "chart.xyaxis.line") }
                .tag(LegacyDeskTab.charts)
            LegacyPendingListView(selectedTab: $selectedTab)
                .tabItem { Label("Pending", systemImage: "list.bullet.rectangle") }
                .tag(LegacyDeskTab.pending)
            LegacySlipView()
                .tabItem { Label("Slip", systemImage: "doc.plaintext") }
                .tag(LegacyDeskTab.slip)
            LegacySettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
                .tag(LegacyDeskTab.settings)
        }
        .tint(DeskTheme.accent)
        .toolbarBackground(DeskTheme.surface, for: .tabBar)
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
