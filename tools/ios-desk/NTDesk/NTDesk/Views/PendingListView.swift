import SwiftUI

struct PendingListView: View {
    @EnvironmentObject private var sync: SyncService

    var body: some View {
        NavigationStack {
            List {
                FreshnessBanner()
                    .listRowBackground(Color.clear)
                let bets = sync.snapshot?.pendingBets ?? []
                if bets.isEmpty {
                    Text("No open pending / confirmed bets")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(bets) { b in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(b.match ?? "—")
                                .font(.headline)
                            Text(b.selection ?? "—")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            HStack {
                                Text(b.date ?? "")
                                Spacer()
                                if let o = b.decimalOdds {
                                    Text(String(format: "@ %.2f", o))
                                }
                                if let s = b.stakeNok {
                                    Text(String(format: "%.0f NOK", s))
                                }
                            }
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        }
                        .padding(.vertical, 4)
                    }
                }
            }
            .navigationTitle("Pending")
            .refreshable { await sync.sync() }
        }
    }
}
