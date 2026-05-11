import 'package:flutter/material.dart';

import '../providers/bot_provider.dart';
import '../widgets/trade_card.dart';

class TradeHistoryScreen extends StatelessWidget {
  const TradeHistoryScreen({super.key, required this.botProvider});

  final BotProvider botProvider;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: botProvider,
      builder: (context, _) {
        final history = botProvider.tradeHistory;
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: history.length,
          separatorBuilder: (_, index) => const SizedBox(height: 10),
          itemBuilder: (context, index) => TradeCard(trade: history[index]),
        );
      },
    );
  }
}
