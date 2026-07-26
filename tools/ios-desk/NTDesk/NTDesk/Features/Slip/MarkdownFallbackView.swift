import SwiftUI

struct MarkdownFallbackView: View {
    let text: String
    var monospacedTables: Bool = true

    var body: some View {
        VStack(alignment: .leading, spacing: DeskSpacing.s2) {
            if monospacedTables, text.contains("|"), text.contains("---") {
                ScrollView(.horizontal, showsIndicators: true) {
                    Text(text)
                        .font(DeskTypography.monoFootnote)
                        .foregroundStyle(DeskTheme.text)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            } else if let attributed = try? AttributedString(
                markdown: text,
                options: AttributedString.MarkdownParsingOptions(interpretedSyntax: .inlineOnlyPreservingWhitespace)
            ) {
                Text(attributed)
                    .font(.footnote)
                    .foregroundStyle(DeskTheme.text)
                    .textSelection(.enabled)
            } else {
                Text(text)
                    .font(DeskTypography.monoFootnote)
                    .foregroundStyle(DeskTheme.text)
                    .textSelection(.enabled)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityLabel("Source text")
    }
}
