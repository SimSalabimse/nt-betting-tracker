import SwiftUI

/// Redesign root shell: 4 content tabs (compact TabView / regular NavigationSplitView)
/// + Settings gear → sheet. No Settings tab.
struct AppRootView: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.horizontalSizeClass) private var hSize
    @Environment(\.scenePhase) private var scenePhase
    /// Single source of truth for content destination (compact TabView + regular sidebar).
    @State private var selectedTab: DeskTab = .desk
    @State private var showSettings = false

    /// `List(selection:)` on iOS requires `Binding<SelectionValue?>`; keep it derived from `selectedTab`.
    private var sidebarSelection: Binding<DeskTab?> {
        Binding(
            get: { selectedTab },
            set: { if let tab = $0 { selectedTab = tab } }
        )
    }

    var body: some View {
        Group {
            if hSize == .regular {
                NavigationSplitView {
                    List(selection: sidebarSelection) {
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
                    tabRoot(for: selectedTab)
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
                // Solid tab bar (desk night) — ultraThin material washes labels on iOS 26+ glass.
                .toolbarBackground(DeskTheme.surface, for: .tabBar)
                .toolbarBackground(.visible, for: .tabBar)
                .toolbarColorScheme(.dark, for: .tabBar)
                .background(DeskTheme.bg)
            }
        }
        .sheet(isPresented: $showSettings) {
            NavigationStack {
                SettingsView()
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbarBackground(DeskTheme.surface, for: .navigationBar)
                    .toolbarBackground(.visible, for: .navigationBar)
                    .toolbarColorScheme(.dark, for: .navigationBar)
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button("Done") {
                                showSettings = false
                            }
                            .accessibilityIdentifier("settings.done")
                        }
                    }
            }
            // Solid sheet chrome — iOS 26/27 ultraThin + large title made a tall blur
            // until scroll collapsed the title into the nav bar.
            .presentationBackground(DeskTheme.bg)
            .preferredColorScheme(.dark)
        }
        .environment(\.openSettings, OpenSettingsAction { showSettings = true })
        .task {
            // Initial load: wait for connectivity (user opened the app).
            await sync.sync(waitForConnectivity: true, probeHealth: true)
            sync.startPolling()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                // Foreground resume: one full sync (health+desk), then cheap desk-only polls.
                Task { await sync.sync(waitForConnectivity: false, probeHealth: true) }
                sync.startPolling()
            } else {
                // Background: stop timers entirely (iOS will suspend work anyway).
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


