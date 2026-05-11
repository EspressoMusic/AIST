import 'package:flutter/material.dart';

import '../providers/bot_provider.dart';
import '../widgets/decision_card.dart';

class BotDecisionsScreen extends StatelessWidget {
  const BotDecisionsScreen({super.key, required this.botProvider});

  final BotProvider botProvider;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: botProvider,
      builder: (context, _) {
        final decisions = botProvider.decisions;
        if (decisions.isEmpty) {
          return const Center(
            child: Text('No coordinated decisions yet. Start the bot.'),
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: decisions.length,
          separatorBuilder: (_, index) => const SizedBox(height: 10),
          itemBuilder: (context, index) =>
              DecisionCard(decision: decisions[index]),
        );
      },
    );
  }
}
