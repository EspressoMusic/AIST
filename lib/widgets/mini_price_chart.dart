import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/chart_point_model.dart';
import '../utils/app_theme.dart';

class MiniPriceChart extends StatelessWidget {
  const MiniPriceChart({super.key, required this.symbol, required this.points});

  final String symbol;
  final List<ChartPointModel> points;

  @override
  Widget build(BuildContext context) {
    if (points.length < 2) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Text(symbol, style: const TextStyle(fontWeight: FontWeight.w700)),
              const Spacer(),
              const Text('Waiting for market data...'),
            ],
          ),
        ),
      );
    }

    final first = points.first.value;
    final last = points.last.value;
    final up = last >= first;
    final color = up ? AppTheme.positive : AppTheme.negative;
    final delta = ((last - first) / first) * 100;

    final spots = <FlSpot>[
      for (var i = 0; i < points.length; i++)
        FlSpot(i.toDouble(), points[i].value),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  symbol,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const Spacer(),
                Text(
                  '${up ? '+' : ''}${delta.toStringAsFixed(2)}%',
                  style: TextStyle(color: color, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: 84,
              child: LineChart(
                duration: const Duration(milliseconds: 450),
                curve: Curves.easeOutCubic,
                LineChartData(
                  lineTouchData: const LineTouchData(enabled: false),
                  borderData: FlBorderData(show: false),
                  gridData: const FlGridData(show: false),
                  titlesData: const FlTitlesData(show: false),
                  minX: 0,
                  maxX: (spots.length - 1).toDouble(),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: color,
                      barWidth: 2.2,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(
                        show: true,
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            color.withValues(alpha: 0.25),
                            color.withValues(alpha: 0.02),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 2),
            Text(
              'Last: ${last.toStringAsFixed(2)}',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}
