import 'package:flutter/material.dart';

import '../services/backend_api_client.dart';
import '../utils/app_theme.dart';
import 'app_card.dart';

/// Temporary demo control: probes FastAPI [GET /health] + [GET /market/prices] only.
class BackendConnectionCard extends StatefulWidget {
  const BackendConnectionCard({super.key});

  @override
  State<BackendConnectionCard> createState() => _BackendConnectionCardState();
}

class _BackendConnectionCardState extends State<BackendConnectionCard> {
  final _client = BackendApiClient();
  bool _busy = false;
  bool? _connected;
  double? _btc;
  double? _eth;
  String? _detail;

  Future<void> _test() async {
    setState(() {
      _busy = true;
      _detail = null;
    });
    final result = await _client.probeHealthAndPrices();
    if (!mounted) return;
    setState(() {
      _busy = false;
      _connected = result.connected;
      _btc = result.btcUsdt;
      _eth = result.ethUsdt;
      _detail = result.message;
    });
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final statusColor = _connected == null
        ? scheme.onSurfaceVariant
        : (_connected!
              ? AppTheme.positive
              : AppTheme.negative);

    return AppCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Backend (demo)',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Text(
                'Status: ',
                style: TextStyle(
                  fontSize: 13,
                  color: scheme.onSurfaceVariant,
                ),
              ),
              Text(
                _connected == null
                    ? '—'
                    : (_connected! ? 'Connected' : 'Disconnected'),
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  color: statusColor,
                ),
              ),
              if (_busy) ...[
                const SizedBox(width: 10),
                SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: scheme.primary,
                  ),
                ),
              ],
            ],
          ),
          if (_connected == true && _btc != null && _eth != null) ...[
            const SizedBox(height: 8),
            Text(
              'BTCUSDT (backend): ${_btc!.toStringAsFixed(2)}',
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
            Text(
              'ETHUSDT (backend): ${_eth!.toStringAsFixed(2)}',
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ],
          if (_detail != null && _connected != true) ...[
            const SizedBox(height: 6),
            Text(
              _detail!,
              style: TextStyle(fontSize: 12, color: scheme.error),
            ),
          ],
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _busy ? null : _test,
            icon: const Icon(Icons.cloud_done_outlined, size: 20),
            label: const Text('Test Backend Connection'),
          ),
        ],
      ),
    );
  }
}
