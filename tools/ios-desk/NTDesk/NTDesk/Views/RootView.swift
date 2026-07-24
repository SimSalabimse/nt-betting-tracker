import SwiftUI

/// Type-safe tab destinations — never hard-code tab indices for navigation.
enum DeskTab: Int, CaseIterable, Hashable {
    case desk = 0
    case charts
    case pending
    case slip
    case settings
}

struct RootView: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.scenePhase) private var scenePhase
    @State private var selectedTab: DeskTab = .desk

    var body: some View {
        TabView(selection: $selectedTab) {
            DeskView(selectedTab: $selectedTab)
                .tabItem { Label("Desk", systemImage: "gauge.with.dots.needle.33percent") }
                .tag(DeskTab.desk)
            ChartsView()
                .tabItem { Label("Charts", systemImage: "chart.xyaxis.line") }
                .tag(DeskTab.charts)
            PendingListView(selectedTab: $selectedTab)
                .tabItem { Label("Pending", systemImage: "list.bullet.rectangle") }
                .tag(DeskTab.pending)
            SlipView()
                .tabItem { Label("Slip", systemImage: "doc.plaintext") }
                .tag(DeskTab.slip)
            SettingsView()
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
