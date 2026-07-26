import SwiftUI

/// Frozen pre-HIG root shell. Shares `DeskTab` with scaffold `RootView` (same five tabs).
struct LegacyRootView: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.scenePhase) private var scenePhase
    @State private var selectedTab: DeskTab = .desk

    var body: some View {
        TabView(selection: $selectedTab) {
            LegacyDeskView(selectedTab: $selectedTab)
                .tabItem { Label("Desk", systemImage: "gauge.with.dots.needle.33percent") }
                .tag(DeskTab.desk)
            LegacyChartsView()
                .tabItem { Label("Charts", systemImage: "chart.xyaxis.line") }
                .tag(DeskTab.charts)
            LegacyPendingListView(selectedTab: $selectedTab)
                .tabItem { Label("Pending", systemImage: "list.bullet.rectangle") }
                .tag(DeskTab.pending)
            LegacySlipView()
                .tabItem { Label("Slip", systemImage: "doc.plaintext") }
                .tag(DeskTab.slip)
            LegacySettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
                .tag(DeskTab.settings)
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
