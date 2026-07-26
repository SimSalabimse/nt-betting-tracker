import SwiftUI

/// Injected so EmptyDeskView / CTAs never depend on a Settings tab index.
struct OpenSettingsAction {
    let handler: () -> Void
    func callAsFunction() { handler() }
}

private struct OpenSettingsKey: EnvironmentKey {
    static let defaultValue = OpenSettingsAction(handler: {})
}

extension EnvironmentValues {
    var openSettings: OpenSettingsAction {
        get { self[OpenSettingsKey.self] }
        set { self[OpenSettingsKey.self] = newValue }
    }
}
