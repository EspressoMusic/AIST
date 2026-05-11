import 'package:flutter/material.dart';

/// Legend row for entry / exit markers used with [CandlestickChart].
class TradeMarkerLegend extends StatelessWidget {
  const TradeMarkerLegend({
    super.key,
    required this.showExit,
  });

  final bool showExit;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Wrap(
      spacing: 16,
      runSpacing: 8,
      children: [
        _LegendDot(
          color: const Color(0xFF38BDF8),
          label: 'Entry',
          textColor: scheme.onSurface,
        ),
        if (showExit)
          _LegendDot(
            color: const Color(0xFFA855F7),
            label: 'Exit',
            textColor: scheme.onSurface,
          ),
      ],
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({
    required this.color,
    required this.label,
    required this.textColor,
  });

  final Color color;
  final String label;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: textColor,
            fontSize: 13,
          ),
        ),
      ],
    );
  }
}
