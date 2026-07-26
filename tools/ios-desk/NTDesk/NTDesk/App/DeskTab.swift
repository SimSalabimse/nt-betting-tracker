import SwiftUI

/// Content tabs only. Settings is never a tab — always presented via `openSettings` sheet.
enum DeskTab: Hashable {
    case desk
    case charts
    case pending
    case slip
}
