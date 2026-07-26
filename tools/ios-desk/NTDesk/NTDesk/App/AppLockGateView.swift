import SwiftUI

/// Full-screen gate when optional app lock is enabled and the user has not authenticated.
struct AppLockGateView: View {
    @ObservedObject var appLock: AppLockService

    var body: some View {
        ZStack {
            DeskTheme.bg.ignoresSafeArea()
            VStack(spacing: DeskSpacing.s5) {
                Image(systemName: lockSymbol)
                    .font(.system(size: 48, weight: .medium))
                    .foregroundStyle(DeskTheme.accent)
                    .accessibilityHidden(true)

                Text("NT Desk is locked")
                    .font(DeskTypography.pageTitle)
                    .foregroundStyle(DeskTheme.text)

                Text("Use \(appLock.biometryLabel) to view your on-device desk cache.")
                    .font(.subheadline)
                    .foregroundStyle(DeskTheme.textMuted)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, DeskSpacing.s6)

                if let err = appLock.lastError {
                    Text(err)
                        .font(.caption)
                        .foregroundStyle(DeskTheme.pending)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, DeskSpacing.s5)
                }

                Button {
                    appLock.authenticate()
                } label: {
                    Label(
                        appLock.isAuthenticating ? "Authenticating…" : "Unlock with \(appLock.biometryLabel)",
                        systemImage: lockSymbol
                    )
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(DeskTheme.accent)
                .disabled(appLock.isAuthenticating)
                .padding(.horizontal, DeskSpacing.s6)
                .padding(.top, DeskSpacing.s3)
                .accessibilityIdentifier("appLock.unlock")
            }
            .padding(DeskSpacing.s6)
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("appLock.gate")
        .onAppear {
            // Auto-prompt once when the gate appears (cold launch / return from background).
            if appLock.isLocked && !appLock.isAuthenticating {
                appLock.authenticate()
            }
        }
    }

    private var lockSymbol: String {
        switch appLock.biometryLabel {
        case "Face ID":
            return "faceid"
        case "Touch ID":
            return "touchid"
        default:
            return "lock.fill"
        }
    }
}
