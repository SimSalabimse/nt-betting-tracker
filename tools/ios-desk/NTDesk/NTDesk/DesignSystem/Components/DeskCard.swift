import SwiftUI

/// Elevated surface container — maps desktop `card()` / `panel_surface`.
/// Optional left accent rail for hierarchy.
struct DeskCard<Content: View>: View {
    var accent: Color? = nil
    var padding: CGFloat = DeskSpacing.s4
    @ViewBuilder var content: () -> Content

    var body: some View {
        Group {
            if let accent {
                HStack(alignment: .top, spacing: 0) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(accent)
                        .frame(width: 3)
                    content()
                        .padding(.leading, DeskSpacing.s3)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(.top, padding)
                .padding(.trailing, padding)
                .padding(.bottom, padding)
            } else {
                content()
                    .padding(padding)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .background(
            RoundedRectangle(cornerRadius: DeskSpacing.radius)
                .fill(DeskTheme.surfaceElev)
                .overlay(
                    RoundedRectangle(cornerRadius: DeskSpacing.radius)
                        .stroke(DeskTheme.borderSoft, lineWidth: 1)
                )
        )
    }
}
