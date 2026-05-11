import 'package:flutter/material.dart';

import '../utils/app_theme.dart';

class MetricCard extends StatefulWidget {
  const MetricCard({
    super.key,
    required this.label,
    this.valueText,
    this.valueNumber,
    this.currency = false,
    this.isProfitLoss = false,
  });

  final String label;
  final String? valueText;
  final double? valueNumber;
  final bool currency;
  final bool isProfitLoss;

  @override
  State<MetricCard> createState() => _MetricCardState();
}

class _MetricCardState extends State<MetricCard> {
  late double _previous;

  @override
  void initState() {
    super.initState();
    _previous = widget.valueNumber ?? 0;
  }

  @override
  void didUpdateWidget(covariant MetricCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    _previous = oldWidget.valueNumber ?? _previous;
  }

  String _formatValue(double value) {
    if (widget.currency) {
      final prefix = value >= 0 && widget.isProfitLoss ? '+' : '';
      return '$prefix\$${value.toStringAsFixed(2)}';
    }
    return value.toStringAsFixed(2);
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final textValue = widget.valueText ?? _formatValue(widget.valueNumber ?? 0);
    final valueColor = widget.isProfitLoss
        ? (textValue.trim().startsWith('-')
              ? AppTheme.negative
              : AppTheme.positive)
        : scheme.onSurface;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(14),
        boxShadow: widget.isProfitLoss
            ? [
                BoxShadow(
                  color: valueColor.withValues(alpha: 0.14),
                  blurRadius: 18,
                  spreadRadius: 1,
                ),
              ]
            : null,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            widget.label,
            style: TextStyle(color: scheme.onSurfaceVariant),
          ),
          const SizedBox(height: 8),
          if (widget.valueNumber != null)
            TweenAnimationBuilder<double>(
              tween: Tween<double>(begin: _previous, end: widget.valueNumber!),
              duration: const Duration(milliseconds: 700),
              curve: Curves.easeOutCubic,
              builder: (context, value, _) {
                return Text(
                  _formatValue(value),
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: valueColor,
                  ),
                );
              },
            )
          else
            Text(
              textValue,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: valueColor,
              ),
            ),
        ],
      ),
    );
  }
}
