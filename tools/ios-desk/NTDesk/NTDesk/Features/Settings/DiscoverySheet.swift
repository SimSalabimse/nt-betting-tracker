import SwiftUI

/// User-initiated LAN discovery. Lists health hits (`ok==true`) and **confirms** before
/// adding a connection profile or running a full desk sync.
struct DiscoverySheet: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.dismiss) private var dismiss

    @StateObject private var discovery = ServerDiscoveryService()
    @State private var pendingConnect: DiscoveredServer?
    @State private var portText: String = "8787"

    var body: some View {
        List {
            Section {
                Text(
                    "Scans your current private Wi‑Fi subnet for mobile-view on the chosen port (default 8787). Only GET /api/health is used — the full desk is fetched after you confirm. Tailscale 100.x is not bulk-scanned; add those as manual profiles."
                )
                .font(.caption)
                .foregroundStyle(DeskTheme.textMuted)
                .listRowBackground(DeskTheme.surface)

                HStack {
                    Text("Port")
                    Spacer()
                    TextField("8787", text: $portText)
                        .keyboardType(.numberPad)
                        .multilineTextAlignment(.trailing)
                        .frame(maxWidth: 100)
                        .foregroundStyle(DeskTheme.text)
                        .accessibilityLabel("Scan port")
                }
                .listRowBackground(DeskTheme.surface)

                if !discovery.pathAllowsDiscovery {
                    Text(pathBlockedMessage)
                        .font(.caption)
                        .foregroundStyle(DeskTheme.pending)
                        .listRowBackground(DeskTheme.surface)
                }

                Button {
                    beginScan()
                } label: {
                    if discovery.isScanning {
                        Label("Scanning…", systemImage: "antenna.radiowaves.left.and.right")
                    } else {
                        Label("Scan local network", systemImage: "magnifyingglass")
                    }
                }
                .disabled(discovery.isScanning || !discovery.pathAllowsDiscovery)
                .foregroundStyle(DeskTheme.accent)
                .listRowBackground(DeskTheme.surface)
                .accessibilityHint("Probes private LAN hosts for a desk health endpoint. You confirm before connecting.")

                if discovery.isScanning {
                    ProgressView(value: progressValue) {
                        Text(progressLabel)
                            .font(.caption)
                            .foregroundStyle(DeskTheme.textMuted)
                    }
                    .tint(DeskTheme.accent)
                    .listRowBackground(DeskTheme.surface)

                    Button("Cancel scan", role: .cancel) {
                        discovery.cancelScan()
                    }
                    .listRowBackground(DeskTheme.surface)
                }

                if let status = discovery.statusMessage {
                    Text(status)
                        .font(.caption)
                        .foregroundStyle(DeskTheme.textMuted)
                        .listRowBackground(DeskTheme.surface)
                }
            } header: {
                Text("Discover")
            } footer: {
                Text(
                    "LAN residual risk: anyone on the same Wi‑Fi who can reach the PC port can read the desk API (including health). Prefer Tailscale ACLs for remote access. Guest networks: only your current private subnet is probed."
                )
            }

            if !discovery.candidates.isEmpty {
                Section {
                    ForEach(discovery.candidates) { server in
                        Button {
                            pendingConnect = server
                        } label: {
                            HStack(alignment: .firstTextBaseline) {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(server.host)
                                        .font(.body.monospaced())
                                        .foregroundStyle(DeskTheme.text)
                                    Text(server.baseURLString)
                                        .font(.caption.monospaced())
                                        .foregroundStyle(DeskTheme.textMuted)
                                        .lineLimit(1)
                                }
                                Spacer()
                                Text("\(server.latencyMs) ms")
                                    .font(.caption.monospaced())
                                    .foregroundStyle(DeskTheme.textDim)
                                Image(systemName: "chevron.right")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(DeskTheme.textDim)
                            }
                        }
                        .accessibilityLabel("Desk server at \(server.host), \(server.latencyMs) milliseconds")
                        .accessibilityHint("Shows confirmation before adding a profile and syncing")
                        .listRowBackground(DeskTheme.surface)
                    }
                } header: {
                    Text("Found")
                } footer: {
                    Text("Tap a server, then confirm. Connecting creates or updates a profile and runs a full sync.")
                }
            }

            Section {
                Text(
                    "About: discovery increases findability only. Health already exposes metadata such as project_root to any client that can hit the port. No third-party analytics."
                )
                .font(.caption)
                .foregroundStyle(DeskTheme.textDim)
                .listRowBackground(DeskTheme.surface)
            } header: {
                Text("Privacy")
            }
        }
        .scrollContentBackground(.hidden)
        .background(DeskTheme.bg)
        .navigationTitle("Find PC")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Close") {
                    discovery.cancelScan()
                    dismiss()
                }
            }
        }
        .onAppear {
            // Capture the class instance (not the View) for the escaping provider.
            let syncService = sync
            discovery.lastSuccessHostProvider = {
                guard let url = PrivateHostPolicy.normalizeBaseURL(syncService.baseURLString) else {
                    return nil
                }
                return url.host
            }
            portText = String(discovery.port)
            if discovery.pathAllowsDiscovery, discovery.candidates.isEmpty, !discovery.isScanning {
                // Do not auto-scan — user-initiated only. Ready state message.
                if discovery.statusMessage == nil {
                    discovery.setStatusMessage("Ready — tap Scan when you want to probe the LAN.")
                }
            }
        }
        .onDisappear {
            discovery.cancelScan()
        }
        .confirmationDialog(
            "Connect to this PC?",
            isPresented: Binding(
                get: { pendingConnect != nil },
                set: { if !$0 { pendingConnect = nil } }
            ),
            titleVisibility: .visible,
            presenting: pendingConnect
        ) { server in
            Button("Connect & sync") {
                confirmConnect(server)
            }
            Button("Cancel", role: .cancel) {
                pendingConnect = nil
            }
        } message: { server in
            Text(
                "Add \(server.baseURLString) as your default profile and fetch the desk snapshot. Only connect to your own PC."
            )
        }
    }

    // MARK: - Actions

    private func beginScan() {
        if let p = Int(portText.trimmingCharacters(in: .whitespacesAndNewlines)), (1...65535).contains(p) {
            discovery.port = p
        } else {
            discovery.port = 8787
            portText = "8787"
        }
        discovery.startScan()
    }

    private func confirmConnect(_ server: DiscoveredServer) {
        pendingConnect = nil
        // Normalize through policy before saving.
        guard let normalized = PrivateHostPolicy.normalizeBaseURL(server.baseURLString) else {
            discovery.setStatusMessage("Host not allowed for cleartext HTTP.")
            return
        }
        let urlString = normalized.absoluteString.hasSuffix("/")
            ? String(normalized.absoluteString.dropLast())
            : normalized.absoluteString
        let name = ConnectionProfileStore.displayName(for: urlString)

        if let existing = sync.profiles.first(where: { urlsMatch($0.baseURLString, urlString) }) {
            sync.updateProfile(id: existing.id, name: existing.name, baseURLString: urlString)
            sync.setDefaultProfile(id: existing.id)
        } else {
            sync.addProfile(name: name, baseURLString: urlString, makeDefault: true)
        }

        Task {
            await sync.sync()
            dismiss()
        }
    }

    // MARK: - Helpers

    private var pathBlockedMessage: String {
        switch discovery.pathKind {
        case .cellularOrConstrained:
            return "Cellular or constrained network — discovery disabled. Use a saved profile or Wi‑Fi."
        case .unsatisfied:
            return "Network unavailable."
        default:
            return "Discovery unavailable on this path."
        }
    }

    private var progressValue: Double {
        guard discovery.hostsPlanned > 0 else { return 0 }
        return min(1, Double(discovery.hostsProbed) / Double(discovery.hostsPlanned))
    }

    private var progressLabel: String {
        "\(discovery.hostsProbed) / \(discovery.hostsPlanned) hosts"
    }

    private func urlsMatch(_ a: String, _ b: String) -> Bool {
        let na = PrivateHostPolicy.normalizeBaseURL(a)?.absoluteString
        let nb = PrivateHostPolicy.normalizeBaseURL(b)?.absoluteString
        return na != nil && na == nb
    }
}
