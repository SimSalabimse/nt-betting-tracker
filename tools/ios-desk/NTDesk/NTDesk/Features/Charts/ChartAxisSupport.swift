import Charts
import SwiftUI

/// Shared date-axis density helpers for time-series charts.
enum ChartAxisSupport {
    /// Compact list plot heights.
    static let compactHeight: CGFloat = 160
    static let compactBarHeight: CGFloat = 140

    // MARK: - Adaptive Y domain

    /// Build a Y domain that follows the series without forcing from zero, so
    /// equity around ~500 NOK is readable — but not over-zoomed on noise.
    ///
    /// - `includeZero`: for signed series (daily P/L) keep 0 on-screen.
    /// - `minRelativeSpan`: floor on range as a fraction of |mid| (e.g. 0.06 ≈
    ///   never zoom tighter than ~6% of equity level).
    /// - `padFraction`: breathing room above/below the final span.
    static func adaptiveDomain(
        _ values: [Double],
        includeZero: Bool = false,
        minRelativeSpan: Double = 0.06,
        padFraction: Double = 0.14,
        absoluteFloor: Double = 2.0
    ) -> ClosedRange<Double>? {
        let vals = values.filter(\.isFinite)
        guard let dataMin = vals.min(), let dataMax = vals.max() else { return nil }

        var lo = dataMin
        var hi = dataMax
        if includeZero {
            lo = min(lo, 0)
            hi = max(hi, 0)
        }

        var span = hi - lo
        let mid = (hi + lo) / 2
        let floorSpan = max(abs(mid) * minRelativeSpan, absoluteFloor)

        if span < floorSpan {
            // Expand around the data mid so tiny wiggles stay subtle.
            let half = floorSpan / 2
            lo = mid - half
            hi = mid + half
            if includeZero {
                lo = min(lo, 0)
                hi = max(hi, 0)
                if hi - lo < floorSpan {
                    if abs(lo) <= abs(hi) {
                        lo = hi - floorSpan
                    } else {
                        hi = lo + floorSpan
                    }
                }
            }
            span = hi - lo
        }

        let pad = max(span * padFraction, absoluteFloor * 0.15)
        return (lo - pad)...(hi + pad)
    }

    /// Apply design density rules to a chart X axis.
    @AxisContentBuilder
    static func dateAxisMarks(
        days: [ChartDay],
        density: ChartAxisDensity
    ) -> some AxisContent {
        let ticks = ChartDataBuilder.axisTickDates(from: days, density: density)
        if let ticks {
            AxisMarks(values: ticks) { value in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                    .foregroundStyle(DeskTheme.borderSoft)
                AxisTick()
                    .foregroundStyle(DeskTheme.textDim)
                if let date = value.as(Date.self) {
                    AxisValueLabel {
                        Text(date, format: labelFormat(for: density))
                            .font(DeskTypography.caption)
                            .foregroundStyle(DeskTheme.textMuted)
                    }
                }
            }
        } else {
            AxisMarks(values: .automatic(desiredCount: density.desiredAxisCount)) { value in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                    .foregroundStyle(DeskTheme.borderSoft)
                AxisTick()
                    .foregroundStyle(DeskTheme.textDim)
                if let date = value.as(Date.self) {
                    AxisValueLabel {
                        Text(date, format: labelFormat(for: density))
                            .font(DeskTypography.caption)
                            .foregroundStyle(DeskTheme.textMuted)
                    }
                }
            }
        }
    }

    private static func labelFormat(for density: ChartAxisDensity) -> Date.FormatStyle {
        switch density {
        case .empty, .allLabels, .thinnedLabels:
            return .dateTime.month(.abbreviated).day()
        case .weeklyDisplay:
            return .dateTime.month(.abbreviated).year(.twoDigits)
        }
    }
}
