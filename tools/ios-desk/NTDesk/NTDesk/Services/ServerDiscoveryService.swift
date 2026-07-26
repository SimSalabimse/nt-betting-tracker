import Foundation
import Network
import os

// MARK: - DiscoverySession

/// Normative probe session: short timeouts, high concurrency, **not** DeskAPIClient’s 8s/12s.
struct DiscoverySession: Equatable, Sendable {
    /// Dedicated ephemeral session — NOT DeskAPIClient timeouts.
    static func makeURLSession(protocolClasses: [AnyClass]? = nil) -> URLSession {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = 0.4 // 400ms per host
        cfg.timeoutIntervalForResource = 0.5
        cfg.waitsForConnectivity = false
        cfg.httpMaximumConnectionsPerHost = 1
        if let protocolClasses {
            cfg.protocolClasses = protocolClasses
        }
        return URLSession(configuration: cfg)
    }

    var port: Int = 8787
    var maxHosts: Int = 256
    var maxConcurrent: Int = 32
    /// Wall-clock budget for the whole scan; outstanding probes are cancelled after this.
    var overallBudgetNanoseconds: UInt64 = 8_000_000_000 // 8s

    static let `default` = DiscoverySession()
}

// MARK: - Models

struct DiscoveredServer: Identifiable, Equatable, Hashable, Sendable {
    /// Stable id = base URL string used for profiles.
    var id: String { baseURLString }
    let host: String
    let port: Int
    let latencyMs: Int
    let baseURLString: String
    /// Soft preference when health JSON includes `view_only` (not required).
    let viewOnly: Bool?
}

/// IPv4 interface snapshot used to plan host lists (testable without getifaddrs).
struct DiscoveryInterfaceIPv4: Equatable, Sendable {
    let address: String
    /// Prefix length 0…32 (e.g. 24 for a typical home LAN).
    let prefixLength: Int
}

enum DiscoveryPathKind: Equatable, Sendable {
    case wifiOrWired
    case cellularOrConstrained
    case unsatisfied
    case unknown
}

// MARK: - Pure probe / host-plan helpers (unit-tested)

enum DiscoveryProbeLogic {
    /// Success: HTTP 2xx **and** JSON object with `ok == true` (bool). Soft-read `view_only` when present.
    static func evaluateHealthResponse(statusCode: Int, data: Data) -> (ok: Bool, viewOnly: Bool?) {
        guard (200...299).contains(statusCode) else { return (false, nil) }
        guard
            let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return (false, nil)
        }
        let okFlag: Bool = {
            if let b = obj["ok"] as? Bool { return b }
            if let n = obj["ok"] as? NSNumber { return n.boolValue }
            return false
        }()
        guard okFlag else { return (false, nil) }
        let viewOnly: Bool? = {
            if let b = obj["view_only"] as? Bool { return b }
            if let n = obj["view_only"] as? NSNumber { return n.boolValue }
            return nil
        }()
        return (true, viewOnly)
    }

    /// Whether a host may be **probed** (cleartext allowlist). Public hosts must never be requested.
    static func isProbeHostAllowed(_ host: String) -> Bool {
        PrivateHostPolicy.isCleartextAllowed(host: host)
    }

    /// Subnet expansion is **RFC1918 only** — never full Tailscale CGNAT 100.64/10, never public.
    static func isScannableLANSubnetHost(_ host: String) -> Bool {
        let parts = host.split(separator: ".").compactMap { Int($0) }
        guard parts.count == 4, parts.allSatisfy({ (0...255).contains($0) }) else { return false }
        let a = parts[0], b = parts[1]
        if a == 10 { return true }
        if a == 192 && b == 168 { return true }
        if a == 172 && (16...31).contains(b) { return true }
        return false
    }

    /// Build ≤ `maxHosts` probe targets from private interfaces.
    /// - Full **/24** (up to 256) when the planned set fits.
    /// - Larger subnets: sample interface ±32, `.1`, and optional last-success host.
    /// - Skips Tailscale CGNAT expansion and loopback-only interfaces.
    static func planHosts(
        interfaces: [DiscoveryInterfaceIPv4],
        lastSuccessHost: String?,
        maxHosts: Int = 256
    ) -> [String] {
        var ordered: [String] = []
        var seen = Set<String>()

        func append(_ host: String) {
            guard ordered.count < maxHosts else { return }
            guard isProbeHostAllowed(host), isScannableLANSubnetHost(host) else { return }
            if seen.insert(host).inserted {
                ordered.append(host)
            }
        }

        for iface in interfaces {
            guard isScannableLANSubnetHost(iface.address) else { continue }
            let parts = iface.address.split(separator: ".").compactMap { Int($0) }
            guard parts.count == 4 else { continue }

            let prefix = min(32, max(0, iface.prefixLength))
            let hostBits = 32 - prefix
            let hostCount = hostBits >= 32 ? UInt64(maxHosts) + 1 : (UInt64(1) << hostBits)

            if hostCount <= UInt64(maxHosts), hostBits <= 8 {
                // Full subnet (typical /24 → 256 addresses).
                let network = ipv4UInt32(parts) & prefixMask(prefix)
                let count = Int(hostCount)
                for i in 0..<count {
                    guard ordered.count < maxHosts else { break }
                    let ip = network &+ UInt32(i)
                    append(stringFromIPv4(ip))
                }
            } else {
                // Oversized: sample around interface, gateway-ish .1, last success.
                let base = ipv4UInt32(parts)
                append(iface.address)
                // .1 in same /24-ish last octet family
                append("\(parts[0]).\(parts[1]).\(parts[2]).1")
                for delta in 1...32 {
                    append(stringFromIPv4(base &+ UInt32(delta)))
                    append(stringFromIPv4(base &- UInt32(delta)))
                }
            }
        }

        if let last = lastSuccessHost?.trimmingCharacters(in: .whitespacesAndNewlines), !last.isEmpty {
            append(last)
        }

        return ordered
    }

    static func baseURLString(host: String, port: Int) -> String {
        "http://\(host):\(port)"
    }

    // MARK: IPv4 math

    private static func ipv4UInt32(_ parts: [Int]) -> UInt32 {
        (UInt32(parts[0]) << 24) | (UInt32(parts[1]) << 16) | (UInt32(parts[2]) << 8) | UInt32(parts[3])
    }

    private static func prefixMask(_ prefix: Int) -> UInt32 {
        if prefix <= 0 { return 0 }
        if prefix >= 32 { return 0xffff_ffff }
        return 0xffff_ffff << (32 - prefix)
    }

    private static func stringFromIPv4(_ value: UInt32) -> String {
        let a = (value >> 24) & 0xff
        let b = (value >> 16) & 0xff
        let c = (value >> 8) & 0xff
        let d = value & 0xff
        return "\(a).\(b).\(c).\(d)"
    }
}

// MARK: - Interface enumeration (production)

enum DiscoveryInterfaceEnumerator {
    /// Non-loopback IPv4 + prefix via `getifaddrs`. Excludes loopback; includes all other up IPv4.
    static func enumerateIPv4() -> [DiscoveryInterfaceIPv4] {
        var result: [DiscoveryInterfaceIPv4] = []
        var ifaddrPtr: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifaddrPtr) == 0, let first = ifaddrPtr else { return [] }
        defer { freeifaddrs(first) }

        var ptr: UnsafeMutablePointer<ifaddrs>? = first
        while let iface = ptr {
            defer { ptr = iface.pointee.ifa_next }
            let flags = Int32(iface.pointee.ifa_flags)
            guard (flags & IFF_UP) != 0 else { continue }
            guard (flags & IFF_LOOPBACK) == 0 else { continue }
            guard let addr = iface.pointee.ifa_addr, addr.pointee.sa_family == UInt8(AF_INET) else { continue }

            var hostname = [CChar](repeating: 0, count: Int(NI_MAXHOST))
            let saLen = socklen_t(addr.pointee.sa_len)
            guard getnameinfo(
                addr,
                saLen,
                &hostname,
                socklen_t(hostname.count),
                nil,
                0,
                NI_NUMERICHOST
            ) == 0 else { continue }
            let address = String(cString: hostname)

            var prefix = 24
            if let netmask = iface.pointee.ifa_netmask {
                prefix = prefixLength(from: netmask)
            }
            result.append(DiscoveryInterfaceIPv4(address: address, prefixLength: prefix))
        }
        return result
    }

    private static func prefixLength(from netmask: UnsafeMutablePointer<sockaddr>) -> Int {
        guard netmask.pointee.sa_family == UInt8(AF_INET) else { return 24 }
        let sin = netmask.withMemoryRebound(to: sockaddr_in.self, capacity: 1) { $0.pointee }
        var mask = UInt32(bigEndian: sin.sin_addr.s_addr)
        var count = 0
        while mask != 0 {
            count += Int(mask & 1)
            mask >>= 1
        }
        return count
    }
}

// MARK: - Service

/// User-initiated LAN discovery: concurrent `GET /api/health` probes on private /24, confirm-before-connect.
@MainActor
final class ServerDiscoveryService: ObservableObject {
    private static let log = Logger(subsystem: "app.ntdesk", category: "discovery")

    @Published private(set) var candidates: [DiscoveredServer] = []
    @Published private(set) var isScanning = false
    @Published private(set) var statusMessage: String?
    @Published private(set) var pathKind: DiscoveryPathKind = .unknown
    @Published private(set) var hostsPlanned = 0
    @Published private(set) var hostsProbed = 0
    @Published private(set) var lastScanDurationMs: Int?

    /// Port used for the next / current scan (UI-overridable).
    @Published var port: Int = 8787

    var pathAllowsDiscovery: Bool {
        pathKind == .wifiOrWired || pathKind == .unknown
    }

    /// Injected for tests (URLProtocol). Production uses `DiscoverySession.makeURLSession()`.
    var makeSession: () -> URLSession = { DiscoverySession.makeURLSession() }
    /// Injected host list; when nil, plan from live interfaces.
    var interfaceProvider: () -> [DiscoveryInterfaceIPv4] = { DiscoveryInterfaceEnumerator.enumerateIPv4() }
    /// Optional last-success host hint (from default profile).
    var lastSuccessHostProvider: () -> String? = { nil }
    /// Override path kind for tests (skips NWPathMonitor when set).
    var pathKindOverride: DiscoveryPathKind?

    private var pathMonitor: NWPathMonitor?
    private var scanTask: Task<Void, Never>?
    private let pathQueue = DispatchQueue(label: "app.ntdesk.discovery.path")

    init(startPathMonitor: Bool = true) {
        if startPathMonitor {
            startMonitoringPath()
        }
    }

    deinit {
        pathMonitor?.cancel()
        scanTask?.cancel()
    }

    // MARK: Path

    func startMonitoringPath() {
        pathMonitor?.cancel()
        let monitor = NWPathMonitor()
        pathMonitor = monitor
        monitor.pathUpdateHandler = { [weak self] path in
            let kind = Self.classify(path: path)
            Task { @MainActor in
                self?.pathKind = kind
            }
        }
        monitor.start(queue: pathQueue)
    }

    nonisolated static func classify(path: NWPath) -> DiscoveryPathKind {
        guard path.status == .satisfied else { return .unsatisfied }
        if path.isExpensive || path.isConstrained {
            // Cellular / constrained: discovery UI disabled; saved profiles only.
            return .cellularOrConstrained
        }
        if path.usesInterfaceType(.cellular) {
            return .cellularOrConstrained
        }
        if path.usesInterfaceType(.wifi) || path.usesInterfaceType(.wiredEthernet) {
            return .wifiOrWired
        }
        // Other satisfied (e.g. other) — allow probe of RFC1918 if interfaces exist.
        return .wifiOrWired
    }

    /// UI helper for idle / error copy without opening a write path for scan results.
    func setStatusMessage(_ message: String?) {
        statusMessage = message
    }

    // MARK: Scan lifecycle

    func cancelScan() {
        scanTask?.cancel()
        scanTask = nil
        if isScanning {
            isScanning = false
            statusMessage = "Scan cancelled"
        }
    }

    /// User-initiated only. Does **not** fetch `/api/desk`.
    func startScan(session: DiscoverySession = .default) {
        cancelScan()
        candidates = []
        hostsProbed = 0
        hostsPlanned = 0
        lastScanDurationMs = nil

        let kind = pathKindOverride ?? pathKind
        if kind == .cellularOrConstrained {
            statusMessage = "Discovery isn’t available on cellular. Use a saved profile or connect on Wi‑Fi."
            return
        }
        if kind == .unsatisfied {
            statusMessage = "No network. Connect to Wi‑Fi and try again, or use a saved profile."
            return
        }

        let port = max(1, min(65535, self.port))
        let interfaces = interfaceProvider()
        let lastHost = lastSuccessHostProvider()
        let hosts = DiscoveryProbeLogic.planHosts(
            interfaces: interfaces,
            lastSuccessHost: lastHost,
            maxHosts: session.maxHosts
        )
        hostsPlanned = hosts.count

        guard !hosts.isEmpty else {
            statusMessage = "No private LAN interface found. Enter a URL manually, or use Tailscale (manual profile — no CGNAT scan)."
            return
        }

        isScanning = true
        statusMessage = "Scanning \(hosts.count) hosts on port \(port)…"
        Self.log.info("discovery start hosts=\(hosts.count, privacy: .public) port=\(port, privacy: .public)")

        let budget = session.overallBudgetNanoseconds
        let maxConcurrent = max(1, session.maxConcurrent)
        let makeSession = self.makeSession

        scanTask = Task { [weak self] in
            let started = ContinuousClock.now
            let hits = await Self.runProbes(
                hosts: hosts,
                port: port,
                maxConcurrent: maxConcurrent,
                budgetNanoseconds: budget,
                makeSession: makeSession,
                onProgress: { probed in
                    Task { @MainActor in
                        self?.hostsProbed = probed
                    }
                }
            )
            let elapsed = started.duration(to: .now)
            let ms = Int(elapsed.components.seconds * 1000 + elapsed.components.attoseconds / 1_000_000_000_000_000)
            await MainActor.run {
                guard let self else { return }
                self.isScanning = false
                self.scanTask = nil
                self.lastScanDurationMs = ms
                // Sort by latency, then host
                self.candidates = hits.sorted {
                    if $0.latencyMs != $1.latencyMs { return $0.latencyMs < $1.latencyMs }
                    return $0.host < $1.host
                }
                if hits.isEmpty {
                    self.statusMessage = "No desk servers found (health ok==true). Check mobile-view -Lan, firewall, same Wi‑Fi."
                } else {
                    self.statusMessage = "Found \(hits.count) server\(hits.count == 1 ? "" : "s"). Confirm before connecting."
                }
                Self.log.info(
                    "discovery done hits=\(hits.count, privacy: .public) probed=\(self.hostsProbed, privacy: .public) ms=\(ms, privacy: .public)"
                )
            }
        }
    }

    /// Concurrent health probes with a concurrency cap and overall budget. Never calls `/api/desk`.
    nonisolated static func runProbes(
        hosts: [String],
        port: Int,
        maxConcurrent: Int,
        budgetNanoseconds: UInt64,
        makeSession: @escaping () -> URLSession,
        onProgress: @escaping @Sendable (Int) -> Void
    ) async -> [DiscoveredServer] {
        let session = makeSession()
        defer { session.finishTasksAndInvalidate() }

        let deadline = ContinuousClock.now + .nanoseconds(Int64(min(budgetNanoseconds, UInt64(Int64.max))))
        let results = ProbeResultBox()
        let progress = ProbeProgressBox()

        await withTaskGroup(of: DiscoveredServer?.self) { group in
            var nextIndex = 0
            var inFlight = 0

            func enqueueIfPossible() {
                while inFlight < maxConcurrent, nextIndex < hosts.count {
                    if Task.isCancelled { return }
                    if ContinuousClock.now >= deadline { return }
                    let host = hosts[nextIndex]
                    nextIndex += 1
                    // Policy gate before any request.
                    guard DiscoveryProbeLogic.isProbeHostAllowed(host) else {
                        let n = progress.increment()
                        onProgress(n)
                        continue
                    }
                    // Never expand/request non-LAN public — double gate.
                    guard DiscoveryProbeLogic.isScannableLANSubnetHost(host)
                            || PrivateHostPolicy.isCleartextAllowed(host: host) else {
                        let n = progress.increment()
                        onProgress(n)
                        continue
                    }
                    // Discovery only probes scannable RFC1918 planned hosts (planHosts already filters).
                    inFlight += 1
                    group.addTask {
                        let server = await Self.probeOne(
                            host: host,
                            port: port,
                            session: session,
                            deadline: deadline
                        )
                        let n = progress.increment()
                        onProgress(n)
                        return server
                    }
                }
            }

            enqueueIfPossible()
            while let result = await group.next() {
                inFlight -= 1
                if let result {
                    await results.append(result)
                }
                if Task.isCancelled || ContinuousClock.now >= deadline {
                    group.cancelAll()
                    break
                }
                enqueueIfPossible()
            }
        }

        return await results.snapshot()
    }

    nonisolated private static func probeOne(
        host: String,
        port: Int,
        session: URLSession,
        deadline: ContinuousClock.Instant
    ) async -> DiscoveredServer? {
        if Task.isCancelled || ContinuousClock.now >= deadline { return nil }
        // Final allowlist check before request.
        guard DiscoveryProbeLogic.isProbeHostAllowed(host) else { return nil }

        let baseStr = DiscoveryProbeLogic.baseURLString(host: host, port: port)
        guard let base = PrivateHostPolicy.normalizeBaseURL(baseStr) else { return nil }
        let url = base.appendingPathComponent("api/health")

        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.timeoutInterval = 0.4

        let t0 = ContinuousClock.now
        do {
            let (data, resp) = try await session.data(for: req)
            let elapsed = t0.duration(to: .now)
            let ms = max(
                0,
                Int(elapsed.components.seconds * 1000 + elapsed.components.attoseconds / 1_000_000_000_000_000)
            )
            let code = (resp as? HTTPURLResponse)?.statusCode ?? -1
            let eval = DiscoveryProbeLogic.evaluateHealthResponse(statusCode: code, data: data)
            guard eval.ok else { return nil }
            return DiscoveredServer(
                host: host,
                port: port,
                latencyMs: ms,
                baseURLString: base.absoluteString.hasSuffix("/")
                    ? String(base.absoluteString.dropLast())
                    : base.absoluteString,
                viewOnly: eval.viewOnly
            )
        } catch {
            return nil
        }
    }
}

// MARK: - Concurrency helpers

private actor ProbeResultBox {
    private var items: [DiscoveredServer] = []
    func append(_ item: DiscoveredServer) { items.append(item) }
    func snapshot() -> [DiscoveredServer] { items }
}

private final class ProbeProgressBox: @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0
    func increment() -> Int {
        lock.lock()
        defer { lock.unlock() }
        count += 1
        return count
    }
}
