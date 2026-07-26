import Foundation

/// Saved PC connection endpoint. Shared by Redesign Settings and SyncService multi-profile.
/// Legacy continues to use `SyncService.baseURLString` (facade over the default profile).
struct ConnectionProfile: Identifiable, Codable, Equatable, Hashable {
    var id: UUID
    var name: String
    var baseURLString: String
    var createdAt: Date
    /// ISO-8601 string when this profile last synced successfully (optional).
    var lastSuccessAt: String?
    var isDefault: Bool

    init(
        id: UUID = UUID(),
        name: String,
        baseURLString: String,
        createdAt: Date = Date(),
        lastSuccessAt: String? = nil,
        isDefault: Bool = false
    ) {
        self.id = id
        self.name = name
        self.baseURLString = baseURLString
        self.createdAt = createdAt
        self.lastSuccessAt = lastSuccessAt
        self.isDefault = isDefault
    }
}
