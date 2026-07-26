import SwiftUI

/// Frozen five-tab destinations for the Legacy shell (includes Settings as a peer tab).
/// Redesign uses `DeskTab` (four content tabs only) + gear/sheet for Settings.
enum LegacyDeskTab: Int, CaseIterable, Hashable {
    case desk = 0
    case charts
    case pending
    case slip
    case settings
}
