import SwiftUI
import UIKit

/// Full-field pending bet detail + desk context from last sync snapshot.
struct PendingBetDetailView: View {
    let bet: PendingBet
    let desk: DeskSnapshot?

    @State private var copiedBetId = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DeskSpacing.s3) {
                matchSection
                selectionSection
                statusSection
                identitySection
                deskContextSection
            }
            .padding(DeskSpacing.contentPad)
        }
        .background(DeskTheme.bg)
        .navigationTitle(bet.match ?? "Pending bet")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(DeskTheme.surface, for: .navigationBar)
    }

    // MARK: - Sections

    private var matchSection: some View {
        detailCard(title: "Match", accent: DeskTheme.result(bet.result)) {
            detailRow(label: "Match", value: bet.match ?? "—")
            detailRow(label: "Sport", value: bet.sport ?? "—")
            detailRow(label: "Date", value: bet.date ?? "—")
            if let ko = bet.kickoff, !ko.isEmpty {
                detailRow(label: "Kickoff", value: ko)
            }
            TimelineView(.periodic(from: .now, by: 30)) { context in
                detailRow(
                    label: "Starts",
                    value: KickoffCountdown.label(for: bet, now: context.date)
                )
            }
        }
    }

    private var selectionSection: some View {
        detailCard(title: "Selection") {
            detailRow(label: "Selection", value: bet.selection ?? "—")
            detailRow(label: "Odds", value: oddsDisplay)
            detailRow(label: "Stake", value: DeskFormatters.nok(bet.stakeNok))
        }
    }

    private var statusSection: some View {
        detailCard(title: "Status") {
            HStack {
                Text("Result")
                    .font(DeskTypography.caption)
                    .foregroundStyle(DeskTheme.textDim)
                Spacer(minLength: DeskSpacing.s2)
                resultPill
            }
            detailRow(label: "Updated", value: bet.updatedAt ?? "—")
        }
    }

    private var identitySection: some View {
        detailCard(title: "Identity") {
            HStack(alignment: .firstTextBaseline, spacing: DeskSpacing.s2) {
                VStack(alignment: .leading, spacing: DeskSpacing.s1) {
                    Text("BET ID")
                        .font(DeskTypography.kpiLabel)
                        .foregroundStyle(DeskTheme.textDim)
                    Text(betIdDisplay)
                        .font(DeskTypography.monoFootnote)
                        .foregroundStyle(DeskTheme.text)
                        .textSelection(.enabled)
                }
                Spacer(minLength: 0)
                if let betId = bet.betId, !betId.isEmpty {
                    Button {
                        UIPasteboard.general.string = betId
                        copiedBetId = true
                        Task {
                            try? await Task.sleep(nanoseconds: 1_500_000_000)
                            copiedBetId = false
                        }
                    } label: {
                        Label(
                            copiedBetId ? "Copied" : "Copy",
                            systemImage: copiedBetId ? "checkmark" : "doc.on.doc"
                        )
                        .font(.caption.weight(.semibold))
                    }
                    .buttonStyle(.bordered)
                    .tint(DeskTheme.accent)
                    .accessibilityIdentifier("pending.detail.copyBetId")
                    .accessibilityLabel(copiedBetId ? "Bet id copied" : "Copy bet id")
                }
            }
        }
    }

    private var deskContextSection: some View {
        detailCard(title: "Desk at last sync") {
            if let desk {
                detailRow(label: "Equity", value: DeskFormatters.nok(desk.equityNok))
                detailRow(
                    label: "Open risk",
                    value: DeskFormatters.nok(desk.pendingAtRiskNok ?? desk.openPendingRiskNok)
                )
                detailRow(label: "Remaining", value: DeskFormatters.nok(desk.remainingRiskNok))
                detailRow(label: "Phase", value: phaseDisplay(desk))
                HStack {
                    Text("Gate")
                        .font(DeskTypography.caption)
                        .foregroundStyle(DeskTheme.textDim)
                    Spacer(minLength: DeskSpacing.s2)
                    StatusPill(
                        status: RiskGateStatus.resolve(
                            stopped: desk.stopped,
                            freeze: desk.freeze,
                            canBet: desk.canBet
                        )
                    )
                }
                if let generated = desk.generatedAt, !generated.isEmpty {
                    TimelineView(.periodic(from: .now, by: 60)) { context in
                        detailRow(
                            label: "Generated",
                            value: DeskFormatters.relativeTime(
                                generated,
                                relativeTo: context.date
                            )
                        )
                    }
                }
            } else {
                Text("No desk snapshot available")
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
            }
        }
    }

    // MARK: - Helpers

    private var oddsDisplay: String {
        guard let o = bet.decimalOdds else { return "—" }
        return String(format: "%.2f", o)
    }

    private var betIdDisplay: String {
        if let id = bet.betId, !id.isEmpty { return id }
        return "—"
    }

    private func phaseDisplay(_ desk: DeskSnapshot) -> String {
        let id = desk.phaseId?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let label = desk.phaseLabel?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if id.isEmpty && label.isEmpty { return "—" }
        if label.isEmpty { return id }
        if id.isEmpty { return label }
        if id == label { return id }
        return "\(id) · \(label)"
    }

    private var resultPill: some View {
        let text = (bet.result?.isEmpty == false) ? bet.result! : "—"
        let color = DeskTheme.result(bet.result)
        return HStack(spacing: DeskSpacing.s2) {
            Circle()
                .fill(color)
                .frame(width: 6, height: 6)
            Text(text)
                .font(.system(.caption2, design: .default).weight(.bold))
                .foregroundStyle(color)
                .lineLimit(1)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(
            Capsule()
                .fill(DeskTheme.surface2)
                .overlay(
                    Capsule()
                        .stroke(DeskTheme.border, lineWidth: 1)
                )
        )
        .accessibilityLabel("Result \(text)")
    }

    private func detailCard<Content: View>(
        title: String,
        accent: Color? = nil,
        @ViewBuilder content: @escaping () -> Content
    ) -> some View {
        DeskCard(accent: accent) {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                Text(title.uppercased())
                    .font(DeskTypography.sectionLabel)
                    .foregroundStyle(DeskTheme.textDim)
                    .accessibilityAddTraits(.isHeader)
                content()
            }
        }
    }

    private func detailRow(label: String, value: String) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label)
                .font(DeskTypography.caption)
                .foregroundStyle(DeskTheme.textDim)
            Spacer(minLength: DeskSpacing.s2)
            Text(value)
                .font(.subheadline)
                .foregroundStyle(DeskTheme.text)
                .multilineTextAlignment(.trailing)
                .textSelection(.enabled)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(label), \(value)")
    }
}
