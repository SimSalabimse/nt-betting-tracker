import SwiftUI
import UIKit

struct PendingListView: View {
    @EnvironmentObject private var sync: SyncService
    @Environment(\.openSettings) private var openSettings
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
                            EmptyDeskView {
                                openSettings()
                            }
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
                Text("No open pending / confirmed bets")
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                    .accessibilityLabel("No open pending or confirmed bets")
            } else if filteredBets.isEmpty {
                Text("No bets match “\(searchText)”")
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                    .accessibilityLabel("No bets match search")
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
