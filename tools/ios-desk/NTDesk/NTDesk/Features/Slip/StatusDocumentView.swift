import SwiftUI

struct StatusDocumentView: View {
    let statusExcerpt: String

    private var sections: [StatusSection] { Self.splitSections(statusExcerpt) }

    var body: some View {
        DeskCard {
            VStack(alignment: .leading, spacing: DeskSpacing.s2) {
                Text("STATUS")
                    .font(DeskTypography.sectionLabel)
                    .foregroundStyle(DeskTheme.textDim)
                    .tracking(0.6)
                    .accessibilityAddTraits(.isHeader)

                if sections.count >= 2 {
                    ForEach(sections) { section in
                        DisclosureGroup {
                            MarkdownFallbackView(text: section.body, monospacedTables: false)
                                .padding(.top, DeskSpacing.s1)
                        } label: {
                            Text(section.title)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(DeskTheme.text)
                        }
                        .tint(DeskTheme.accent)
                    }
                } else if let only = sections.first {
                    if only.title != "STATUS" {
                        Text(only.title)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(DeskTheme.text)
                    }
                    MarkdownFallbackView(text: only.body.isEmpty ? statusExcerpt : only.body)
                } else {
                    MarkdownFallbackView(text: statusExcerpt)
                }
            }
        }
    }

    struct StatusSection: Identifiable {
        var id: String { title + String(body.prefix(24)) }
        var title: String
        var body: String
    }

    static func splitSections(_ text: String) -> [StatusSection] {
        let lines = text.replacingOccurrences(of: "\r\n", with: "\n").components(separatedBy: "\n")
        var result: [StatusSection] = []
        var currentTitle: String?
        var bodyLines: [String] = []

        func flush() {
            guard let title = currentTitle else {
                let joined = bodyLines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
                if !joined.isEmpty { result.append(StatusSection(title: "STATUS", body: joined)) }
                bodyLines = []
                return
            }
            let body = bodyLines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
            result.append(StatusSection(title: title, body: body))
            bodyLines = []
        }

        var sawHeading = false
        for line in lines {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.hasPrefix("## ") {
                flush()
                currentTitle = String(trimmed.dropFirst(3)).trimmingCharacters(in: .whitespaces)
                sawHeading = true
            } else {
                bodyLines.append(line)
            }
        }
        flush()
        if !sawHeading { return [StatusSection(title: "STATUS", body: text)] }
        return result
    }
}
