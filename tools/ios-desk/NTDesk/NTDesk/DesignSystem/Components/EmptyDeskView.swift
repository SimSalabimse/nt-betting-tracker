import SwiftUI

/// First-run / empty-cache guidance. Primary action uses `openSettings` (or an explicit callback).
/// Built on HIG `ContentUnavailableView` with desk-night tokens.
struct EmptyDeskView: View {
    @Environment(\.openSettings) private var openSettings

    var title: String = "Connect to your desk PC"
    var systemImage: String = "desktopcomputer"
    var message: String =
        "Set the PC base URL (LAN IP or Tailscale 100.x), start mobile-view with -Lan, then sync. View-only — place and settle stay on the desk PC."
    var showOpenSettings: Bool = true
    /// Optional override (e.g. Legacy tab switch). When nil, uses `EnvironmentValues.openSettings`.
    var onOpenSettings: (() -> Void)?

    var body: some View {
        ContentUnavailableView {
            Label {
                Text(title)
                    .font(DeskTypography.sectionTitle)
                    .foregroundStyle(DeskTheme.text)
                    .multilineTextAlignment(.center)
            } icon: {
                Image(systemName: systemImage)
                    .font(.largeTitle.weight(.medium))
                    .symbolRenderingMode(.hierarchical)
                    .foregroundStyle(DeskTheme.accent)
                    .accessibilityHidden(true)
            }
        } description: {
            Text(message)
                .font(.subheadline)
                .foregroundStyle(DeskTheme.textMuted)
                .multilineTextAlignment(.center)
        } actions: {
            if showOpenSettings {
                Button("Open Settings") {
                    if let onOpenSettings {
                        onOpenSettings()
                    } else {
                        openSettings()
                    }
                }
                .buttonStyle(.borderedProminent)
                .tint(DeskTheme.accent)
                .controlSize(.large)
                .accessibilityLabel("Open Settings")
                .accessibilityHint("Opens Settings to set the PC base URL")
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, DeskSpacing.s4)
        // Keep children separate so "Open Settings" remains an activatable VoiceOver control.
        .accessibilityElement(children: .contain)
    }
}

/// Themed empty / unavailable chrome (HIG ContentUnavailable pattern, desk tokens).
/// Use for no-data, no-search-match, and secondary empty states — not first-run connect
/// (prefer `EmptyDeskView` for Settings CTA).
struct DeskContentUnavailable: View {
    var title: String
    var systemImage: String
    var description: String
    /// Optional override; default combines title + description.
    var accessibilityLabelText: String? = nil

    var body: some View {
        ContentUnavailableView {
            Label {
                Text(title)
                    .font(DeskTypography.sectionTitle)
                    .foregroundStyle(DeskTheme.text)
                    .multilineTextAlignment(.center)
            } icon: {
                Image(systemName: systemImage)
                    .font(.largeTitle.weight(.medium))
                    .symbolRenderingMode(.hierarchical)
                    .foregroundStyle(DeskTheme.textDim)
                    .accessibilityHidden(true)
            }
        } description: {
            Text(description)
                .font(.subheadline)
                .foregroundStyle(DeskTheme.textMuted)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, DeskSpacing.s4)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilityLabelText ?? "\(title). \(description)")
    }
}
