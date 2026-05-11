import 'dart:async';
import 'package:flutter/foundation.dart';
import 'dart:math';

import '../agents/decision_coordinator.dart';
import '../agents/execution_agent.dart';
import '../agents/learning_agent.dart';
import '../agents/news_agent.dart';
import '../agents/risk_agent.dart';
import '../agents/strategy_agent.dart';
import '../agents/technical_analysis_agent.dart';
import '../models/activity_log_model.dart';
import '../models/agent_result_model.dart';
import '../models/bot_decision_model.dart';
import '../models/bot_settings_model.dart';
import '../models/bot_status_model.dart';
import '../models/coordinated_decision_model.dart';
import '../models/chart_point_model.dart';
import '../models/trade_lesson_model.dart';
import '../models/trade_model.dart';
import '../services/dummy_data_service.dart';
import '../services/fake_market_socket_service.dart';
import '../services/settings_storage_service.dart';

class BotProvider extends ChangeNotifier {
  BotProvider({
    DummyDataService? dataService,
    FakeMarketSocketService? marketSocketService,
    SettingsStorageService? settingsStorageService,
    DecisionCoordinator? decisionCoordinator,
    ExecutionAgent? executionAgent,
  }) : _dataService = dataService ?? DummyDataService(),
       _marketSocketService = marketSocketService ?? FakeMarketSocketService(),
       _settingsStorageService =
           settingsStorageService ?? SettingsStorageService(),
       _executionAgent = executionAgent ?? ExecutionAgent(),
       _decisionCoordinator =
           decisionCoordinator ??
           DecisionCoordinator(
             newsAgent: NewsAgent(),
             technicalAgent: TechnicalAnalysisAgent(),
             riskAgent: RiskAgent(),
             strategyAgent: StrategyAgent(),
             executionAgent: executionAgent ?? ExecutionAgent(),
           ),
       _random = Random() {
    _status = _dataService.getInitialStatus();
    _openTrades = _dataService.getOpenTrades();
    _tradeHistory = _dataService.getTradeHistory();
    _decisions = _dataService.getBotDecisions();
    _marketPrices = _marketSocketService.currentPrices;
    _isMarketLoading = true;
    _marketSocketService.connect(symbols: const ['BTCUSDT', 'ETHUSDT']);
    _priceStream = _marketSocketService.priceStream;
    _priceSubscription = _priceStream!.listen(_onPriceTick);
    _activityLogs = [
      ActivityLogModel(
        event: 'System ready',
        message: 'Simulation environment initialized with local dummy data.',
        timestamp: DateTime.now(),
      ),
    ];
    _settings = BotSettingsModel.defaults;
    _btcPriceHistory = [];
    _ethPriceHistory = [];
    _equityHistory = [];
    _realizedPnlHistory = [];
    _unrealizedPnlHistory = [];
    _latestAgentResults = [];
    _coordinatedDecisions = [];
    _isSettingsLoading = true;
    _loadSettings();
    for (final t in _tradeHistory) {
      if (!t.isOpen) _ingestLesson(t);
    }
    _recalculateStatus();
  }

  final DummyDataService _dataService;
  final FakeMarketSocketService _marketSocketService;
  final SettingsStorageService _settingsStorageService;
  final ExecutionAgent _executionAgent;
  final DecisionCoordinator _decisionCoordinator;
  final Random _random;
  final LearningAgent _learningAgent = LearningAgent();

  late BotStatusModel _status;
  late List<TradeModel> _openTrades;
  late List<TradeModel> _tradeHistory;
  late List<BotDecisionModel> _decisions;
  late List<ActivityLogModel> _activityLogs;
  late Map<String, double> _marketPrices;
  late BotSettingsModel _settings;
  late List<ChartPointModel> _btcPriceHistory;
  late List<ChartPointModel> _ethPriceHistory;
  late List<ChartPointModel> _equityHistory;
  late List<ChartPointModel> _realizedPnlHistory;
  late List<ChartPointModel> _unrealizedPnlHistory;
  late List<AgentResultModel> _latestAgentResults;
  late List<CoordinatedDecisionModel> _coordinatedDecisions;
  List<TradeLessonModel> _tradeLessons = [];
  bool _isMarketLoading = false;
  bool _isSettingsLoading = false;
  bool _marketConnected = false;
  int _tickCount = 0;
  int _tradesOpenedToday = 0;
  DateTime _tradesCounterDate = DateTime.now();
  Stream<Map<String, double>>? _priceStream;
  StreamSubscription<Map<String, double>>? _priceSubscription;
  bool _isDisposed = false;

  BotStatusModel get status => _status;
  List<TradeModel> get openTrades => _openTrades;
  List<TradeModel> get tradeHistory => _tradeHistory;
  List<BotDecisionModel> get decisions => _decisions;
  List<ActivityLogModel> get activityLogs => _activityLogs;
  Map<String, double> get marketPrices => _marketPrices;
  bool get isMarketLoading => _isMarketLoading;
  bool get isSettingsLoading => _isSettingsLoading;
  bool get marketConnected => _marketConnected;
  int get tickCount => _tickCount;
  BotSettingsModel get settings => _settings;
  int get tradesOpenedToday => _tradesOpenedToday;
  List<ChartPointModel> get btcPriceHistory => _btcPriceHistory;
  List<ChartPointModel> get ethPriceHistory => _ethPriceHistory;
  List<ChartPointModel> get equityHistory => _equityHistory;
  List<ChartPointModel> get realizedPnlHistory => _realizedPnlHistory;
  List<ChartPointModel> get unrealizedPnlHistory => _unrealizedPnlHistory;
  List<AgentResultModel> get latestAgentResults => _latestAgentResults;
  List<CoordinatedDecisionModel> get coordinatedDecisions =>
      _coordinatedDecisions;
  List<TradeLessonModel> get tradeLessons => _tradeLessons;

  void startBot() {
    if (_status.isActive) return;
    _status = _status.copyWith(isActive: true);
    _log(
      'Bot started',
      'Autonomous engine started and market stream connected.',
    );
    notifyListeners();
  }

  void stopBot() {
    if (!_status.isActive) return;
    _status = _status.copyWith(isActive: false);
    _log('Bot stopped', 'Bot execution paused by operator.');
    notifyListeners();
  }

  void emergencyStop() {
    final now = DateTime.now();
    final forcedClosed = _openTrades
        .map((trade) => trade.copyWith(isOpen: false, closedAt: now))
        .toList();
    for (final t in forcedClosed) {
      _ingestLesson(t);
    }
    _tradeHistory = [...forcedClosed, ..._tradeHistory];
    _status = _status.copyWith(isActive: false);
    _openTrades = [];
    _log('Bot stopped', 'Emergency stop triggered by operator.');
    _recalculateStatus();
    notifyListeners();
  }

  void closeTrade(String tradeId) {
    final idx = _openTrades.indexWhere((trade) => trade.id == tradeId);
    if (idx == -1) return;
    final now = DateTime.now();
    final closed = _openTrades[idx].copyWith(isOpen: false, closedAt: now);
    _openTrades = _openTrades.where((trade) => trade.id != tradeId).toList();
    _tradeHistory = [closed, ..._tradeHistory];
    _ingestLesson(closed);
    _log('Execution Agent', 'Closed ${closed.symbol} ${closed.side} manually.');
    _recalculateStatus();
    notifyListeners();
  }

  void _onPriceTick(Map<String, double> prices) {
    _resetDailyCounterIfNeeded();
    _marketPrices = prices;
    _tickCount += 1;
    _marketConnected = true;
    _isMarketLoading = false;

    _openTrades = _executionAgent.markToMarket(_openTrades, prices);
    _appendPriceHistory(prices);

    if (_status.isActive) {
      final symbols = prices.keys.toList();
      if (symbols.isNotEmpty) {
        final symbol = symbols[_random.nextInt(symbols.length)];
        final chartPoints = symbol == 'BTCUSDT'
            ? _btcPriceHistory
            : _ethPriceHistory;
        final recentPrices = chartPoints.map((p) => p.value).toList();
        final coordinatorResult = _decisionCoordinator.run(
          symbol: symbol,
          recentPrices: recentPrices,
          currentPrice: prices[symbol] ?? 0,
          openTrades: _openTrades,
          prices: prices,
          settings: _settings,
          tradesOpenedToday: _tradesOpenedToday,
          recentLessons: _tradeLessons.take(24).toList(),
        );

        for (final closed
            in coordinatorResult.executionResult.closedTrades) {
          _ingestLesson(closed);
        }

        _latestAgentResults = coordinatorResult.agentResults;
        _coordinatedDecisions = [
          coordinatorResult.coordinatedDecision,
          ..._coordinatedDecisions,
        ].take(80).toList();
        _openTrades = coordinatorResult.executionResult.openTrades;
        _tradeHistory = [
          ...coordinatorResult.executionResult.closedTrades,
          ..._tradeHistory,
        ];
        _tradesOpenedToday +=
            coordinatorResult.executionResult.openedTrades.length;
        _decisions = [
          _toBotDecision(
            coordinatorResult.coordinatedDecision,
            coordinatorResult.agentResults,
          ),
          ..._decisions,
        ].take(80).toList();

        for (final log in coordinatorResult.logs) {
          _log(log.event, log.message, timestamp: log.timestamp);
        }
      }
    }

    if (_random.nextDouble() < 0.04) {
      _log(
        'API simulated error',
        'Transient gateway timeout from simulated exchange endpoint.',
      );
    }

    _recalculateStatus();
    _appendEquityHistory();
    notifyListeners();
  }

  BotDecisionModel _toBotDecision(
    CoordinatedDecisionModel coordinated,
    List<AgentResultModel> agentResults,
  ) {
    return BotDecisionModel(
      symbol: coordinated.symbol,
      action: coordinated.finalAction,
      confidence: coordinated.confidence,
      newsScore: coordinated.newsScore,
      technicalScore: coordinated.technicalScore,
      riskScore: coordinated.riskScore,
      riskApproved: coordinated.riskApproved,
      explanation: coordinated.explanation,
      agentResults: agentResults,
      timestamp: coordinated.createdAt,
    );
  }

  Future<void> _loadSettings() async {
    final loaded = await _settingsStorageService.loadSettings();
    _settings = loaded;
    _isSettingsLoading = false;
    if (!_isDisposed) {
      _log('Settings loaded', 'Saved strategy settings applied.');
      notifyListeners();
    }
  }

  Future<void> updateSettings(BotSettingsModel settings) async {
    _settings = settings;
    await _settingsStorageService.saveSettings(settings);
    _log('Settings updated', 'Strategy configuration has been updated.');
    if (!_isDisposed) notifyListeners();
  }

  Future<void> resetSettings() async {
    _settings = BotSettingsModel.defaults;
    await _settingsStorageService.saveSettings(_settings);
    _log('Settings updated', 'Reset to default strategy configuration.');
    if (!_isDisposed) notifyListeners();
  }

  void _resetDailyCounterIfNeeded() {
    final now = DateTime.now();
    if (now.year != _tradesCounterDate.year ||
        now.month != _tradesCounterDate.month ||
        now.day != _tradesCounterDate.day) {
      _tradesCounterDate = now;
      _tradesOpenedToday = 0;
      _log('System', 'Daily trades counter reset.');
    }
  }

  void _recalculateStatus() {
    final openPnl = _openTrades.fold<double>(
      0,
      (sum, trade) => sum + trade.profitLoss,
    );
    final closedPnl = _tradeHistory.fold<double>(
      0,
      (sum, trade) => sum + trade.profitLoss,
    );
    final totalPnl = openPnl + closedPnl;
    _status = _status.copyWith(
      openTradesCount: _openTrades.length,
      profitLoss: totalPnl,
      demoBalance: 25000 + totalPnl,
    );
  }

  void _appendPriceHistory(Map<String, double> prices) {
    final now = DateTime.now();
    final btc = prices['BTCUSDT'];
    final eth = prices['ETHUSDT'];

    if (btc != null) {
      _btcPriceHistory = _appendAndTrim(
        _btcPriceHistory,
        ChartPointModel(timestamp: now, value: btc),
      );
    }
    if (eth != null) {
      _ethPriceHistory = _appendAndTrim(
        _ethPriceHistory,
        ChartPointModel(timestamp: now, value: eth),
      );
    }
  }

  void _appendEquityHistory() {
    final now = DateTime.now();
    final openPnl = _openTrades.fold<double>(
      0,
      (sum, trade) => sum + trade.profitLoss,
    );
    final closedPnl = _tradeHistory.fold<double>(
      0,
      (sum, trade) => sum + trade.profitLoss,
    );

    _equityHistory = _appendAndTrim(
      _equityHistory,
      ChartPointModel(timestamp: now, value: _status.demoBalance),
    );
    _realizedPnlHistory = _appendAndTrim(
      _realizedPnlHistory,
      ChartPointModel(timestamp: now, value: closedPnl),
    );
    _unrealizedPnlHistory = _appendAndTrim(
      _unrealizedPnlHistory,
      ChartPointModel(timestamp: now, value: openPnl),
    );
  }

  List<ChartPointModel> _appendAndTrim(
    List<ChartPointModel> list,
    ChartPointModel point,
  ) {
    final updated = [...list, point];
    if (updated.length <= 50) return updated;
    return updated.sublist(updated.length - 50);
  }

  void _ingestLesson(TradeModel closedTrade) {
    if (_tradeLessons.any((l) => l.tradeId == closedTrade.id)) return;
    final lesson = _learningAgent.lessonFromClosedTrade(closedTrade);
    _tradeLessons = [lesson, ..._tradeLessons].take(120).toList();
  }

  void _log(String event, String message, {DateTime? timestamp}) {
    _activityLogs = [
      ActivityLogModel(
        event: event,
        message: message,
        timestamp: timestamp ?? DateTime.now(),
      ),
      ..._activityLogs,
    ].take(150).toList();
  }

  @override
  void dispose() {
    if (_isDisposed) return;
    _isDisposed = true;
    _marketSocketService.dispose();
    _priceSubscription?.cancel();
    super.dispose();
  }
}
