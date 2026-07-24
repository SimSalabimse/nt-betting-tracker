import SwiftUI

extension Color {
    /// sRGB from 0xRRGGBB (24-bit). Alpha via `opacity` (default 1).
    /// Not 0xAARRGGBB — use opacity for alpha (matches ACCENT_SOFT encoding).
    init(hex: UInt32, opacity: Double = 1) {
        let r = Double((hex >> 16) & 0xFF) / 255
        let g = Double((hex >> 8) & 0xFF) / 255
        let b = Double(hex & 0xFF) / 255
        self.init(.sRGB, red: r, green: g, blue: b, opacity: opacity)
    }
}
