import 'package:flutter/material.dart';

import '../utils/app_theme.dart';

class StatusBadge extends StatelessWidget {
  const StatusBadge({super.key, required this.label, required this.type});

  final String label;
  final StatusBadgeType type;

  @override
  Widget build(BuildContext context) {
    final color = switch (type) {
      StatusBadgeType.positive => AppTheme.positive,
      StatusBadgeType.negative => AppTheme.negative,
      StatusBadgeType.warning => AppTheme.warning,
      StatusBadgeType.neutral => Colors.grey,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

enum StatusBadgeType { positive, negative, warning, neutral }
