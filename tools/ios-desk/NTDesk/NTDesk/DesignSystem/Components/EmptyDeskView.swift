import SwiftUI

/// First-run / empty-cache guidance. Primary action switches to Settings via `DeskTab` (not a hard-coded index).
struct EmptyDeskView: View {
    var title: String = "Connect to your desk PC"
    var systemImage: String = "desktopcomputer"
    var message: String =
        "Set the PC base URL (LAN IP or Tailscale 100.x), start mobile-view with -Lan, then sync. View-only — place and settle stay on the desk PC."
    var showOpenSettings: Bool = true
    var onOpenSettings: (() -> Void)?

    var body: some View {
        VStack(spacing: DeskSpacing.s4) {
            Image(systemName: systemImage)
                .font(.system(size: 44, weight: .medium))
                .foregroundStyle(DeskTheme.accent)
                .accessibilityHidden(true)

            Text(title)
                .font(DeskTypography.sectionTitle)
                .foregroundStyle(DeskTheme.text)
                .multilineTextAlignment(.center)

            Text(message)
                .font(.subheadline)
                .foregroundStyle(DeskTheme.textMuted)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)

            if showOpenSettings, let onOpenSettings {
                Button("Open Settings", action: onOpenSettings)
                    .buttonStyle(.borderedProminent)
                    .tint(DeskTheme.accent)
                    .controlSize(.large)
                    .padding(.top, DeskSpacing.s2)
                    .accessibilityHint("Opens the Settings tab to set the PC base URL")
            }
        }
        .padding(DeskSpacing.s6)
        .frame(maxWidth: .infinity)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title). \(message)")
    }
}
