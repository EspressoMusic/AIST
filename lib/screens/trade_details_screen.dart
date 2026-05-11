import 'package:flutter/material.dart';

import '../models/trade_model.dart';
import '../providers/bot_provider.dart';
import '../widgets/app_card.dart';
import '../widgets/candlestick_chart.dart';
import '../widgets/status_badge.dart';
import '../widgets/trade_marker.dart';

class TradeDetailsScreen extends StatelessWidget {
  const TradeDetailsScreen({
    super.key,
    required this.tradeId,
    required this.botProvider,
  });

  final String tradeId;
  final BotProvider botProvider;

  TradeModel? _resolve(BotProvider p) {
    for (final t in p.openTrades) {
      if (t.id == tradeId) return t;
    }
    for (final t in p.tradeHistory) {
      if (t.id == tradeId) return t;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: botProvider,
      builder: (context, _) {
        final trade = _resolve(botProvider);
        if (trade == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Trade')),
            body: const Center(child: Text('Trade not found')),
          );
        }

        final pack = buildDummyCandlesForTrade(
          tradeId: trade.id,
          entryPrice: trade.entryPrice,
          isOpen: trade.isOpen,
        );

        final scheme = Theme.of(context).colorScheme;

        return Scaffold(
          appBar: AppBar(title: Text(trade.symbol)),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          trade.symbol,
                          style: const TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(width: 10),
                        StatusBadge(
                          label: trade.side.toUpperCase(),
                          type: trade.side.toLowerCase() == 'buy'
                              ? StatusBadgeType.positive
                              : StatusBadgeType.negative,
                        ),
                        const Spacer(),
                        StatusBadge(
                          label: trade.isOpen ? 'OPEN' : 'CLOSED',
                          type: trade.isOpen
                              ? StatusBadgeType.warning
                              : StatusBadgeType.positive,
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    _row(context, 'Entry price', trade.entryPrice.toStringAsFixed(2)),
                    if (!trade.isOpen)
                      _row(context, 'Exit price', trade.currentPrice.toStringAsFixed(2))
                    else
                      _row(
                        context,
                        'Current price',
                        trade.currentPrice.toStringAsFixed(2),
                      ),
                    _row(
                      context,
                      'Profit / loss',
                      trade.profitLoss.toStringAsFixed(2),
                      emphasize: true,
                    ),
                    _row(context, 'Entry time', _fmt(trade.openedAt)),
                    if (trade.closedAt != null)
                      _row(context, 'Exit time', _fmt(trade.closedAt!)),
                    const SizedBox(height: 8),
                    Text(
                      trade.reason,
                      style: TextStyle(color: scheme.onSurfaceVariant),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Agents that approved this trade',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 8),
                    if (trade.agentsApprovedAtOpen.isEmpty)
                      Text(
                        'No approval snapshot for this trade (seed data or legacy).',
                        style: TextStyle(color: scheme.onSurfaceVariant),
                      )
                    else
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: trade.agentsApprovedAtOpen
                            .map(
                              (a) => Chip(
                                label: Text(a),
                                visualDensity: VisualDensity.compact,
                                backgroundColor:
                                    scheme.surfaceContainerHighest,
                              ),
                            )
                            .toList(),
                      ),
                    const SizedBox(height: 14),
                    const Text(
                      'Coordinator explanation',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      trade.coordinatorExplanationAtOpen.isEmpty
                          ? 'No coordinator narrative stored for this trade.'
                          : trade.coordinatorExplanationAtOpen,
                      style: TextStyle(color: scheme.onSurfaceVariant),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Price action (dummy)',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Demonstration chart — not tied to live feeds.',
                      style: TextStyle(
                        fontSize: 12,
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 12),
                    CandlestickChart(
                      candles: pack.candles,
                      timeframeLabel: '5m',
                      entryIndex: pack.entryIndex,
                      exitIndex: pack.exitIndex,
                    ),
                    const SizedBox(height: 10),
                    TradeMarkerLegend(showExit: pack.exitIndex != null),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _row(
    BuildContext context,
    String k,
    String v, {
    bool emphasize = false,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 2,
            child: Text(
              k,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            flex: 3,
            child: Text(
              v,
              textAlign: TextAlign.end,
              style: TextStyle(
                fontWeight: emphasize ? FontWeight.w800 : FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _fmt(DateTime dt) {
    return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} '
        '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }
}
