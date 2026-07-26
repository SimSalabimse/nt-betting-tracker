import SwiftUI

/// Stack-free Settings content. The presenting sheet owns the only NavigationStack.
/// Connection IA: active URL + NavigationLinks to ConnectionSettingsView / ProfilesListView.
struct SettingsView: View {
    @EnvironmentObject private var sync: SyncService
    @EnvironmentObject private var appLock: AppLockService
    @State private var confirmClearCache = false
    @FocusState private var urlFieldFocused: Bool
    /// Same key + default as `SlipView` — single UserDefaults read path for the flag.
    @AppStorage(DeskPreferences.useStructuredSlipKey) private var useStructuredSlip: Bool = true
    @State private var showDiscovery = false

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

                Button {
                    showDiscovery = true
                } label: {
                    Label("Find PC on network", systemImage: "magnifyingglass")
                }
                .foregroundStyle(DeskTheme.accent)
                .accessibilityHint("User-initiated LAN scan for mobile-view. You confirm before connecting.")

                NavigationLink {
                    ProfilesListView()
                } label: {
                    Label("Manage profiles", systemImage: "list.bullet.rectangle")
                }
                .accessibilityHint("Add, delete, or set the default connection profile")

                Text(
                    "Profiles store LAN or Tailscale URLs for home/office/travel. Default profile drives sync. Prefer numeric IP over MagicDNS for cleartext. Use Find PC on network for a LAN health scan (confirm before connect), or Edit connection for a typed URL — including Tailscale 100.x (no CGNAT bulk scan)."
                )
                .font(.caption)
                .foregroundStyle(DeskTheme.textMuted)
            } header: {
                Text("Connection")
            }

            Section {
                LabeledContent("Last success") {
                    TimelineView(.periodic(from: .now, by: 60)) { context in
                        Text(
                            DeskFormatters.relativeTime(
                                sync.lastSuccessSyncAt,
                                relativeTo: context.date
                            )
                        )
                        .font(.system(.body, design: .monospaced))
                        .foregroundStyle(DeskTheme.textMuted)
                        .accessibilityLabel(
                            "Last success \(DeskFormatters.relativeTime(sync.lastSuccessSyncAt, relativeTo: context.date))"
                        )
                    }
                }
                LabeledContent("Freshness") {
                    Text(freshnessDisplayLabel)
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
                Toggle("Structured slip", isOn: $useStructuredSlip)
                    .tint(DeskTheme.accent)
                    .accessibilityHint("When on, PLACE_THESE is shown as cards; when off, Markdown source is shown")
            } header: {
                Text("Display")
            } footer: {
                Text("Structured slip parses PLACE_THESE into bet cards. Turn off to always show Markdown source.")
                Toggle(isOn: appLockEnabledBinding) {
                    Label("Require \(appLock.biometryLabel)", systemImage: "lock.fill")
                }
                .tint(DeskTheme.accent)
                .accessibilityIdentifier("settings.appLock")
                .accessibilityHint("Locks the app UI when leaving; default is off")

                Text(
                    "Optional. Default off. UI lock only — does not replace device passcode. When on, the desk cache file also gets complete-until-first-unlock protection after each successful write."
                )
                .font(.caption)
                .foregroundStyle(DeskTheme.textMuted)
                Text("App lock")
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
                    "Privacy: connects only to addresses you set or confirm (LAN or Tailscale). Desk JSON is cached on-device. No third-party analytics, accounts, or cloud sync."
                )
                .font(.caption)
                .foregroundStyle(DeskTheme.textMuted)

                Text(
                    "LAN residual risk: mobile-view on a shared Wi‑Fi is readable by others on that L2 who can reach the port. Prefer Tailscale for remote. Discovery only probes your current private subnet; it does not scan Tailscale CGNAT."
                )
                .font(.caption)
                .foregroundStyle(DeskTheme.textDim)

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
        .sheet(isPresented: $showDiscovery) {
            NavigationStack {
                DiscoverySheet()
                    .environmentObject(sync)
            }
            .preferredColorScheme(.dark)
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
