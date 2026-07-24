import SwiftUI

struct SlipView: View {
    @EnvironmentObject private var sync: SyncService

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    FreshnessBanner()
                    let place = sync.snapshot?.placeThese
                    if place?.exists == true {
                        Text(place?.title ?? "PLACE_THESE")
                            .font(.headline)
                        if let s = place?.summaryLine {
                            Text(s).font(.subheadline).foregroundStyle(.secondary)
                        }
                        Text(place?.textExcerpt ?? "")
                            .font(.system(.footnote, design: .monospaced))
                            .textSelection(.enabled)
                    } else {
                        ContentUnavailableView("No PLACE_THESE.md", systemImage: "doc")
                    }
                    if let status = sync.snapshot?.statusExcerpt, !status.isEmpty {
                        Text("Status")
                            .font(.headline)
                            .padding(.top)
                        Text(status)
                            .font(.system(.caption, design: .monospaced))
                            .textSelection(.enabled)
                    }
                }
                .padding()
            }
            .navigationTitle("Slip")
            .refreshable { await sync.sync() }
        }
    }
}
