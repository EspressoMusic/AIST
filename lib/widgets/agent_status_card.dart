import 'package:flutter/material.dart';

import '../models/agent_result_model.dart';
import '../utils/app_theme.dart';

class AgentStatusCard extends StatelessWidget {
  const AgentStatusCard({super.key, required this.result});

  final AgentResultModel result;

  @override
  Widget build(BuildContext context) {
    final style = _statusStyle(result);
    final time =
        '${result.createdAt.hour.toString().padLeft(2, '0')}:${result.createdAt.minute.toString().padLeft(2, '0')}:${result.createdAt.second.toString().padLeft(2, '0')}';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    result.agentName,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: style.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(99),
                  ),
                  child: Text(
                    result.action ??
                        (result.approved == true ? 'APPROVED' : 'NEUTRAL'),
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: style,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text('Symbol: ${result.symbol}'),
            const SizedBox(height: 2),
            Text('Score: ${result.score.toStringAsFixed(1)}'),
            if (result.confidence != null)
              Text('Confidence: ${result.confidence!.toStringAsFixed(1)}%'),
            if (result.approved != null)
              Text(
                'Status: ${result.approved! ? 'Approved' : 'Rejected'}',
                style: TextStyle(
                  color: result.approved!
                      ? AppTheme.positive
                      : AppTheme.negative,
                ),
              ),
            const SizedBox(height: 6),
            Text(
              result.explanation,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 6),
            Text(
              'Updated $time',
              style: const TextStyle(color: Colors.white54, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Color _statusStyle(AgentResultModel item) {
    final action = item.action?.toUpperCase();
    if (action == 'BUY' || item.approved == true || item.score > 20) {
      return AppTheme.positive;
    }
    if (action == 'SELL' || item.approved == false || item.score < -20) {
      return AppTheme.negative;
    }
    return Colors.grey;
  }
}
