import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/chart_point_model.dart';
import '../utils/app_theme.dart';

class EquityCurveChart extends StatelessWidget {
  const EquityCurveChart({
    super.key,
    required this.equity,
    required this.unrealized,
    required this.realized,
  });

  final List<ChartPointModel> equity;
  final List<ChartPointModel> unrealized;
  final List<ChartPointModel> realized;

  @override
  Widget build(BuildContext context) {
    if (equity.length < 2 || unrealized.length < 2 || realized.length < 2) {
      return const Card(
        child: SizedBox(
          height: 220,
          child: Center(child: Text('Building equity history...')),
        ),
      );
    }

    final maxLen = [
      equity.length,
      unrealized.length,
      realized.length,
    ].reduce((a, b) => a > b ? a : b);

    List<FlSpot> toSpots(List<ChartPointModel> input) {
      return [
        for (var i = 0; i < input.length; i++)
          FlSpot(i.toDouble(), input[i].value),
      ];
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Equity Curve',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 10),
            SizedBox(
              height: 170,
              child: LineChart(
                duration: const Duration(milliseconds: 450),
                curve: Curves.easeOutCubic,
                LineChartData(
                  minX: 0,
                  maxX: (maxLen - 1).toDouble(),
                  borderData: FlBorderData(show: false),
                  lineTouchData: const LineTouchData(enabled: false),
                  titlesData: const FlTitlesData(show: false),
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: 500,
                    getDrawingHorizontalLine: (value) =>
                        FlLine(color: Colors.white12, strokeWidth: 1),
                  ),
                  lineBarsData: [
                    LineChartBarData(
                      spots: toSpots(equity),
                      isCurved: true,
                      color: Colors.blueAccent,
                      barWidth: 2.2,
                      dotData: const FlDotData(show: false),
                    ),
                    LineChartBarData(
                      spots: toSpots(unrealized),
                      isCurved: true,
                      color: AppTheme.warning,
                      barWidth: 2,
                      dotData: const FlDotData(show: false),
                    ),
                    LineChartBarData(
                      spots: toSpots(realized),
                      isCurved: true,
                      color: AppTheme.positive,
                      barWidth: 2,
                      dotData: const FlDotData(show: false),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            const Wrap(
              spacing: 12,
              children: [
                _LegendDot(color: Colors.blueAccent, label: 'Demo Balance'),
                _LegendDot(color: AppTheme.warning, label: 'Unrealized P/L'),
                _LegendDot(color: AppTheme.positive, label: 'Realized P/L'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: Colors.white70),
        ),
      ],
    );
  }
}
