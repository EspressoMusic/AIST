import '../models/activity_log_model.dart';
import '../models/bot_settings_model.dart';
import '../models/trade_model.dart';

class ExecutionResult {
  const ExecutionResult({
    required this.openTrades,
    required this.openedTrades,
    required this.closedTrades,
    required this.logs,
  });

  final List<TradeModel> openTrades;
  final List<TradeModel> openedTrades;
  final List<TradeModel> closedTrades;
  final List<ActivityLogModel> logs;
}

class ExecutionAgent {
  int _tradeCounter = 2000;

  List<TradeModel> markToMarket(
    List<TradeModel> openTrades,
    Map<String, double> prices,
  ) {
    return openTrades.map((trade) {
      final latestPrice = prices[trade.symbol] ?? trade.currentPrice;
      return trade.copyWith(
        currentPrice: latestPrice,
        profitLoss: _calculateProfitLoss(
          side: trade.side,
          entry: trade.entryPrice,
          current: latestPrice,
          quantity: trade.quantity,
        ),
      );
    }).toList();
  }

  ExecutionResult execute({
    required String symbol,
    required String finalAction,
    required bool riskApproved,
    required List<TradeModel> openTrades,
    required Map<String, double> prices,
    required BotSettingsModel settings,
    required double suggestedStopLossPercent,
    required double suggestedTakeProfitPercent,
    List<String> agentsApprovedAtOpen = const [],
    String coordinatorExplanationAtOpen = '',
  }) {
    final now = DateTime.now();
    final logs = <ActivityLogModel>[];
    final openedTrades = <TradeModel>[];
    final closedTrades = <TradeModel>[];
    var updatedOpenTrades = List<TradeModel>.from(openTrades);

    for (final trade in List<TradeModel>.from(updatedOpenTrades)) {
      final ageSeconds = now.difference(trade.openedAt).inSeconds;
      final stopLossHit = trade.agentStopLossPrice == null
          ? false
          : (trade.side == 'Buy'
                ? trade.currentPrice <= trade.agentStopLossPrice!
                : trade.currentPrice >= trade.agentStopLossPrice!);
      final takeProfitHit = trade.agentTakeProfitPrice == null
          ? false
          : (trade.side == 'Buy'
                ? trade.currentPrice >= trade.agentTakeProfitPrice!
                : trade.currentPrice <= trade.agentTakeProfitPrice!);
      final timeoutHit = ageSeconds > 45;
      if (stopLossHit || takeProfitHit || timeoutHit) {
        final closed = trade.copyWith(isOpen: false, closedAt: now);
        updatedOpenTrades.removeWhere((item) => item.id == trade.id);
        closedTrades.add(closed);
        logs.add(
          ActivityLogModel(
            event: 'Execution Agent',
            message:
                'Closed ${closed.symbol} ${closed.side} (${stopLossHit
                    ? 'stop loss'
                    : takeProfitHit
                    ? 'take profit'
                    : 'timeout'})',
            timestamp: now,
          ),
        );
      }
    }

    if (!riskApproved) {
      logs.add(
        ActivityLogModel(
          event: 'Execution Agent',
          message: 'Skipped execution because Risk Agent rejected trade.',
          timestamp: now,
        ),
      );
      return ExecutionResult(
        openTrades: updatedOpenTrades,
        openedTrades: openedTrades,
        closedTrades: closedTrades,
        logs: logs,
      );
    }

    if (finalAction == 'BUY' || finalAction == 'SELL') {
      final entry = prices[symbol] ?? 0;
      if (entry > 0) {
        final quantity = settings.positionSizeUsd / entry;
        final isBuy = finalAction == 'BUY';
        final stopPrice = isBuy
            ? entry * (1 - (suggestedStopLossPercent / 100))
            : entry * (1 + (suggestedStopLossPercent / 100));
        final takePrice = isBuy
            ? entry * (1 + (suggestedTakeProfitPercent / 100))
            : entry * (1 - (suggestedTakeProfitPercent / 100));
        final trade = TradeModel(
          id: 'T-${_tradeCounter++}',
          symbol: symbol,
          side: isBuy ? 'Buy' : 'Sell',
          quantity: quantity,
          entryPrice: entry,
          currentPrice: entry,
          profitLoss: 0,
          reason:
              'Risk Agent set dynamic stop loss and take profit based on volatility and confidence.',
          agentStopLossPrice: stopPrice,
          agentTakeProfitPrice: takePrice,
          openedAt: now,
          agentsApprovedAtOpen: List<String>.from(agentsApprovedAtOpen),
          coordinatorExplanationAtOpen: coordinatorExplanationAtOpen,
        );
        updatedOpenTrades = [trade, ...updatedOpenTrades];
        openedTrades.add(trade);
        logs.add(
          ActivityLogModel(
            event: 'Execution Agent',
            message:
                'Opened ${trade.symbol} ${trade.side} at ${entry.toStringAsFixed(2)}',
            timestamp: now,
          ),
        );
      }
    }

    return ExecutionResult(
      openTrades: updatedOpenTrades,
      openedTrades: openedTrades,
      closedTrades: closedTrades,
      logs: logs,
    );
  }

  double _calculateProfitLoss({
    required String side,
    required double entry,
    required double current,
    required double quantity,
  }) {
    if (side == 'Buy') return (current - entry) * quantity;
    return (entry - current) * quantity;
  }
}
