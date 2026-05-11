import 'package:flutter/material.dart';

import '../providers/bot_provider.dart';
import '../utils/app_theme.dart';

class ActivityLogsScreen extends StatelessWidget {
  const ActivityLogsScreen({super.key, required this.botProvider});

  final BotProvider botProvider;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: botProvider,
      builder: (context, _) {
        final logs = botProvider.activityLogs;
        if (logs.isEmpty) {
          return const Center(child: Text('No activity logs yet.'));
        }

        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: logs.length,
          separatorBuilder: (_, index) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final log = logs[index];
            final color = _eventColor(log.event);
            final time =
                '${log.timestamp.hour.toString().padLeft(2, '0')}:${log.timestamp.minute.toString().padLeft(2, '0')}:${log.timestamp.second.toString().padLeft(2, '0')}';

            return Card(
              child: ListTile(
                leading: Icon(
                  Icons.fiber_manual_record,
                  size: 13,
                  color: color,
                ),
                title: Row(
                  children: [
                    Expanded(child: Text(log.event)),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        _actionType(log.message),
                        style: TextStyle(
                          color: color,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                subtitle: Text(log.message),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      time,
                      style: const TextStyle(
                        color: Colors.white60,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white10,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        log.event,
                        style: const TextStyle(
                          fontSize: 10,
                          color: Colors.white70,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Color _eventColor(String event) {
    if (event.contains('error')) return AppTheme.negative;
    if (event.contains('rejected')) return AppTheme.warning;
    if (event.contains('opened')) return AppTheme.positive;
    if (event.contains('closed')) return Colors.orangeAccent;
    return Colors.blueAccent;
  }

  String _actionType(String message) {
    final text = message.toLowerCase();
    if (text.contains('opened')) return 'OPEN';
    if (text.contains('closed')) return 'CLOSE';
    if (text.contains('rejected')) return 'REJECT';
    if (text.contains('approved')) return 'APPROVE';
    if (text.contains('error')) return 'ERROR';
    return 'INFO';
  }
}
