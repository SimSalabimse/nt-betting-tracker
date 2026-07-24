import CoreGraphics

// Source of truth: desktop/theme.py (“desk night”)

enum DeskSpacing {
    static let s1: CGFloat = 4
    static let s2: CGFloat = 8
    static let s3: CGFloat = 12
    static let s4: CGFloat = 16
    static let s5: CGFloat = 20
    static let s6: CGFloat = 24
    static let s7: CGFloat = 32
    static let s8: CGFloat = 40

    static let radius: CGFloat = 10      // desktop RADIUS
    static let radiusSM: CGFloat = 6     // RADIUS_SM
    static let radiusLG: CGFloat = 14    // RADIUS_LG
    /// Phone content padding (desktop CONTENT_PAD = 22).
    static let contentPad: CGFloat = 16
}
