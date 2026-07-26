import Charts
import SwiftUI

/// Shared date-axis density helpers for time-series charts.
enum ChartAxisSupport {
    /// Compact list plot heights.
    static let compactHeight: CGFloat = 160
    static let compactBarHeight: CGFloat = 140

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
