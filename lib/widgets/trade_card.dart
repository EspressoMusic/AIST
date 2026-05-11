import 'package:flutter/material.dart';

import '../models/trade_model.dart';
import '../utils/app_theme.dart';

class TradeCard extends StatelessWidget {
  const TradeCard({super.key, required this.trade});

  final TradeModel trade;

  @override
  Widget build(BuildContext context) {
    final plColor = trade.profitLoss >= 0
        ? AppTheme.positive
        : AppTheme.negative;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  trade.symbol,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(width: 10),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: trade.side == 'Buy'
                        ? AppTheme.positive.withValues(alpha: 0.18)
                        : AppTheme.negative.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    trade.side,
                    style: TextStyle(
                      color: trade.side == 'Buy'
                          ? AppTheme.positive
                          : AppTheme.negative,
                    ),
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    boxShadow: [
                      BoxShadow(
                        color: plColor.withValues(alpha: 0.18),
                        blurRadius: 18,
                      ),
                    ],
                  ),
                  child: TweenAnimationBuilder<double>(
                    tween: Tween<double>(begin: 0, end: trade.profitLoss),
                    duration: const Duration(milliseconds: 650),
                    curve: Curves.easeOutCubic,
                    builder: (context, value, child) {
                      return Text(
                        '${value >= 0 ? '+' : ''}${value.toStringAsFixed(2)}',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: value >= 0
                              ? AppTheme.positive
                              : AppTheme.negative,
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Entry: ${trade.entryPrice.toStringAsFixed(2)}    Current: ${trade.currentPrice.toStringAsFixed(2)}',
              style: const TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 8),
            Text(
              'Reason: ${trade.reason}',
              style: const TextStyle(color: Colors.white60),
            ),
          ],
        ),
      ),
    );
  }
}
