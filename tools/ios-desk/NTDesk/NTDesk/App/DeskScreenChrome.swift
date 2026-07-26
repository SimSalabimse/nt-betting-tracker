import SwiftUI

/// Wraps content in NavigationStack; checkmark to the **right** of the title opens a
/// full connection sheet (not a broken half-popover) with star rating + Sync.
struct DeskScreenChrome<Content: View>: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.openSettings) private var openSettings
    let title: String
    @ViewBuilder var content: () -> Content

    @State private var showConnectionSheet = false

    private var quality: ConnectionQuality {
        ConnectionQuality.evaluate(
            freshness: sync.freshness,
            isSyncing: sync.isSyncing,
            lastSuccessSyncAt: sync.lastSuccessSyncAt,
            lastError: sync.lastError,
            baseURL: sync.baseURLString,
            lastRTTMs: sync.lastHealthRTTMs
        )
    }

    var body: some View {
        NavigationStack {
            content()
                .navigationBarTitleDisplayMode(.inline)
                .toolbarBackground(DeskTheme.surface, for: .navigationBar)
                .toolbarBackground(.visible, for: .navigationBar)
                .toolbarColorScheme(.dark, for: .navigationBar)
                .toolbar {
                    ToolbarItem(placement: .principal) {
                        HStack(spacing: 8) {
                            Text(title)
                                .font(.headline.weight(.semibold))
                                .foregroundStyle(DeskTheme.text)
                                .lineLimit(1)
                                .minimumScaleFactor(0.85)
                                .accessibilityAddTraits(.isHeader)

                            // Status control — RIGHT of title
                            Button {
                                Haptics.lightImpact()
                                showConnectionSheet = true
                            } label: {
                                Group {
                                    if sync.isSyncing {
                                        ProgressView()
                                            .controlSize(.mini)
                                            .tint(DeskTheme.accent)
                                    } else {
                                        Image(systemName: statusSymbol)
                                            .font(.subheadline.weight(.semibold))
                                            .foregroundStyle(quality.tint)
                                            .symbolRenderingMode(.hierarchical)
                                    }
                                }
                                .frame(minWidth: 28, minHeight: 28)
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel(statusAccessibilityLabel)
                            .accessibilityHint("Shows connection quality")
                            .accessibilityIdentifier("connection.status")
                        }
                    }

                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            openSettings()
                        } label: {
                            Image(systemName: "gearshape")
                                .font(.body.weight(.medium))
                                .foregroundStyle(DeskTheme.text)
                                .accessibilityLabel("Settings")
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("settings.gear")
                    }
                }
                // Sheet with detents — popover was clipped / half-height on phone.
                .sheet(isPresented: $showConnectionSheet) {
                    NavigationStack {
                        connectionSheetBody
                            .navigationTitle("Connection")
                            .navigationBarTitleDisplayMode(.inline)
                            .toolbar {
                                ToolbarItem(placement: .topBarTrailing) {
                                    Button("Done") {
                                        showConnectionSheet = false
                                    }
                                    .accessibilityIdentifier("connection.done")
                                }
                            }
                    }
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
                    .presentationBackground(DeskTheme.surface)
                    .preferredColorScheme(.dark)
                }
        }
    }

    private var statusSymbol: String {
        switch sync.freshness {
        case .fresh: return "checkmark.circle.fill"
        case .liveNotPersisted: return "exclamationmark.circle.fill"
        case .stale: return "clock.arrow.circlepath"
        case .staleMismatch: return "link.badge.plus"
        case .empty: return "wifi.slash"
        }
    }

    private var statusAccessibilityLabel: String {
        if sync.isSyncing { return "Syncing" }
        return "Connection \(quality.title), \(quality.stars) of 5 stars"
    }

    private var connectionSheetBody: some View {
        List {
            Section {
                ConnectionStarsView(quality: quality)
                    .frame(maxWidth: .infinity)
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                    .padding(.vertical, DeskSpacing.s2)

                Text(quality.title)
                    .font(.headline)
                    .foregroundStyle(quality.tint)
                    .listRowBackground(Color.clear)
                Text(quality.detail)
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
                    .listRowBackground(Color.clear)
            }

            Section("PC") {
                Text(sync.baseURLString)
                    .font(.system(.footnote, design: .monospaced))
                    .foregroundStyle(DeskTheme.text)
                    .textSelection(.enabled)
                if sync.isServerAPIOutdated {
                    Label(sync.apiCompatibility.warningDetail, systemImage: "exclamationmark.triangle.fill")
                        .font(.caption)
                        .foregroundStyle(DeskTheme.pending)
                        .fixedSize(horizontal: false, vertical: true)
                } else if let api = sync.serverApiVersion {
                    LabeledContent("API") {
                        Text("mobile-view \(api)")
                            .font(.system(.caption, design: .monospaced))
                            .foregroundStyle(DeskTheme.profit)
                    }
                }
                if let rtt = sync.lastHealthRTTMs {
                    LabeledContent("Last health RTT") {
                        Text("\(rtt) ms")
                            .font(.system(.body, design: .monospaced))
                    }
                }
                if !sync.rttSamplesMs.isEmpty {
                    // Keep default list row chrome (no clear bg) — clear + separators
                    // drew a stray hairline across the next "Last success" row on iOS 26/27.
                    VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                        Text("RTT trend (last \(sync.rttSamplesMs.count))")
                            .font(.caption)
                            .foregroundStyle(DeskTheme.textMuted)
                        HStack(alignment: .bottom, spacing: 4) {
                            ForEach(Array(sync.rttSamplesMs.enumerated()), id: \.offset) { _, ms in
                                let h = max(8, min(36, CGFloat(ms) / 20))
                                RoundedRectangle(cornerRadius: 2)
                                    .fill(DeskTheme.accent.opacity(0.85))
                                    .frame(width: 14, height: h)
                                    .accessibilityLabel("\(ms) milliseconds")
                            }
                            Spacer(minLength: 0)
                        }
                        // Fixed plot height so bars never clip into the following list row.
                        .frame(height: 36, alignment: .bottom)
                        .accessibilityElement(children: .combine)
                        Text(sync.rttSamplesMs.map { "\($0)" }.joined(separator: " · ") + " ms")
                            .font(.system(.caption2, design: .monospaced))
                            .foregroundStyle(DeskTheme.textDim)
                    }
                    .padding(.vertical, 2)
                    .listRowSeparator(.hidden, edges: .bottom)
                }
                if let last = sync.lastSuccessSyncAt {
                    LabeledContent("Last success") {
                        Text(DeskFormatters.relativeTime(last) ?? last)
                            .font(.caption)
                            .foregroundStyle(DeskTheme.textMuted)
                    }
                }
                LabeledContent("Freshness") {
                    Text(sync.freshness.rawValue)
                        .foregroundStyle(quality.tint)
                }
                LabeledContent("Network") {
                    Text(sync.network.pathLabel)
                        .foregroundStyle(sync.network.isSatisfied ? DeskTheme.profit : DeskTheme.loss)
                }
            }

            if sync.canRestoreLastKnownGood {
                Section {
                    Button {
                        sync.restoreLastKnownGoodBaseURL()
                        Task { await sync.sync(waitForConnectivity: true) }
                    } label: {
                        Label("Use last known good PC", systemImage: "arrow.uturn.backward")
                    }
                    .foregroundStyle(DeskTheme.accent)
                    Text(sync.lastKnownGoodBaseURL ?? "")
                        .font(.caption2.monospaced())
                        .foregroundStyle(DeskTheme.textMuted)
                }
            }

            Section {
                Button {
                    Haptics.mediumImpact()
                    Task {
                        await sync.sync(waitForConnectivity: true)
                    }
                } label: {
                    Label(sync.isSyncing ? "Syncing…" : "Sync now", systemImage: "arrow.clockwise")
                        .frame(maxWidth: .infinity)
                }
                .disabled(sync.isSyncing)
                .accessibilityIdentifier("connection.sync_now")
            }
        }
        .listStyle(.insetGrouped)
        .scrollContentBackground(.hidden)
        .background(DeskTheme.surface)
    }
}
