import Foundation
import Network
import Combine

/// Publishes whether the device currently has a usable network path (Wi‑Fi/cellular/etc.).
@MainActor
final class NetworkPathMonitor: ObservableObject {
    static let shared = NetworkPathMonitor()

    @Published private(set) var isSatisfied: Bool = true
    @Published private(set) var isExpensive: Bool = false
    @Published private(set) var isConstrained: Bool = false
    /// Human label: "Wi‑Fi", "Cellular", "Offline", …
    @Published private(set) var pathLabel: String = "Unknown"

    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "ntdesk.networkpath")

    private init() {
        monitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor in
                self?.apply(path)
            }
        }
        monitor.start(queue: queue)
    }

    private func apply(_ path: NWPath) {
        isSatisfied = path.status == .satisfied
        isExpensive = path.isExpensive
        isConstrained = path.isConstrained
        if path.status != .satisfied {
            pathLabel = "Offline"
        } else if path.usesInterfaceType(.wifi) {
            pathLabel = "Wi‑Fi"
        } else if path.usesInterfaceType(.cellular) {
            pathLabel = "Cellular"
        } else if path.usesInterfaceType(.wiredEthernet) {
            pathLabel = "Ethernet"
        } else if path.usesInterfaceType(.other) {
            pathLabel = "Other"
        } else {
            pathLabel = "Online"
        }
    }
}
