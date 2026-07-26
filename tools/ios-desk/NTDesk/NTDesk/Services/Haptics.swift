import UIKit

/// Sparse haptics for desk feedback (success sync, errors, selection).
enum Haptics {
    private static let light = UIImpactFeedbackGenerator(style: .light)
    private static let medium = UIImpactFeedbackGenerator(style: .medium)
    private static let notify = UINotificationFeedbackGenerator()

    static func prepare() {
        light.prepare()
        medium.prepare()
        notify.prepare()
    }

    static func lightImpact() {
        light.impactOccurred()
    }

    static func mediumImpact() {
        medium.impactOccurred()
    }

    static func success() {
        notify.notificationOccurred(.success)
    }

    static func warning() {
        notify.notificationOccurred(.warning)
    }

    static func error() {
        notify.notificationOccurred(.error)
    }
}
