import Foundation

/// Parses PLACE_THESE Markdown `text_excerpt` (and optional structured rows) into `PlaceTheseDocument`.
/// Normative grammar: `docs/IOS_DESK_HIG_REDESIGN.md` §6.
enum PlaceTheseParser {

    private static let phaseRegex: NSRegularExpression = {
        let pattern =
            #"Phase\s+\*{0,2}([A-Za-z0-9]+)\*{0,2}\s*\|\s*Equity\s+\*{0,2}([0-9.,]+)\*{0,2}\s*\|\s*Remaining risk\s+\*{0,2}([0-9.,]+)\*{0,2}\s*/\s*cap\s+\*{0,2}([0-9.,]+)\*{0,2}"#
        return try! NSRegularExpression(pattern: pattern, options: [.caseInsensitive])
    }()

    private static let separatorRowRegex: NSRegularExpression = {
        let pattern = #"^\s*\|?[\s|:\-]+\|?\s*$"#
        return try! NSRegularExpression(pattern: pattern, options: [])
    }()

    static func resolve(
        textExcerpt: String?,
        apiTitle: String?,
        summaryLine: String?,
        rowsPreview: [PlaceTheseRowPreview]
    ) -> PlaceTheseDocument {
        let objectBets = rowsPreview.compactMap { $0.asBet() }
        if !objectBets.isEmpty {
            return documentFromStructuredRows(
                bets: objectBets,
                textExcerpt: textExcerpt,
                apiTitle: apiTitle,
                summaryLine: summaryLine
            )
        }
        return parse(textExcerpt: textExcerpt, apiTitle: apiTitle, summaryLine: summaryLine)
    }

    static func parse(
        textExcerpt: String?,
        apiTitle: String? = nil,
        summaryLine: String? = nil
    ) -> PlaceTheseDocument {
        let text = textExcerpt ?? ""
        let lines = text
            .replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
            .components(separatedBy: "\n")

        var title = "PLACE_THESE"
        var titleLineIndex: Int?
        for (i, line) in lines.enumerated() {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.hasPrefix("# ") && !trimmed.hasPrefix("##") {
                title = String(trimmed.dropFirst(2)).trimmingCharacters(in: .whitespaces)
                titleLineIndex = i
                break
            }
        }
        if titleLineIndex == nil {
            if let apiTitle, !apiTitle.trimmingCharacters(in: .whitespaces).isEmpty {
                title = apiTitle.trimmingCharacters(in: .whitespaces)
            }
        }

        var phaseLine: String?
        var phaseId: String?
        var equityNok: Double?
        var remainingRiskNok: Double?
        var dailyCapNok: Double?
        var phaseLineIndex: Int?

        for (i, line) in lines.enumerated() {
            if let m = firstMatch(phaseRegex, in: line) {
                phaseLine = line.trimmingCharacters(in: .whitespaces)
                phaseId = group(m, 1, in: line)
                equityNok = parseNumber(group(m, 2, in: line))
                remainingRiskNok = parseNumber(group(m, 3, in: line))
                dailyCapNok = parseNumber(group(m, 4, in: line))
                phaseLineIndex = i
                break
            }
        }

        if phaseLine == nil, let summary = summaryLine?.trimmingCharacters(in: .whitespaces), !summary.isEmpty {
            phaseLine = summary
            if let m = firstMatch(phaseRegex, in: summary) {
                phaseId = group(m, 1, in: summary)
                equityNok = parseNumber(group(m, 2, in: summary))
                remainingRiskNok = parseNumber(group(m, 3, in: summary))
                dailyCapNok = parseNumber(group(m, 4, in: summary))
            }
        }

        guard let headerInfo = findTableHeader(in: lines) else {
            var failed = PlaceTheseDocument.failed
            failed.title = title
            failed.phaseLine = phaseLine
            failed.phaseId = phaseId
            failed.equityNok = equityNok
            failed.remainingRiskNok = remainingRiskNok
            failed.dailyCapNok = dailyCapNok
            return failed
        }

        let headerIndex = headerInfo.index
        let columnMap = headerInfo.map

        var notices: [String] = []
        let noticeStart = max((titleLineIndex ?? -1) + 1, (phaseLineIndex ?? -1) + 1, 0)
        if noticeStart < headerIndex {
            for i in noticeStart..<headerIndex {
                let t = lines[i].trimmingCharacters(in: .whitespaces)
                if t.isEmpty { continue }
                if t.hasPrefix("#") { continue }
                notices.append(t)
            }
        }

        var bets: [PlaceTheseBet] = []
        var partial = false
        var sawDataRow = false
        var emptySlipFromRow = false

        var i = headerIndex + 1
        while i < lines.count {
            if isSeparatorRow(lines[i]) {
                i += 1
                continue
            }
            break
        }

        while i < lines.count {
            let raw = lines[i]
            let trimmed = raw.trimmingCharacters(in: .whitespaces)
            if trimmed.isEmpty {
                i += 1
                if i < lines.count, lines[i].trimmingCharacters(in: .whitespaces).hasPrefix("##") {
                    break
                }
                continue
            }
            if trimmed.hasPrefix("##") { break }
            if isSeparatorRow(raw) {
                i += 1
                continue
            }
            guard trimmed.contains("|") else { break }

            sawDataRow = true
            let cells = splitTableCells(raw)
            if cells.count < columnMap.requiredCount {
                partial = true
                i += 1
                continue
            }

            let matchCell = normalizeCell(cell(cells, columnMap.match))
            let selectionCell = normalizeCell(cell(cells, columnMap.selection))

            if matchCell.localizedCaseInsensitiveContains("NO BETS") {
                emptySlipFromRow = true
                i += 1
                continue
            }

            if matchCell.isEmpty || selectionCell.isEmpty {
                partial = true
                i += 1
                continue
            }

            let indexRaw = columnMap.index.map { normalizeCell(cell(cells, $0)) } ?? ""
            let indexVal = parseIndex(indexRaw)
            let odds = columnMap.odds.flatMap { parseNumber(normalizeCell(cell(cells, $0))) }
            let stake = columnMap.stake.flatMap { parseNumber(normalizeCell(cell(cells, $0))) }
            let evVal = columnMap.ev.flatMap { parseNumber(normalizeCell(cell(cells, $0))) }
            let grade: String? = {
                guard let gi = columnMap.grade else { return nil }
                let g = normalizeCell(cell(cells, gi))
                return g.isEmpty ? nil : g
            }()
            let band: String? = {
                guard let bi = columnMap.band else { return nil }
                let b = normalizeCell(cell(cells, bi))
                return b.isEmpty ? nil : b
            }()

            bets.append(PlaceTheseBet(
                index: indexVal,
                match: matchCell,
                selection: selectionCell,
                decimalOdds: odds,
                stakeNok: stake,
                ev: evVal,
                grade: grade,
                band: band
            ))
            i += 1
        }

        let notes = parseNotes(from: lines)
        let isEmptySlip = emptySlipFromRow || !sawDataRow

        if isEmptySlip {
            return PlaceTheseDocument(
                title: title, phaseLine: phaseLine, phaseId: phaseId,
                equityNok: equityNok, remainingRiskNok: remainingRiskNok, dailyCapNok: dailyCapNok,
                notices: notices, bets: [], notes: notes, isEmptySlip: true, parseQuality: .full
            )
        }
        if bets.isEmpty {
            return PlaceTheseDocument(
                title: title, phaseLine: phaseLine, phaseId: phaseId,
                equityNok: equityNok, remainingRiskNok: remainingRiskNok, dailyCapNok: dailyCapNok,
                notices: notices, bets: [], notes: notes, isEmptySlip: false, parseQuality: .partial
            )
        }
        return PlaceTheseDocument(
            title: title, phaseLine: phaseLine, phaseId: phaseId,
            equityNok: equityNok, remainingRiskNok: remainingRiskNok, dailyCapNok: dailyCapNok,
            notices: notices, bets: bets, notes: notes, isEmptySlip: false,
            parseQuality: partial ? .partial : .full
        )
    }

    private static func documentFromStructuredRows(
        bets: [PlaceTheseBet], textExcerpt: String?, apiTitle: String?, summaryLine: String?
    ) -> PlaceTheseDocument {
        let meta = parse(textExcerpt: textExcerpt, apiTitle: apiTitle, summaryLine: summaryLine)
        let empty = bets.contains { $0.match.localizedCaseInsensitiveContains("NO BETS") } || bets.isEmpty
        let cleanBets = empty ? [] : bets.filter { !$0.match.localizedCaseInsensitiveContains("NO BETS") }
        let resolvedTitle: String = {
            if meta.parseQuality != .failed { return meta.title }
            if let t = apiTitle?.trimmingCharacters(in: .whitespaces), !t.isEmpty { return t }
            return "PLACE_THESE"
        }()
        return PlaceTheseDocument(
            title: resolvedTitle,
            phaseLine: meta.phaseLine ?? summaryLine,
            phaseId: meta.phaseId,
            equityNok: meta.equityNok,
            remainingRiskNok: meta.remainingRiskNok,
            dailyCapNok: meta.dailyCapNok,
            notices: meta.notices,
            bets: cleanBets,
            notes: meta.notes,
            isEmptySlip: empty,
            parseQuality: .full
        )
    }

    private struct ColumnMap {
        var index: Int?
        var match: Int
        var selection: Int
        var odds: Int?
        var stake: Int?
        var ev: Int?
        var grade: Int?
        var band: Int?
        var requiredCount: Int { max(match, selection) + 1 }
    }

    private static func findTableHeader(in lines: [String]) -> (index: Int, map: ColumnMap)? {
        for (i, line) in lines.enumerated() {
            guard line.trimmingCharacters(in: .whitespaces).contains("|") else { continue }
            let cells = splitTableCells(line).map { normalizeCell($0) }
            guard let matchIdx = cells.firstIndex(where: { $0.localizedCaseInsensitiveCompare("Match") == .orderedSame }) else { continue }
            guard let selIdx = cells.firstIndex(where: { $0.localizedCaseInsensitiveCompare("Selection") == .orderedSame }) else { continue }
            var map = ColumnMap(match: matchIdx, selection: selIdx)
            for (j, h) in cells.enumerated() {
                let lower = h.lowercased()
                if lower == "#" || lower == "index" || lower == "no" || lower == "no." { map.index = j }
                else if lower.contains("odds") { map.odds = j }
                else if lower.contains("stake") { map.stake = j }
                else if lower == "ev" { map.ev = j }
                else if lower.contains("grade") { map.grade = j }
                else if lower.contains("band") { map.band = j }
            }
            if let hash = cells.firstIndex(of: "#") { map.index = hash }
            return (i, map)
        }
        return nil
    }

    static func splitTableCells(_ line: String) -> [String] {
        var s = line.trimmingCharacters(in: .whitespaces)
        if s.hasPrefix("|") { s = String(s.dropFirst()) }
        if s.hasSuffix("|") { s = String(s.dropLast()) }
        return s.components(separatedBy: "|").map { $0.trimmingCharacters(in: .whitespaces) }
    }

    static func normalizeCell(_ raw: String) -> String {
        var s = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if s.count >= 4 {
            if s.hasPrefix("**"), s.hasSuffix("**") { s = String(s.dropFirst(2).dropLast(2)) }
            else if s.hasPrefix("__"), s.hasSuffix("__") { s = String(s.dropFirst(2).dropLast(2)) }
        }
        if s.count >= 2 {
            if s.hasPrefix("*"), s.hasSuffix("*"), !s.hasPrefix("**") { s = String(s.dropFirst().dropLast()) }
            else if s.hasPrefix("_"), s.hasSuffix("_"), !s.hasPrefix("__") { s = String(s.dropFirst().dropLast()) }
        }
        return s.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func cell(_ cells: [String], _ index: Int) -> String {
        guard index >= 0, index < cells.count else { return "" }
        return cells[index]
    }

    private static func isSeparatorRow(_ line: String) -> Bool {
        let range = NSRange(line.startIndex..., in: line)
        return separatorRowRegex.firstMatch(in: line, options: [], range: range) != nil
    }

    private static func parseIndex(_ raw: String) -> Int? {
        let t = raw.trimmingCharacters(in: .whitespaces)
        if t.isEmpty { return nil }
        if t == "—" || t == "–" || t == "-" || t == "−" { return nil }
        return Int(t)
    }

    static func parseNumber(_ raw: String?) -> Double? {
        guard var t = raw?.trimmingCharacters(in: .whitespaces), !t.isEmpty else { return nil }
        if t == "—" || t == "–" || t == "-" || t == "−" { return nil }
        t = normalizeCell(t)
        if t.contains(","), !t.contains(".") { t = t.replacingOccurrences(of: ",", with: ".") }
        else { t = t.replacingOccurrences(of: ",", with: "") }
        return Double(t)
    }

    private static func parseNotes(from lines: [String]) -> [String] {
        var notes: [String] = []
        var inNotes = false
        for line in lines {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.lowercased().hasPrefix("## notes") { inNotes = true; continue }
            if inNotes {
                if trimmed.hasPrefix("##") { break }
                if trimmed.hasPrefix("- ") { notes.append(String(trimmed.dropFirst(2)).trimmingCharacters(in: .whitespaces)) }
                else if trimmed.hasPrefix("* ") { notes.append(String(trimmed.dropFirst(2)).trimmingCharacters(in: .whitespaces)) }
                else if !trimmed.isEmpty { notes.append(trimmed) }
            }
        }
        return notes
    }

    private static func firstMatch(_ regex: NSRegularExpression, in string: String) -> NSTextCheckingResult? {
        regex.firstMatch(in: string, options: [], range: NSRange(string.startIndex..., in: string))
    }

    private static func group(_ match: NSTextCheckingResult, _ index: Int, in string: String) -> String? {
        let r = match.range(at: index)
        guard r.location != NSNotFound, let swiftRange = Range(r, in: string) else { return nil }
        return String(string[swiftRange])
    }
}
