import 'package:flutter/material.dart';

import '../models/bot_decision_model.dart';
import '../utils/app_theme.dart';

class DecisionCard extends StatelessWidget {
  const DecisionCard({super.key, required this.decision});

  final BotDecisionModel decision;

  @override
  Widget build(BuildContext context) {
    final approved = decision.riskApproved;
    final riskColor = approved ? AppTheme.positive : AppTheme.warning;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  '${decision.symbol}  ${decision.action}',
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const Spacer(),
                Text(
                  '${decision.timestamp.hour.toString().padLeft(2, '0')}:${decision.timestamp.minute.toString().padLeft(2, '0')}',
                  style: const TextStyle(color: Colors.white60),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text('Explanation: ${decision.explanation}'),
            const SizedBox(height: 10),
            Text(
              'Confidence: ${decision.confidence.toStringAsFixed(1)}%',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(
              'News: ${decision.newsScore.toStringAsFixed(1)} | Technical: ${decision.technicalScore.toStringAsFixed(1)} | Risk: ${decision.riskScore.toStringAsFixed(1)}',
            ),
            const SizedBox(height: 8),
            Text(
              'Risk status: ${approved ? 'Approved' : 'Rejected'}',
              style: TextStyle(color: riskColor, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 10),
            const Text(
              'Agent Results',
              style: TextStyle(
                fontWeight: FontWeight.w700,
                color: Colors.white70,
              ),
            ),
            const SizedBox(height: 6),
            for (final result in decision.agentResults)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                  '${result.agentName}: ${result.explanation}',
                  style: const TextStyle(color: Colors.white60, fontSize: 12.5),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
