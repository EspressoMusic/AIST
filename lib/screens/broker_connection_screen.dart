import 'package:flutter/material.dart';

import '../providers/broker_provider.dart';
import '../widgets/section_container.dart';

class BrokerConnectionScreen extends StatelessWidget {
  const BrokerConnectionScreen({super.key, required this.brokerProvider});

  final BrokerProvider brokerProvider;

  @override
  Widget build(BuildContext context) {
    const options = [
      ('Binance Testnet', true),
      ('Alpaca Paper Trading', true),
      ('Demo Broker', true),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('Broker Connection')),
      body: AnimatedBuilder(
        animation: brokerProvider,
        builder: (context, _) {
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const SectionContainer(
                title: 'Choose Broker',
                subtitle: 'Dummy local setup only, no real API keys',
                child: SizedBox.shrink(),
              ),
              const SizedBox(height: 10),
              for (final option in options) ...[
                Card(
                  child: ListTile(
                    title: Text(option.$1),
                    subtitle: const Text('Paper / demo mode'),
                    trailing: FilledButton(
                      onPressed: brokerProvider.isBusy
                          ? null
                          : () async {
                              await brokerProvider.connectBroker(
                                brokerName: option.$1,
                                isPaper: option.$2,
                              );
                              if (context.mounted) {
                                Navigator.of(context).pop();
                              }
                            },
                      child: const Text('Connect'),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
              ],
            ],
          );
        },
      ),
    );
  }
}
