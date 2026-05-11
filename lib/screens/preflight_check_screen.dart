import 'package:flutter/material.dart';

import '../providers/bot_provider.dart';
import '../providers/broker_provider.dart';
import '../services/preflight_check_service.dart';
import '../widgets/preflight_check_item.dart';

class PreflightCheckScreen extends StatelessWidget {
  const PreflightCheckScreen({
    super.key,
    required this.brokerProvider,
    required this.botProvider,
    this.checkService,
  });

  final BrokerProvider brokerProvider;
  final BotProvider botProvider;
  final PreflightCheckService? checkService;

  @override
  Widget build(BuildContext context) {
    final service = checkService ?? PreflightCheckService();

    return Scaffold(
      appBar: AppBar(title: const Text('Bot Pre-Flight Check')),
      body: AnimatedBuilder(
        animation: Listenable.merge([brokerProvider, botProvider]),
        builder: (context, _) {
          final checks = service.runChecks(
            brokerProvider: brokerProvider,
            botProvider: botProvider,
          );
          final allPassed = checks.every((check) => check.passed);

          return Column(
            children: [
              Expanded(
                child: ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: checks.length,
                  separatorBuilder: (_, index) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    return PreflightCheckItem(item: checks[index]);
                  },
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (!allPassed)
                      const Padding(
                        padding: EdgeInsets.only(bottom: 10),
                        child: Text(
                          'Fix the issues above before starting the bot.',
                          style: TextStyle(color: Colors.redAccent),
                        ),
                      ),
                    FilledButton.icon(
                      onPressed: allPassed
                          ? () {
                              botProvider.startBot();
                              Navigator.of(context).pop(true);
                            }
                          : null,
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Start Bot'),
                    ),
                    const SizedBox(height: 8),
                    OutlinedButton(
                      onPressed: () => Navigator.of(context).pop(false),
                      child: const Text('Cancel'),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
