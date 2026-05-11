import 'package:flutter/material.dart';

import '../models/preflight_check_model.dart';
import '../utils/app_theme.dart';

class PreflightCheckItem extends StatelessWidget {
  const PreflightCheckItem({super.key, required this.item});

  final PreflightCheckModel item;

  @override
  Widget build(BuildContext context) {
    final color = item.passed ? AppTheme.positive : AppTheme.negative;
    final icon = item.passed ? Icons.check_circle : Icons.warning_amber_rounded;

    return Card(
      child: ListTile(
        leading: Icon(icon, color: color),
        title: Text(item.title),
        subtitle: Text(
          item.message,
          style: TextStyle(
            color: item.passed ? Colors.white70 : Colors.red[200],
          ),
        ),
      ),
    );
  }
}
