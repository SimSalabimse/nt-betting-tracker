import SwiftUI

// Source of truth: desktop/theme.py (“desk night”)
// Keep hex values in sync with desktop/theme.py.
// Asserted in NTDeskTests.DeskThemeTokenTests when test target exists.

enum DeskTheme {
    // Surfaces
    static let bg          = Color(hex: 0x0B0D12)   // BG
    static let surface     = Color(hex: 0x12161F)   // SURFACE
    static let surfaceElev = Color(hex: 0x171C27)   // SURFACE_ELEV
    static let surface2    = Color(hex: 0x1C2330)   // SURFACE_2
    static let surface3    = Color(hex: 0x262E3D)   // SURFACE_3
    static let rail        = Color(hex: 0x1A2030)   // RAIL

    // Borders
    static let border      = Color(hex: 0x2C3548)
    static let borderSoft  = Color(hex: 0x232A38)
    static let borderFocus = Color(hex: 0x4A5568)

    // Text
    static let text        = Color(hex: 0xF3F5F9)
    static let textMuted   = Color(hex: 0x8B95A8)
    static let textDim     = Color(hex: 0x5C6678)

    // Semantic
    static let accent      = Color(hex: 0xE8A317)   // brand amber
    /// Desktop ACCENT_SOFT = "#E8A31728" → alpha 0x28/255 ≈ 0.15686
    static let accentSoft  = Color(hex: 0xE8A317, opacity: Double(0x28) / 255.0)
    static let accentDim   = Color(hex: 0xB87E10)
    static let profit      = Color(hex: 0x3DDC97)
    static let loss        = Color(hex: 0xFF6B7A)
    static let pending     = Color(hex: 0xF5C542)
    static let info        = Color(hex: 0x7C9CFF)

    static func pl(_ value: Double?) -> Color {
        guard let v = value else { return textMuted }
        if v > 0.005 { return profit }
        if v < -0.005 { return loss }
        return textMuted
    }

    static func result(_ result: String?) -> Color {
        switch (result ?? "").trimmingCharacters(in: .whitespaces) {
        case "Win": return profit
        case "Loss": return loss
        case "Pending": return pending
        default: return textMuted
        }
    }
}
