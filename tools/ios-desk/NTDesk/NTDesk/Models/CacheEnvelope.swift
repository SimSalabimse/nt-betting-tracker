import Foundation

/// On-disk envelope. `desk` is stored as a raw JSON object graph — never re-encoded via DeskSnapshot.
struct CacheEnvelope: Codable {
    var envelopeVersion: Int
    var cachedAt: String
    var sourceBaseURL: String
    var desk: AnyCodableJSON

    enum CodingKeys: String, CodingKey {
        case envelopeVersion = "envelope_version"
        case cachedAt = "cached_at"
        case sourceBaseURL = "source_base_url"
        case desk
    }
}

/// Type-erased JSON value for raw desk storage.
enum AnyCodableJSON: Codable, Equatable {
    case object([String: AnyCodableJSON])
    case array([AnyCodableJSON])
    case string(String)
    case number(Double)
    case bool(Bool)
    case null

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() {
            self = .null
        } else if let b = try? c.decode(Bool.self) {
            self = .bool(b)
        } else if let n = try? c.decode(Double.self) {
            self = .number(n)
        } else if let s = try? c.decode(String.self) {
            self = .string(s)
        } else if let a = try? c.decode([AnyCodableJSON].self) {
            self = .array(a)
        } else if let o = try? c.decode([String: AnyCodableJSON].self) {
            self = .object(o)
        } else {
            throw DecodingError.dataCorruptedError(in: c, debugDescription: "Unsupported JSON")
        }
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .null: try c.encodeNil()
        case .bool(let b): try c.encode(b)
        case .number(let n): try c.encode(n)
        case .string(let s): try c.encode(s)
        case .array(let a): try c.encode(a)
        case .object(let o): try c.encode(o)
        }
    }

    static func fromJSONObject(_ obj: Any) -> AnyCodableJSON {
        switch obj {
        case let d as [String: Any]:
            return .object(d.mapValues { fromJSONObject($0) })
        case let a as [Any]:
            return .array(a.map { fromJSONObject($0) })
        case let s as String:
            return .string(s)
        case let n as NSNumber:
            // Bool is bridged as NSNumber
            if CFGetTypeID(n) == CFBooleanGetTypeID() {
                return .bool(n.boolValue)
            }
            return .number(n.doubleValue)
        case let b as Bool:
            return .bool(b)
        case is NSNull:
            return .null
        default:
            return .null
        }
    }

    func toFoundation() -> Any {
        switch self {
        case .null: return NSNull()
        case .bool(let b): return b
        case .number(let n): return n
        case .string(let s): return s
        case .array(let a): return a.map { $0.toFoundation() }
        case .object(let o): return o.mapValues { $0.toFoundation() }
        }
    }
}
