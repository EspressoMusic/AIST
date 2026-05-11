import '../models/bot_decision_model.dart';
import '../models/bot_status_model.dart';
import '../models/trade_model.dart';

class DummyDataService {
  BotStatusModel getInitialStatus() {
    return const BotStatusModel(
      isActive: false,
      demoBalance: 25000,
      profitLoss: 1240.55,
      openTradesCount: 3,
    );
  }

  List<TradeModel> getOpenTrades() {
    return [
      TradeModel(
        id: 'T-101',
        symbol: 'BTCUSDT',
        side: 'Buy',
        quantity: 0.04,
        entryPrice: 62850.0,
        currentPrice: 63210.5,
        profitLoss: 360.5,
        reason: 'Breakout above resistance with volume confirmation',
        openedAt: DateTime.now().subtract(const Duration(hours: 3)),
      ),
      TradeModel(
        id: 'T-102',
        symbol: 'ETHUSDT',
        side: 'Sell',
        quantity: 0.6,
        entryPrice: 3090.4,
        currentPrice: 3042.2,
        profitLoss: 190.2,
        reason: 'Bearish divergence on RSI and MACD crossover',
        openedAt: DateTime.now().subtract(const Duration(hours: 1)),
      ),
      TradeModel(
        id: 'T-103',
        symbol: 'SOLUSDT',
        side: 'Buy',
        quantity: 1.9,
        entryPrice: 142.7,
        currentPrice: 139.1,
        profitLoss: -85.7,
        reason: 'Pullback to EMA 20 in bullish trend channel',
        openedAt: DateTime.now().subtract(const Duration(minutes: 35)),
      ),
    ];
  }

  List<TradeModel> getTradeHistory() {
    return [
      TradeModel(
        id: 'H-201',
        symbol: 'XRPUSDT',
        side: 'Buy',
        quantity: 1500,
        entryPrice: 0.58,
        currentPrice: 0.61,
        profitLoss: 95.4,
        reason: 'Support bounce from daily demand zone',
        openedAt: DateTime.now().subtract(const Duration(days: 1, hours: 6)),
        closedAt: DateTime.now().subtract(const Duration(days: 1, hours: 4)),
        isOpen: false,
      ),
      TradeModel(
        id: 'H-202',
        symbol: 'BNBUSDT',
        side: 'Sell',
        quantity: 13,
        entryPrice: 612.0,
        currentPrice: 621.8,
        profitLoss: -124.0,
        reason: 'Failed breakdown and reversal candle pattern',
        openedAt: DateTime.now().subtract(const Duration(days: 2, hours: 4)),
        closedAt: DateTime.now().subtract(const Duration(days: 2, hours: 1)),
        isOpen: false,
      ),
      TradeModel(
        id: 'H-203',
        symbol: 'ADAUSDT',
        side: 'Buy',
        quantity: 4200,
        entryPrice: 0.45,
        currentPrice: 0.49,
        profitLoss: 210.7,
        reason: 'Trend continuation after consolidation breakout',
        openedAt: DateTime.now().subtract(const Duration(days: 3, hours: 2)),
        closedAt: DateTime.now().subtract(const Duration(days: 3)),
        isOpen: false,
      ),
    ];
  }

  List<BotDecisionModel> getBotDecisions() {
    return [];
  }
}
