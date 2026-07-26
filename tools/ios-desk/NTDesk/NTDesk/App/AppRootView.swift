import SwiftUI

/// Redesign root shell: 4 content tabs (compact TabView / regular NavigationSplitView)
/// + Settings gear → sheet. No Settings tab.
struct AppRootView: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.horizontalSizeClass) private var hSize
    @Environment(\.scenePhase) private var scenePhase
    @State private var selectedTab: DeskTab = .desk
    /// Sidebar selection must be Optional for `List(selection:)` on iOS.
    @State private var sidebarSelection: DeskTab? = .desk
    @State private var showSettings = false

    var body: some View {
        Group {
            if hSize == .regular {
                NavigationSplitView {
                    List(selection: $sidebarSelection) {
                        Label("Desk", systemImage: "gauge.with.dots.needle.33percent")
                            .tag(DeskTab.desk)
                        Label("Charts", systemImage: "chart.xyaxis.line")
                            .tag(DeskTab.charts)
                        Label("Pending", systemImage: "list.bullet.rectangle")
                            .tag(DeskTab.pending)
                        Label("Slip", systemImage: "doc.text")
                            .tag(DeskTab.slip)
                        // No Settings row — gear + sheet on all widths
                    }
                    .navigationTitle("NT Desk")
                } detail: {
                    tabRoot(for: sidebarSelection ?? .desk)
                }
            } else {
                TabView(selection: $selectedTab) {
                    DeskView()
                        .tabItem { Label("Desk", systemImage: "gauge.with.dots.needle.33percent") }
                        .tag(DeskTab.desk)
                    ChartsView()
                        .tabItem { Label("Charts", systemImage: "chart.xyaxis.line") }
                        .tag(DeskTab.charts)
                    PendingListView()
                        .tabItem { Label("Pending", systemImage: "list.bullet.rectangle") }
                        .badge(pendingBadge)
                        .tag(DeskTab.pending)
                    SlipView()
                        .tabItem { Label("Slip", systemImage: "doc.text") }
                        .tag(DeskTab.slip)
                }
                .tint(DeskTheme.accent)
                .toolbarBackground(DeskTheme.surface, for: .tabBar)
                .background(DeskTheme.bg)
            }
        }
        .sheet(isPresented: $showSettings) {
            NavigationStack {
                SettingsView()
            }
        }
        .environment(\.openSettings, OpenSettingsAction { showSettings = true })
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

    @ViewBuilder
    private func tabRoot(for tab: DeskTab) -> some View {
        switch tab {
        case .desk: DeskView()
        case .charts: ChartsView()
        case .pending: PendingListView()
        case .slip: SlipView()
        }
    }

    private var pendingBadge: Int {
        sync.snapshot?.pendingCount ?? sync.snapshot?.pendingBets?.count ?? 0
    }
}
