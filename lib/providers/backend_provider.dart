import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/backend_market_prices_model.dart';
import '../services/backend_api_client.dart';

/// FastAPI demo bot + market data; local [BotProvider] remains optional debug-only.
class BackendProvider extends ChangeNotifier {
  static const String kBackendDisconnectedMessage = 'Backend disconnected';

  static String? friendlyBackendMessage(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    final lower = raw.toLowerCase();
    const hints = <String>[
      'socketexception',
      'failed host lookup',
      'connection refused',
      'clientexception',
      'network is unreachable',
      'timed out',
      'handshakeexception',
      'connection reset',
    ];
    for (final h in hints) {
      if (lower.contains(h)) return kBackendDisconnectedMessage;
    }
    return raw;
  }

  BackendProvider({BackendApiClient? client})
    : _client = client ?? BackendApiClient();

  final BackendApiClient _client;

  /// POST /bot/tick every [backendAutoRunInterval] while [backendAutoRunActive].
  static const Duration backendAutoRunInterval = Duration(seconds: 5);

  Timer? _backendAutoRunTimer;
  bool _autoTickInFlight = false;

  /// True while periodic backend ticks are scheduled (may be false when app is backgrounded).
  bool backendAutoRunActive = false;

  /// Server snapshot refresh after start/stop/tick/auto-tick.
  DateTime? lastBackendSyncAt;

  bool _lifecycleSuspendedAutoRun = false;

  BackendMarketPricesModel? backendMarketPrices;

  /// Raw `source` field from last successful [refreshMarketPrices].
  String? marketPriceSource;
  DateTime? lastMarketPriceUpdatedAt;
  String? backendMarketPriceError;
  bool isMarketPricesLoading = false;

  Map<String, dynamic>? backendPortfolio;
  String? backendLastError;
  bool isBackendLoading = false;

  // --- Backend multi-agent demo bot (probe) ---
  Map<String, dynamic>? backendBotStatusDetails;
  List<dynamic> backendOpenTrades = [];
  List<dynamic> backendTradeHistory = [];
  List<dynamic> backendDecisions = [];
  List<dynamic> backendLatestAgents = [];
  List<dynamic> backendLessons = [];
  List<Map<String, dynamic>> agentTeamChatMessages = [];
  Map<String, dynamic>? backendLastCycleResult;
  String? backendBotError;
  bool isBackendBotLoading = false;
  bool isAgentTeamChatLoading = false;
  String? agentTeamChatError;
  Map<String, dynamic>? aiTeamPreview;
  Map<String, dynamic>? aiTeamStatus;
  List<Map<String, dynamic>> aiTeamChatMessages = [];
  bool isAiTeamLoading = false;
  bool isAiTeamChatLoading = false;
  String? aiTeamError;
  Map<String, dynamic>? systemHealth;
  Map<String, dynamic>? alpacaPaperStatus;
  Map<String, dynamic>? demoWeekStatus;
  Map<String, dynamic>? chiefBotStatus;
  bool isDemoStatusLoading = false;
  String? demoStatusError;
  DateTime? lastDemoStatusUpdatedAt;

  /// Bot-tracked Spot Testnet orders from `GET /bot/testnet-orders`.
  List<dynamic> backendTestnetOrders = [];
  String? backendTestnetOrdersError;
  bool isLoadingTestnetOrders = false;

  /// `GET /performance` — closed-trade analytics (same scope as `/trades` history).
  Map<String, dynamic>? backendPerformance;
  String? backendPerformanceError;
  bool isPerformanceLoading = false;

  /// Legacy label derived from [backendBotStatusDetails] when present.
  String get backendBotStatusLabel {
    final s = backendBotStatusDetails?['status']?.toString();
    if (s == 'started' || s == 'stopped') return s!;
    return '—';
  }

  String? get userVisibleBotError => friendlyBackendMessage(backendBotError);

  String? get userVisiblePortfolioError =>
      friendlyBackendMessage(backendLastError);

  String? get userVisibleMarketError =>
      friendlyBackendMessage(backendMarketPriceError);

  String? get userVisiblePerformanceError =>
      friendlyBackendMessage(backendPerformanceError);

  String? get userVisibleAiTeamError => friendlyBackendMessage(aiTeamError);

  String? get userVisibleDemoStatusError =>
      friendlyBackendMessage(demoStatusError);

  /// Reads a float from [backendPortfolio] (snake_case keys). Safe if map is null or key missing.
  double portfolioNumber(String key, [double fallback = 0]) {
    final m = backendPortfolio;
    if (m == null) return fallback;
    final v = m[key];
    if (v == null) return fallback;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? fallback;
  }

  /// Reads an int from [backendPortfolio].
  int portfolioInt(String key, [int fallback = 0]) {
    final m = backendPortfolio;
    if (m == null) return fallback;
    final v = m[key];
    if (v == null) return fallback;
    if (v is int) return v;
    if (v is num) return v.toInt();
    return int.tryParse(v.toString()) ?? fallback;
  }

  /// After start / stop / tick: sync bot state, trades, decisions, agents, lessons, portfolio, prices.
  Future<void> refreshAfterBotAction() async {
    await refreshAllBackendBotData(showLoading: false);
    await refreshPortfolio();
    await refreshMarketPrices();
  }

  Future<void> refreshMarketPrices() async {
    isMarketPricesLoading = true;
    backendMarketPriceError = null;
    notifyListeners();
    try {
      final m = await _client.getMarketPrices();
      backendMarketPrices = m;
      marketPriceSource = m.source;
      lastMarketPriceUpdatedAt = DateTime.now();
      backendMarketPriceError = null;
    } catch (e) {
      backendMarketPriceError =
          friendlyBackendMessage(e.toString()) ?? e.toString();
    }
    isMarketPricesLoading = false;
    notifyListeners();
  }

  Future<void> refreshBackendPerformance() async {
    isPerformanceLoading = true;
    notifyListeners();
    backendPerformanceError = null;
    try {
      backendPerformance = await _client.getBackendPerformance();
      backendPerformanceError = null;
    } catch (e) {
      backendPerformance = null;
      backendPerformanceError =
          friendlyBackendMessage(e.toString()) ?? e.toString();
    } finally {
      isPerformanceLoading = false;
      notifyListeners();
    }
  }

  Future<void> refreshPortfolio() async {
    isBackendLoading = true;
    notifyListeners();
    try {
      backendPortfolio = await _client.getPortfolio();
      backendLastError = null;
    } catch (e) {
      backendPortfolio = null;
      backendLastError = friendlyBackendMessage(e.toString()) ?? e.toString();
    }
    isBackendLoading = false;
    notifyListeners();
  }

  Future<void> refreshBackendBotStatus({bool clearBotError = true}) async {
    if (clearBotError) backendBotError = null;
    try {
      backendBotStatusDetails = await _client.getBackendBotStatus();
    } catch (e) {
      backendBotError = friendlyBackendMessage(e.toString()) ?? e.toString();
    }
    notifyListeners();
  }

  String get backendExecutionModeLabel =>
      backendBotStatusDetails?['execution_mode']?.toString() ??
      systemHealth?['execution_mode']?.toString() ??
      chiefBotStatus?['execution_mode']?.toString() ??
      aiTeamStatus?['execution_mode']?.toString() ??
      '—';

  /// Developer/debug only — switches server bot execution (still no keys in app).
  Future<bool> setBackendExecutionMode(String mode) async {
    backendBotError = null;
    notifyListeners();
    try {
      await _client.setBackendExecutionMode(mode);
      await refreshBackendBotStatus(clearBotError: false);
      backendBotError = null;
      return true;
    } catch (e) {
      backendBotError = friendlyBackendMessage(e.toString()) ?? e.toString();
      return false;
    } finally {
      notifyListeners();
    }
  }

  Future<void> refreshBackendTrades({bool clearBotError = true}) async {
    if (clearBotError) backendBotError = null;
    try {
      final bundle = await _client.getBackendTrades();
      final open = bundle['open_trades'];
      final hist = bundle['history'];
      backendOpenTrades = open is List<dynamic> ? List<dynamic>.from(open) : [];
      backendTradeHistory = hist is List<dynamic>
          ? List<dynamic>.from(hist)
          : [];
    } catch (e) {
      backendBotError = friendlyBackendMessage(e.toString()) ?? e.toString();
    }
    notifyListeners();
  }

  Future<void> refreshBackendDecisions({bool clearBotError = true}) async {
    if (clearBotError) backendBotError = null;
    try {
      final body = await _client.getBackendDecisions();
      final list = body['decisions'];
      backendDecisions = list is List<dynamic> ? List<dynamic>.from(list) : [];
    } catch (e) {
      backendBotError = friendlyBackendMessage(e.toString()) ?? e.toString();
    }
    notifyListeners();
  }

  Future<void> refreshBackendAgents({bool clearBotError = true}) async {
    if (clearBotError) backendBotError = null;
    try {
      final body = await _client.getBackendAgentsLatest();
      final list = body['agents'];
      backendLatestAgents = list is List<dynamic>
          ? List<dynamic>.from(list)
          : [];
    } catch (e) {
      backendBotError = friendlyBackendMessage(e.toString()) ?? e.toString();
    }
    notifyListeners();
  }

  Future<void> refreshAiTeamPreview({
    bool showLoading = true,
    String symbol = 'BTCUSDT',
  }) async {
    if (showLoading) {
      isAiTeamLoading = true;
      notifyListeners();
    }
    aiTeamError = null;
    try {
      aiTeamPreview = await _client.getAiTeamPreview(symbol: symbol);
      aiTeamStatus = await _client.getAiTeamStatus();
      aiTeamError = null;
      await refreshBackendDecisions(clearBotError: false);
    } catch (e) {
      aiTeamError = friendlyBackendMessage(e.toString()) ?? e.toString();
    } finally {
      if (showLoading) {
        isAiTeamLoading = false;
      }
      notifyListeners();
    }
  }

  Future<void> refreshDemoStatus({bool showLoading = true}) async {
    if (showLoading) {
      isDemoStatusLoading = true;
      notifyListeners();
    }
    demoStatusError = null;
    try {
      final health = await _client.getSystemHealth();
      final executionMode = health['execution_mode']?.toString();
      final errors = <String>[];
      final alpaca = executionMode == 'ALPACA_PAPER'
          ? await _tryDemoStatusFetch(
              () => _client.getAlpacaPaperStatus(),
              errors,
              'Alpaca Paper status',
            )
          : null;
      final aiStatus = executionMode == 'ALPACA_PAPER'
          ? null
          : await _tryDemoStatusFetch(
              () => _client.getAiTeamStatus(),
              errors,
              'AI team status',
            );
      final demo = executionMode == 'ALPACA_PAPER'
          ? null
          : await _tryDemoStatusFetch(
              () => _client.getDemoWeekStatus(),
              errors,
              'Demo Week status',
            );
      final chief = await _tryDemoStatusFetch(
        () => _client.getChiefBotStatus(),
        errors,
        'Chief bot status',
      );
      final portfolio = await _tryDemoStatusFetch(
        () => _client.getPortfolio(),
        errors,
        'Portfolio',
      );
      final performance = await _tryDemoStatusFetch(
        () => _client.getBackendPerformance(),
        errors,
        'Performance',
      );
      systemHealth = health;
      alpacaPaperStatus = alpaca;
      aiTeamStatus = aiStatus;
      demoWeekStatus = demo;
      chiefBotStatus = chief;
      backendPortfolio = portfolio;
      backendPerformance = performance;
      lastDemoStatusUpdatedAt = DateTime.now();
      demoStatusError = errors.isEmpty ? null : errors.join('\n');
    } catch (e) {
      demoStatusError = friendlyBackendMessage(e.toString()) ?? e.toString();
    } finally {
      if (showLoading) {
        isDemoStatusLoading = false;
      }
      notifyListeners();
    }
  }

  Future<Map<String, dynamic>?> _tryDemoStatusFetch(
    Future<Map<String, dynamic>> Function() load,
    List<String> errors,
    String label,
  ) async {
    try {
      return await load();
    } catch (e) {
      final message = friendlyBackendMessage(e.toString()) ?? e.toString();
      errors.add('$label: $message');
      return null;
    }
  }

  Future<bool> sendAiTeamChatMessage({
    required String message,
    required String targetAgent,
    String symbol = 'BTCUSDT',
  }) async {
    final clean = message.trim();
    if (clean.isEmpty || isAiTeamChatLoading) return false;
    isAiTeamChatLoading = true;
    aiTeamError = null;
    aiTeamChatMessages.add({
      'type': 'user',
      'sender': 'You',
      'text': clean,
      'target_agent': targetAgent,
      'created_at': DateTime.now().toIso8601String(),
    });
    notifyListeners();
    try {
      final body = await _client.postAiTeamChat(
        message: clean,
        targetAgent: targetAgent,
        symbol: symbol,
      );
      final messages = body['messages'];
      if (messages is List) {
        for (final raw in messages) {
          if (raw is Map) {
            aiTeamChatMessages.add({
              'type': 'agent',
              ...Map<String, dynamic>.from(
                raw.map((k, v) => MapEntry(k.toString(), v)),
              ),
              'created_at': DateTime.now().toIso8601String(),
            });
          }
        }
      }
      final chief = body['chief_summary'];
      if (chief is Map) {
        aiTeamChatMessages.add({
          'type': 'chief',
          'sender': 'Chief AI Manager',
          'agent_key': 'CHIEF',
          ...Map<String, dynamic>.from(
            chief.map((k, v) => MapEntry(k.toString(), v)),
          ),
          'created_at': DateTime.now().toIso8601String(),
        });
      }
      aiTeamError = null;
      return true;
    } catch (e) {
      aiTeamError = friendlyBackendMessage(e.toString()) ?? e.toString();
      return false;
    } finally {
      isAiTeamChatLoading = false;
      notifyListeners();
    }
  }

  Future<bool> sendAgentTeamMessage(String message) async {
    final clean = message.trim();
    if (clean.isEmpty || isAgentTeamChatLoading) return false;
    isAgentTeamChatLoading = true;
    agentTeamChatError = null;
    agentTeamChatMessages.add({
      'sender': 'user',
      'message': clean,
      'created_at': DateTime.now().toIso8601String(),
    });
    notifyListeners();
    try {
      final body = await _client.postAgentTeamChat(clean);
      final replies = body['replies'];
      final provider = body['provider_status'];
      if (replies is List) {
        for (final raw in replies) {
          if (raw is Map) {
            agentTeamChatMessages.add({
              'sender': 'agent',
              'provider_status': provider,
              ...Map<String, dynamic>.from(
                raw.map((k, v) => MapEntry(k.toString(), v)),
              ),
              'created_at': DateTime.now().toIso8601String(),
            });
          }
        }
      }
      agentTeamChatError = null;
      return true;
    } catch (e) {
      agentTeamChatError = friendlyBackendMessage(e.toString()) ?? e.toString();
      return false;
    } finally {
      isAgentTeamChatLoading = false;
      notifyListeners();
    }
  }

  Future<void> refreshBackendTestnetOrders() async {
    isLoadingTestnetOrders = true;
    backendTestnetOrdersError = null;
    notifyListeners();
    try {
      final body = await _client.getBackendTestnetOrders();
      final list = body['orders'];
      backendTestnetOrders = list is List<dynamic>
          ? List<dynamic>.from(list)
          : [];
      backendTestnetOrdersError = null;
    } catch (e) {
      backendTestnetOrdersError =
          friendlyBackendMessage(e.toString()) ?? e.toString();
    }
    isLoadingTestnetOrders = false;
    notifyListeners();
  }

  Future<void> refreshBackendLessons({bool clearBotError = true}) async {
    if (clearBotError) backendBotError = null;
    try {
      final body = await _client.getBackendLessons();
      final list = body['lessons'];
      backendLessons = list is List<dynamic> ? List<dynamic>.from(list) : [];
    } catch (e) {
      backendBotError = friendlyBackendMessage(e.toString()) ?? e.toString();
    }
    notifyListeners();
  }

  Future<void> refreshAllBackendBotData({bool showLoading = true}) async {
    if (showLoading) {
      isBackendBotLoading = true;
      notifyListeners();
    }
    backendBotError = null;
    try {
      await refreshBackendBotStatus(clearBotError: false);
      await refreshBackendTrades(clearBotError: false);
      await refreshBackendDecisions(clearBotError: false);
      await refreshBackendAgents(clearBotError: false);
      await refreshBackendLessons(clearBotError: false);
      await refreshAiTeamPreview(showLoading: false);
      await refreshDemoStatus(showLoading: false);
    } finally {
      if (showLoading) {
        isBackendBotLoading = false;
      }
      notifyListeners();
    }
  }

  void recordBackendSyncComplete() {
    lastBackendSyncAt = DateTime.now();
    notifyListeners();
  }

  /// Refresh backend-heavy lists when user opens a shell tab (IndexedStack keeps screens alive).
  void refreshForShellTab(int index) {
    if (index == 1) {
      unawaited(refreshBackendTrades());
    } else if (index == 2) {
      unawaited(refreshAllBackendBotData(showLoading: false));
      unawaited(refreshAiTeamPreview(showLoading: false));
    } else if (index == 3) {
      unawaited(refreshBackendPerformance());
    }
  }

  void startBackendAutoRun() {
    _backendAutoRunTimer?.cancel();
    backendAutoRunActive = true;
    _backendAutoRunTimer = Timer.periodic(backendAutoRunInterval, (_) {
      unawaited(_runBackendAutoTick());
    });
    notifyListeners();
  }

  void stopBackendAutoRun() {
    _backendAutoRunTimer?.cancel();
    _backendAutoRunTimer = null;
    backendAutoRunActive = false;
    notifyListeners();
  }

  Future<void> _runBackendAutoTick() async {
    if (!backendAutoRunActive || _autoTickInFlight) return;
    _autoTickInFlight = true;
    try {
      final m = await tickBackendBot(silentLoading: true);
      if (m['status'] == 'stopped') {
        stopBackendAutoRun();
        backendBotError =
            m['message']?.toString() ?? 'Bot is stopped on the server.';
        notifyListeners();
        return;
      }
      await refreshAfterBotAction();
      backendBotError = null;
      recordBackendSyncComplete();
    } catch (_) {
      stopBackendAutoRun();
      backendBotError = kBackendDisconnectedMessage;
      notifyListeners();
    } finally {
      _autoTickInFlight = false;
    }
  }

  /// Pause periodic ticks when app goes to background (timer cancelled).
  void onAppLifecyclePaused() {
    if (!backendAutoRunActive) return;
    _lifecycleSuspendedAutoRun = true;
    _backendAutoRunTimer?.cancel();
    _backendAutoRunTimer = null;
    backendAutoRunActive = false;
    notifyListeners();
  }

  /// Resume ticks if the server bot is still started after foreground.
  Future<void> onAppLifecycleResumed() async {
    try {
      await refreshBackendBotStatus(clearBotError: false);
    } catch (_) {
      // leave backendBotError / status as-is
    }
    final started = backendBotStatusDetails?['status'] == 'started';
    if (_lifecycleSuspendedAutoRun && started) {
      _lifecycleSuspendedAutoRun = false;
      startBackendAutoRun();
    } else {
      _lifecycleSuspendedAutoRun = false;
    }
    notifyListeners();
  }

  Future<bool> startBackendBot() async {
    isBackendBotLoading = true;
    backendBotError = null;
    notifyListeners();
    try {
      final ok = await _client.startBackendBot();
      if (!ok) {
        backendBotError = 'POST /bot/start did not return status started';
        stopBackendAutoRun();
        return false;
      }
      await refreshAfterBotAction();
      recordBackendSyncComplete();
      startBackendAutoRun();
      return true;
    } catch (e) {
      backendBotError = friendlyBackendMessage(e.toString()) ?? e.toString();
      stopBackendAutoRun();
      return false;
    } finally {
      isBackendBotLoading = false;
      notifyListeners();
    }
  }

  Future<bool> stopBackendBot() async {
    stopBackendAutoRun();
    _lifecycleSuspendedAutoRun = false;
    isBackendBotLoading = true;
    backendBotError = null;
    notifyListeners();
    try {
      final ok = await _client.stopBackendBot();
      if (!ok) {
        backendBotError = 'POST /bot/stop did not return status stopped';
        return false;
      }
      await refreshBackendBotStatus(clearBotError: true);
      backendBotError = null;
      return true;
    } catch (e) {
      backendBotError = friendlyBackendMessage(e.toString()) ?? e.toString();
      return false;
    } finally {
      isBackendBotLoading = false;
      notifyListeners();
    }
  }

  /// POST /bot/force-close — then refresh status, portfolio, trades, testnet orders, decisions, agents.
  Future<Map<String, dynamic>?> forceCloseBackendPosition() async {
    isBackendBotLoading = true;
    backendBotError = null;
    notifyListeners();
    try {
      final r = await _client.postBackendForceClose();
      await refreshBackendBotStatus(clearBotError: false);
      await refreshPortfolio();
      await refreshBackendTrades(clearBotError: false);
      await refreshBackendTestnetOrders();
      await refreshBackendDecisions(clearBotError: false);
      await refreshBackendAgents(clearBotError: false);
      await refreshBackendPerformance();
      backendBotError = null;
      return r;
    } catch (e) {
      backendBotError = friendlyBackendMessage(e.toString()) ?? e.toString();
      return null;
    } finally {
      isBackendBotLoading = false;
      notifyListeners();
    }
  }

  /// Returns tick JSON: `{ cycle: ... }` or `{ status, message }` when stopped.
  Future<Map<String, dynamic>> tickBackendBot({
    bool silentLoading = false,
  }) async {
    if (!silentLoading) {
      isBackendBotLoading = true;
      backendBotError = null;
      notifyListeners();
    }
    try {
      final m = await _client.tickBackendBot();
      final cycle = m['cycle'];
      if (cycle is Map) {
        backendLastCycleResult = Map<String, dynamic>.from(
          cycle.map((k, v) => MapEntry(k.toString(), v)),
        );
      } else {
        backendLastCycleResult = null;
      }
      return m;
    } catch (e) {
      backendBotError = friendlyBackendMessage(e.toString()) ?? e.toString();
      rethrow;
    } finally {
      if (!silentLoading) {
        isBackendBotLoading = false;
      }
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _backendAutoRunTimer?.cancel();
    super.dispose();
  }
}
