import SwiftUI

/// Stack-free Settings content. The presenting sheet owns the only NavigationStack.
struct SettingsView: View {
    @EnvironmentObject private var sync: SyncService
    @EnvironmentObject private var appLock: AppLockService
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var confirmClearCache = false
    @AppStorage(DeskPreferences.useStructuredSlipKey) private var useStructuredSlip: Bool = true
    @State private var showDiscovery = false
    @State private var exportURL: URL?
    @State private var exportError: String?
    @State private var showExportShare = false

    private var appVersionLine: String {
        let short = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "—"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "—"
        return "\(short) (\(build))"
    }

    private var relativeTimelinePeriod: TimeInterval {
        reduceMotion ? 300 : 60
    }

    var body: some View {
        Form {
            Section {
                if let profile = sync.profileStore.defaultProfile {
                    LabeledContent("Active") {
                        Text(profile.name).foregroundStyle(DeskTheme.text)
                    }
                }
                LabeledContent("URL") {
                    Text(sync.baseURLString)
                        .font(.caption.monospaced())
                        .foregroundStyle(DeskTheme.textMuted)
                        .lineLimit(2)
                        .multilineTextAlignment(.trailing)
                }

                NavigationLink {
                    ConnectionSettingsView()
                } label: {
                    Label("Edit connection", systemImage: "link")
                }

                Button {
                    showDiscovery = true
                } label: {
                    Label("Find PC on network", systemImage: "magnifyingglass")
                }
                .foregroundStyle(DeskTheme.accent)

                NavigationLink {
                    ProfilesListView()
                } label: {
                    Label("Manage profiles", systemImage: "list.bullet.rectangle")
                }
            } header: {
                Text("Connection")
            } footer: {
                Text("Prefer numeric LAN or Tailscale 100.x IP. Discovery only scans your private subnet (not CGNAT).")
            }

            Section {
                LabeledContent("Last success") {
                    TimelineView(.periodic(from: .now, by: relativeTimelinePeriod)) { context in
                        let relative = DeskFormatters.relativeTime(
                            sync.lastSuccessSyncAt,
                            relativeTo: context.date
                        )
                        Text(relative)
                            .font(.system(.body, design: .monospaced))
                            .foregroundStyle(DeskTheme.textMuted)
                    }
                }
                LabeledContent("Freshness") {
                    Text(freshnessDisplayLabel).foregroundStyle(freshnessColor)
                }
                if let rtt = sync.lastHealthRTTMs {
                    LabeledContent("Health RTT") {
                        Text("\(rtt) ms")
                            .font(.system(.body, design: .monospaced))
                            .foregroundStyle(DeskTheme.textMuted)
                    }
                }
                if let err = sync.lastError {
                    Text(err)
                        .font(.caption)
                        .foregroundStyle(DeskTheme.pending)
                }
            } header: {
                Text("Status")
            }

            Section {
                Toggle("Structured slip", isOn: $useStructuredSlip)
                    .tint(DeskTheme.accent)
            } header: {
                Text("Display")
            } footer: {
                Text("Structured slip parses PLACE_THESE into bet cards. Turn off for Markdown source.")
            }

            Section {
                Toggle(isOn: appLockEnabledBinding) {
                    Label("Require \(appLock.biometryLabel)", systemImage: "lock.fill")
                }
                .tint(DeskTheme.accent)
                .accessibilityIdentifier("settings.appLock")
            } header: {
                Text("App lock")
            } footer: {
                Text("Optional. Default off. UI lock only — does not replace device passcode.")
            }

            Section {
                Button("Sync now") {
                    Haptics.mediumImpact()
                    Task { await sync.sync(waitForConnectivity: true) }
                }
                .foregroundStyle(DeskTheme.accent)

                Button {
                    exportDebugZip()
                } label: {
                    Label("Export cache debug zip", systemImage: "square.and.arrow.up")
                }
                .foregroundStyle(DeskTheme.accent)
                .accessibilityHint("Shares on-device cache envelope and connection metadata")

                if let exportError {
                    Text(exportError)
                        .font(.caption)
                        .foregroundStyle(DeskTheme.loss)
                }

                Button("Clear cache", role: .destructive) {
                    confirmClearCache = true
                }
            } header: {
                Text("Cache")
            }

            Section {
                Text("View-only personal desk. Place and settle stay on the PC.")
                    .font(.caption)
                    .foregroundStyle(DeskTheme.text)
                LabeledContent("App version", value: appVersionLine)
                    .font(.caption)
                    .foregroundStyle(DeskTheme.textMuted)
                if let api = sync.snapshot?.apiVersion, !api.isEmpty {
                    LabeledContent("PC API", value: "mobile-view \(api)")
                        .font(.caption)
                        .foregroundStyle(DeskTheme.textMuted)
                }
                if let schema = sync.snapshot?.schemaVersion {
                    LabeledContent("Desk schema", value: "v\(schema)")
                        .font(.caption)
                        .foregroundStyle(DeskTheme.textMuted)
                }
            } header: {
                Text("About")
            } footer: {
                Text("App = phone IPA. PC API = tools/mobile-view VERSION. Schema = wire shape (docs/api).")
            }
        }
        .scrollContentBackground(.hidden)
        .background(DeskTheme.bg)
        .navigationTitle("Settings")
        // Inline from the start — large title + material on iOS 26/27 sheets
        // left a tall blur until the user scrolled and the title collapsed.
        .navigationBarTitleDisplayMode(.inline)
        .confirmationDialog(
            "Clear on-device cache?",
            isPresented: $confirmClearCache,
            titleVisibility: .visible
        ) {
            Button("Clear cache", role: .destructive) {
                sync.clearCache()
                Haptics.warning()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Removes the cached desk snapshot. Sync again when the PC is reachable.")
        }
        .sheet(isPresented: $showDiscovery) {
            NavigationStack {
                DiscoverySheet()
                    .environmentObject(sync)
            }
            .preferredColorScheme(.dark)
        }
        .sheet(isPresented: $showExportShare) {
            if let exportURL {
                ShareSheet(items: [exportURL])
            }
        }
    }

    private func exportDebugZip() {
        do {
            let url = try CacheDebugExport.buildZip(sync: sync)
            exportURL = url
            exportError = nil
            showExportShare = true
            Haptics.success()
        } catch {
            exportError = error.localizedDescription
            Haptics.error()
        }
    }

    private var appLockEnabledBinding: Binding<Bool> {
        Binding(
            get: { appLock.isEnabled },
            set: { appLock.setEnabled($0) }
        )
    }

    private var freshnessDisplayLabel: String {
        switch sync.freshness {
        case .fresh: return "Live"
        case .stale: return "Stale"
        case .staleMismatch: return "URL mismatch"
        case .liveNotPersisted: return "Live (not saved)"
        case .empty: return "Empty"
        }
    }

    private var freshnessColor: Color {
        switch sync.freshness {
        case .fresh: return DeskTheme.profit
        case .stale, .liveNotPersisted: return DeskTheme.pending
        case .staleMismatch: return DeskTheme.loss
        case .empty: return DeskTheme.textMuted
        }
    }
}

// MARK: - Share sheet

private struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
