import 'package:flutter/material.dart';

import '../providers/bot_provider.dart';
import '../widgets/agent_status_card.dart';

class AgentMonitorScreen extends StatelessWidget {
  const AgentMonitorScreen({super.key, required this.botProvider});

  final BotProvider botProvider;

  static const _agentOrder = [
    'News Agent',
    'Technical Analysis Agent',
    'Risk Agent',
    'Strategy Agent',
    'Execution Agent',
    'Decision Coordinator',
  ];

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: botProvider,
      builder: (context, _) {
        final latest = botProvider.latestAgentResults;
        if (latest.isEmpty) {
          return const Center(
            child: Text(
              'No agent output yet. Start the bot to monitor agents.',
            ),
          );
        }

        final map = {for (final item in latest) item.agentName: item};
        final items = _agentOrder
            .where((name) => map[name] != null)
            .map((name) => map[name]!)
            .toList();

        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              child: Row(
                children: [
                  const Text(
                    'Multi-Agent Live Monitor',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const Spacer(),
                  if (botProvider.marketConnected)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.green.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: const Text(
                        'LIVE',
                        style: TextStyle(
                          color: Colors.greenAccent,
                          fontWeight: FontWeight.bold,
                          fontSize: 11,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: items.length,
                separatorBuilder: (_, index) => const SizedBox(height: 8),
                itemBuilder: (context, index) =>
                    AgentStatusCard(result: items[index]),
              ),
            ),
          ],
        );
      },
    );
  }
}
