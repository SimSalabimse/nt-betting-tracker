import SwiftUI

/// Stack-free Settings content. The presenting sheet owns the only NavigationStack.
/// Connection IA: active URL + NavigationLinks to ConnectionSettingsView / ProfilesListView.
struct SettingsView: View {
    @EnvironmentObject private var sync: SyncService
    @State private var confirmClearCache = false

    private var appVersionLine: String {
        let short = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "—"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "—"
        return "\(short) (\(build))"
    }

    var body: some View {
        Form {
            Section {
                if let profile = sync.profileStore.defaultProfile {
                    LabeledContent("Active") {
                        Text(profile.name)
                            .foregroundStyle(DeskTheme.text)
                    }
                }
                LabeledContent("URL") {
                    Text(sync.baseURLString)
                        .font(.caption.monospaced())
                        .foregroundStyle(DeskTheme.textMuted)
                        .lineLimit(2)
                        .multilineTextAlignment(.trailing)
                }
                .accessibilityElement(children: .combine)

                NavigationLink {
                    ConnectionSettingsView()
                } label: {
                    Label("Edit connection", systemImage: "link")
                }
                .accessibilityHint("Edit default profile name and base URL, then save and sync")

                NavigationLink {
                    ProfilesListView()
                } label: {
                    Label("Manage profiles", systemImage: "list.bullet.rectangle")
                }
                .accessibilityHint("Add, delete, or set the default connection profile")

                Button("Save & sync") {
                    // Re-apply facade (dual-write) then sync — matches Legacy path.
                    sync.baseURLString = sync.baseURLString
                    Task { await sync.sync() }
                }
                .foregroundStyle(DeskTheme.accent)
                .accessibilityHint("Syncs a read-only desk snapshot from the default connection")

                Text(
                    "Profiles store LAN or Tailscale URLs for home/office/travel. Default profile drives sync. Prefer numeric IP over MagicDNS for cleartext."
                )
                .font(.caption)
                .foregroundStyle(DeskTheme.textMuted)
            } header: {
                Text("Connection")
            }

            Section {
                LabeledContent("Last success") {
                    Text(sync.lastSuccessSyncAt ?? "—")
                        .font(.system(.body, design: .monospaced))
                        .foregroundStyle(DeskTheme.textMuted)
                }
                LabeledContent("Freshness") {
                    Text(sync.freshness.rawValue)
                        .foregroundStyle(freshnessColor)
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
                Button("Sync now") {
                    Task { await sync.sync() }
                }
                .foregroundStyle(DeskTheme.accent)
                .accessibilityHint("Fetches the latest desk snapshot from the configured PC")

                Button("Clear cache", role: .destructive) {
                    confirmClearCache = true
                }
                .accessibilityHint("Removes the on-device cached desk snapshot after confirmation")
            } header: {
                Text("Cache")
            }

            Section {
                Text("View-only personal desk. Unsigned IPA sideload build. Place and settle stay on the PC.")
                    .font(.caption)
                    .foregroundStyle(DeskTheme.text)

                Text(
                    "Privacy: connects only to the base URL you set (LAN or Tailscale). Desk JSON is cached on-device. No third-party analytics, accounts, or cloud sync."
                )
                .font(.caption)
                .foregroundStyle(DeskTheme.textMuted)

                LabeledContent("Version", value: appVersionLine)
                    .font(.caption)
                    .foregroundStyle(DeskTheme.textMuted)

                #if DEBUG
                LabeledContent("Build flavor", value: "Redesign")
                    .font(.caption)
                    .foregroundStyle(DeskTheme.textMuted)
                #endif

                Text("Charts: equity, daily P/L, drawdown, sport — from PC ledger snapshot.")
                    .font(.caption)
                    .foregroundStyle(DeskTheme.textDim)
            } header: {
                Text("About")
            }
        }
        .scrollContentBackground(.hidden)
        .background(DeskTheme.bg)
        .navigationTitle("Settings")
        .confirmationDialog(
            "Clear on-device cache?",
            isPresented: $confirmClearCache,
            titleVisibility: .visible
        ) {
            Button("Clear cache", role: .destructive) {
                sync.clearCache()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Removes the cached desk snapshot. Sync again when the PC is reachable.")
        }
    }

    private var freshnessColor: Color {
        switch sync.freshness {
        case .fresh:
            return DeskTheme.profit
        case .stale, .liveNotPersisted:
            return DeskTheme.pending
        case .staleMismatch:
            return DeskTheme.loss
        case .empty:
            return DeskTheme.textMuted
        }
    }
}
