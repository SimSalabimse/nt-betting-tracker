import SwiftUI

struct SlipView: View {
    @EnvironmentObject private var sync: SyncService
    @AppStorage(DeskPreferences.useStructuredSlipKey) private var useStructuredSlipStored: Bool = true

    private var useStructuredSlip: Bool { useStructuredSlipStored }

    var body: some View {
        DeskScreenChrome(title: "Slip") {
            ScrollView {
                VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                    FreshnessBanner()
                    let place = sync.snapshot?.placeThese
                    if place?.exists == true {
                        placeTheseContent(place!)
                    } else {
                        emptyPlaceThese
                    }
                    if let status = sync.snapshot?.statusExcerpt, !status.isEmpty {
                        StatusDocumentView(statusExcerpt: status)
                    }
                }
                .padding(DeskSpacing.contentPad)
            }
            .background(DeskTheme.bg)
            .refreshable { await sync.sync() }
        }
    }

    @ViewBuilder
    private func placeTheseContent(_ place: PlaceThese) -> some View {
        if !useStructuredSlip {
            markdownOnlyCard(place)
        } else {
            let doc = PlaceTheseParser.resolve(
                textExcerpt: place.textExcerpt,
                apiTitle: place.title,
                summaryLine: place.summaryLine,
                rowsPreview: place.rowsPreview
            )
            if doc.parseQuality == .failed {
                markdownOnlyCard(place)
            } else {
                structuredSlip(document: doc, place: place)
            }
        }
    }

    @ViewBuilder
    private func structuredSlip(document: PlaceTheseDocument, place: PlaceThese) -> some View {
        DeskCard(accent: DeskTheme.accent) {
            SlipMetaHeader(document: document, mtime: place.mtime)
        }
        if document.isEmptySlip {
            SlipEmptySuccessCard()
        } else {
            ForEach(document.bets) { bet in
                SlipBetCard(bet: bet)
            }
        }
        if !document.notices.isEmpty {
            DeskCard {
                DisclosureGroup {
                    VStack(alignment: .leading, spacing: DeskSpacing.s1) {
                        ForEach(Array(document.notices.enumerated()), id: \.offset) { _, notice in
                            Text(notice).font(.caption).foregroundStyle(DeskTheme.textMuted)
                        }
                    }.padding(.top, DeskSpacing.s1)
                } label: {
                    Text("Notices").font(.subheadline.weight(.semibold)).foregroundStyle(DeskTheme.text)
                }.tint(DeskTheme.accent)
            }
        }
        if !document.notes.isEmpty {
            DeskCard {
                DisclosureGroup {
                    VStack(alignment: .leading, spacing: DeskSpacing.s1) {
                        ForEach(Array(document.notes.enumerated()), id: \.offset) { _, note in
                            Text("• \(note)").font(.caption).foregroundStyle(DeskTheme.textMuted)
                        }
                    }.padding(.top, DeskSpacing.s1)
                } label: {
                    Text("Notes").font(.subheadline.weight(.semibold)).foregroundStyle(DeskTheme.text)
                }.tint(DeskTheme.accent)
            }
        }
        if let excerpt = place.textExcerpt, !excerpt.isEmpty {
            DeskCard {
                DisclosureGroup {
                    MarkdownFallbackView(text: excerpt).padding(.top, DeskSpacing.s1)
                } label: {
                    Text("View source").font(.subheadline.weight(.semibold)).foregroundStyle(DeskTheme.text)
                }.tint(DeskTheme.accent)
            }
        }
    }

    private func markdownOnlyCard(_ place: PlaceThese) -> some View {
        DeskCard(accent: DeskTheme.accent) {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                Text(place.title ?? "PLACE_THESE")
                    .font(DeskTypography.sectionTitle)
                    .foregroundStyle(DeskTheme.text)
                    .accessibilityAddTraits(.isHeader)
                if let summary = place.summaryLine, !summary.isEmpty {
                    Text(summary).font(.subheadline).foregroundStyle(DeskTheme.textMuted)
                }
                MarkdownFallbackView(text: place.textExcerpt ?? "")
            }
        }
    }

    private var emptyPlaceThese: some View {
        DeskCard {
            DeskContentUnavailable(
                title: "No PLACE_THESE.md",
                systemImage: "doc.plaintext",
                description: "View-only — place bets on the PC desk. Sync when the PC is reachable.",
                accessibilityLabelText: "No PLACE_THESE file. View-only — place bets on the PC desk. Sync when the PC is reachable."
            )
        }
    }
}
