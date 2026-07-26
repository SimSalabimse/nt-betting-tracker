import SwiftUI

struct SlipView: View {
    @EnvironmentObject private var sync: SyncService

    var body: some View {
        DeskScreenChrome(title: "Slip") {
            ScrollView {
                VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                    FreshnessBanner()

                    let place = sync.snapshot?.placeThese
                    if place?.exists == true {
                        DeskCard(accent: DeskTheme.accent) {
                            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                                Text(place?.title ?? "PLACE_THESE")
                                    .font(DeskTypography.sectionTitle)
                                    .foregroundStyle(DeskTheme.text)
                                    .accessibilityAddTraits(.isHeader)

                                if let summary = place?.summaryLine, !summary.isEmpty {
                                    Text(summary)
                                        .font(.subheadline)
                                        .foregroundStyle(DeskTheme.textMuted)
                                }

                                Text(place?.textExcerpt ?? "")
                                    .font(DeskTypography.monoFootnote)
                                    .foregroundStyle(DeskTheme.text)
                                    .textSelection(.enabled)
                            }
                        }
                    } else {
                        emptyPlaceThese
                    }

                    if let status = sync.snapshot?.statusExcerpt, !status.isEmpty {
                        DeskCard {
                            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                                Text("STATUS")
                                    .font(DeskTypography.sectionLabel)
                                    .foregroundStyle(DeskTheme.textDim)
                                    .tracking(0.6)
                                    .accessibilityAddTraits(.isHeader)

                                Text(status)
                                    .font(.system(.caption, design: .monospaced))
                                    .foregroundStyle(DeskTheme.textMuted)
                                    .textSelection(.enabled)
                                    .accessibilityLabel("Status excerpt")
                                    .accessibilityValue(status)
                            }
                        }
                    }
                }
                .padding(DeskSpacing.contentPad)
            }
            .background(DeskTheme.bg)
            .refreshable { await sync.sync() }
        }
    }

    private var emptyPlaceThese: some View {
        DeskCard {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                Label("No PLACE_THESE.md", systemImage: "doc.plaintext")
                    .font(DeskTypography.sectionTitle)
                    .foregroundStyle(DeskTheme.text)
                Text("View-only — place bets on the PC desk. Sync when the PC is reachable.")
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(
            "No PLACE_THESE file. View-only — place bets on the PC desk. Sync when the PC is reachable."
        )
    }
}
