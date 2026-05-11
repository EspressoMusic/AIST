import 'package:flutter/material.dart';

import '../providers/bot_provider.dart';
import '../widgets/trade_card.dart';

class OpenTradesScreen extends StatelessWidget {
  const OpenTradesScreen({super.key, required this.botProvider});

  final BotProvider botProvider;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: botProvider,
      builder: (context, _) {
        final trades = botProvider.openTrades;
        if (botProvider.isMarketLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (trades.isEmpty) {
          return const Center(child: Text('No open trades.'));
        }

        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: trades.length,
          separatorBuilder: (_, index) => const SizedBox(height: 10),
          itemBuilder: (context, index) => TradeCard(trade: trades[index]),
        );
      },
    );
  }
}
