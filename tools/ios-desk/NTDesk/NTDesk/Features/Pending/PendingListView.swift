import SwiftUI
import UIKit

struct PendingListView: View {
    @EnvironmentObject private var sync: SyncService
    @State private var searchText = ""

    private var allBets: [PendingBet] {
        sync.snapshot?.pendingBets ?? []
    }

    private var filteredBets: [PendingBet] {
        allBets.filter { $0.matchesSearch(searchText) }
    }

    var body: some View {
        DeskScreenChrome(title: "Pending") {
            Group {
                if sync.snapshot == nil {
                    ScrollView {
                        VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                            FreshnessBanner()
                            EmptyDeskView()
                                .frame(maxWidth: .infinity)
                                .padding(.top, DeskSpacing.s4)
                        }
                        .padding(DeskSpacing.contentPad)
                    }
                } else {
                    pendingList
                }
            }
            .background(DeskTheme.bg)
            .refreshable { await sync.sync() }
            .searchable(
                text: $searchText,
                prompt: "Match, selection, sport, bet id"
            )
            .navigationDestination(for: PendingBetRoute.self) { route in
                PendingBetDetailView(bet: route.bet, desk: sync.snapshot)
            }
        }
    }

    private var pendingList: some View {
        List {
            FreshnessBanner()
                .listRowInsets(EdgeInsets(
                    top: DeskSpacing.s2,
                    leading: DeskSpacing.contentPad,
                    bottom: DeskSpacing.s2,
                    trailing: DeskSpacing.contentPad
                ))
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)

            if allBets.isEmpty {
                DeskContentUnavailable(
                    title: "No open bets",
                    systemImage: "list.bullet.rectangle",
                    description: "No pending or confirmed-placed tickets right now.",
                    accessibilityLabelText: "No open pending or confirmed bets"
                )
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)
            } else if filteredBets.isEmpty {
                DeskContentUnavailable(
                    title: "No matches",
                    systemImage: "magnifyingglass",
                    description: "No bets match “\(searchText)”.",
                    accessibilityLabelText: "No bets match search"
                )
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)
            } else {
                ForEach(filteredBets) { bet in
                    NavigationLink(value: PendingBetRoute.make(from: bet)) {
                        PendingBetRow(bet: bet)
                    }
                    .buttonStyle(.plain)
                    .listRowInsets(EdgeInsets(
                        top: DeskSpacing.s2,
                        leading: DeskSpacing.contentPad,
                        bottom: DeskSpacing.s2,
                        trailing: DeskSpacing.contentPad
                    ))
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                    .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                        if let betId = bet.betId, !betId.isEmpty {
                            Button {
                                UIPasteboard.general.string = betId
                            } label: {
                                Label("Copy ID", systemImage: "doc.on.doc")
                            }
                            .tint(DeskTheme.accent)
                            .accessibilityLabel("Copy bet id")
                        }
                    }
                }
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(DeskTheme.bg)
    }
}
