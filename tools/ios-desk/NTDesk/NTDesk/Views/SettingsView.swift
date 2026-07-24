import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var sync: SyncService
    @State private var draftURL: String = ""
    @State private var confirmClearCache = false
    @FocusState private var urlFieldFocused: Bool

    private var appVersionLine: String {
        let short = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "—"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "—"
        return "\(short) (\(build))"
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("http://192.168.x.x:8787", text: $draftURL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                        .textContentType(.URL)
                        .focused($urlFieldFocused)
                        .foregroundStyle(DeskTheme.text)
                        .accessibilityLabel("PC base URL")
                        .accessibilityHint("LAN IP or Tailscale 100.x address for the desk mobile-view server")

                    Button("Save & sync") {
                        sync.baseURLString = draftURL
                        Task { await sync.sync() }
                    }
                    .foregroundStyle(DeskTheme.accent)
                    .accessibilityHint("Saves the base URL and syncs a read-only desk snapshot")

                    Text(
                        "Use LAN IP or Tailscale 100.x — e.g. http://192.168.1.10:8787 or http://100.x.y.z:8787. Prefer numeric IP over MagicDNS for cleartext. Start mobile-view with -Lan on the PC."
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
            .onAppear {
                draftURL = sync.baseURLString
                if sync.freshness == .empty {
                    urlFieldFocused = true
                }
            }
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
