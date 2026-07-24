import SwiftUI

// Source of truth: desktop/theme.py (“desk night”)
// Prefer Font.TextStyle over fixed sizes so Dynamic Type scales.

enum DeskTypography {
    /// Page / navigation title (desktop 24 W800).
    static var pageTitle: Font {
        .system(.title, design: .default).weight(.bold)
    }

    /// Section title (desktop 15 W700).
    static var sectionTitle: Font {
        .headline
    }

    /// Uppercase muted mono section label (desktop 11 mono).
    static var sectionLabel: Font {
        .system(.caption, design: .monospaced).weight(.bold)
    }

    /// KPI numeric value (desktop 22 W700 mono → title2 monospaced bold).
    static var kpiValue: Font {
        .system(.title2, design: .monospaced).weight(.bold)
    }

    /// Optional hero equity (desktop 36 mono).
    static var heroValue: Font {
        .system(.largeTitle, design: .monospaced).weight(.bold)
    }

    /// Muted body / caption (desktop ~12).
    static var caption: Font {
        .caption
    }

    /// Slip / dense monospaced footnote.
    static var monoFootnote: Font {
        .system(.footnote, design: .monospaced)
    }

    /// KPI label (desktop 10 mono uppercased).
    static var kpiLabel: Font {
        .system(.caption2, design: .monospaced).weight(.bold)
    }
}
