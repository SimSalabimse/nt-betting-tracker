import SwiftUI

/// Edit the active (default) connection URL and save & sync.
/// Stack-free: push target inside Settings sheet NavigationStack.
struct ConnectionSettingsView: View {
    @EnvironmentObject private var sync: SyncService
    @State private var draftName: String = ""
    @State private var draftURL: String = ""
    @FocusState private var urlFieldFocused: Bool

    var body: some View {
        Form {
            Section {
                TextField("Name", text: $draftName)
                    .foregroundStyle(DeskTheme.text)
                    .accessibilityLabel("Profile name")

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
                    saveAndSync()
                }
                .foregroundStyle(DeskTheme.accent)
                .accessibilityHint("Saves the base URL on the default profile and syncs a read-only desk snapshot")

                Text(
                    "Use LAN IP or Tailscale 100.x — e.g. http://192.168.1.10:8787 or http://100.x.y.z:8787. Prefer numeric IP over MagicDNS for cleartext. Start mobile-view with -Lan on the PC."
                )
                .font(.caption)
                .foregroundStyle(DeskTheme.textMuted)
            } header: {
                Text("Default connection")
            }

            if let profile = sync.profileStore.defaultProfile {
                Section {
                    LabeledContent("Profile", value: profile.name)
                    LabeledContent("Created") {
                        Text(profile.createdAt.formatted(date: .abbreviated, time: .shortened))
                            .foregroundStyle(DeskTheme.textMuted)
                    }
                    if let last = profile.lastSuccessAt {
                        LabeledContent("Last success") {
                            Text(last)
                                .font(.system(.body, design: .monospaced))
                                .foregroundStyle(DeskTheme.textMuted)
                        }
                    }
                } header: {
                    Text("Active profile")
                }
            }
        }
        .scrollContentBackground(.hidden)
        .background(DeskTheme.bg)
        .navigationTitle("Connection")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            let def = sync.profileStore.defaultProfile
            draftName = def?.name ?? ""
            draftURL = sync.baseURLString
            if sync.freshness == .empty {
                urlFieldFocused = true
            }
        }
    }

    private func saveAndSync() {
        let url = draftURL.trimmingCharacters(in: .whitespacesAndNewlines)
        let name = draftName.trimmingCharacters(in: .whitespacesAndNewlines)
        if let id = sync.profileStore.defaultProfile?.id {
            sync.updateProfile(
                id: id,
                name: name.isEmpty ? nil : name,
                baseURLString: url
            )
        } else {
            sync.addProfile(
                name: name.isEmpty ? ConnectionProfileStore.displayName(for: url) : name,
                baseURLString: url,
                makeDefault: true
            )
        }
        // Facade dual-write path used by Legacy remains valid:
        sync.baseURLString = url
        Task { await sync.sync() }
    }
}
