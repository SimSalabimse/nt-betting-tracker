import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var sync: SyncService
    @State private var draftURL: String = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("PC base URL") {
                    TextField("http://192.168.x.x:8787", text: $draftURL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                    Button("Save & sync") {
                        sync.baseURLString = draftURL
                        Task { await sync.sync() }
                    }
                    Text("Use LAN IP or Tailscale 100.x. Prefer numeric IP over MagicDNS for cleartext.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section("Cache") {
                    LabeledContent("Last success", value: sync.lastSuccessSyncAt ?? "—")
                    LabeledContent("Freshness", value: sync.freshness.rawValue)
                    if let err = sync.lastError {
                        Text(err).font(.caption).foregroundStyle(.orange)
                    }
                    Button("Sync now") {
                        Task { await sync.sync() }
                    }
                    Button("Clear cache", role: .destructive) {
                        sync.clearCache()
                    }
                }
                Section("About") {
                    Text("View-only personal desk. Unsigned IPA sideload build.")
                        .font(.caption)
                    Text("Charts: equity, daily P/L, drawdown, sport — from PC ledger snapshot.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
            .onAppear { draftURL = sync.baseURLString }
        }
    }
}
