import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/backend_market_prices_model.dart';
import '../utils/backend_config.dart';

/// Demo FastAPI client — no Binance, no secrets in the app.
class BackendProbeResult {
  const BackendProbeResult._({
    required this.connected,
    this.btcUsdt,
    this.ethUsdt,
    this.message,
  });

  final bool connected;
  final double? btcUsdt;
  final double? ethUsdt;
  final String? message;

  factory BackendProbeResult.success({
    required double btc,
    required double eth,
  }) {
    return BackendProbeResult._(connected: true, btcUsdt: btc, ethUsdt: eth);
  }

  factory BackendProbeResult.failure(String message) {
    return BackendProbeResult._(connected: false, message: message);
  }
}

class BackendApiClient {
  BackendApiClient({String? baseUrl})
    : baseUrl = baseUrl ?? BackendConfig.defaultBaseUrl;

  final String baseUrl;
  static const _timeout = Duration(seconds: 10);
  static const _aiTimeout = Duration(seconds: 75);

  Map<String, dynamic> _decodeObject(http.Response res) {
    if (res.statusCode != 200) {
      throw Exception('HTTP ${res.statusCode}');
    }
    final decoded = jsonDecode(res.body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception('Expected JSON object');
    }
    return decoded;
  }

  Future<BackendProbeResult> probeHealthAndPrices() async {
    try {
      final healthUri = Uri.parse('$baseUrl/health');
      final healthRes = await http.get(healthUri).timeout(_timeout);
      if (healthRes.statusCode != 200) {
        return BackendProbeResult.failure(
          'Health HTTP ${healthRes.statusCode}',
        );
      }
      final healthJson = jsonDecode(healthRes.body);
      if (healthJson is! Map<String, dynamic> || healthJson['status'] != 'ok') {
        return BackendProbeResult.failure('Unexpected /health response');
      }

      final pricesUri = Uri.parse('$baseUrl/market/prices');
      final pricesRes = await http.get(pricesUri).timeout(_timeout);
      if (pricesRes.statusCode != 200) {
        return BackendProbeResult.failure(
          'Prices HTTP ${pricesRes.statusCode}',
        );
      }
      final pricesJson = jsonDecode(pricesRes.body);
      if (pricesJson is! Map<String, dynamic>) {
        return BackendProbeResult.failure('Unexpected /market/prices shape');
      }
      final btc = pricesJson['BTCUSDT'];
      final eth = pricesJson['ETHUSDT'];
      if (btc == null || eth == null) {
        return BackendProbeResult.failure('Missing BTCUSDT or ETHUSDT');
      }
      return BackendProbeResult.success(
        btc: (btc as num).toDouble(),
        eth: (eth as num).toDouble(),
      );
    } catch (e) {
      return BackendProbeResult.failure(e.toString());
    }
  }

  /// Live backend quotes (`GET /market/prices`) including `source`.
  Future<BackendMarketPricesModel> getMarketPrices() async {
    final pricesUri = Uri.parse('$baseUrl/market/prices');
    final pricesRes = await http.get(pricesUri).timeout(_timeout);
    if (pricesRes.statusCode != 200) {
      throw Exception('Market prices HTTP ${pricesRes.statusCode}');
    }
    final decoded = jsonDecode(pricesRes.body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception('Invalid market prices JSON');
    }
    return BackendMarketPricesModel.fromJson(decoded);
  }

  Future<Map<String, dynamic>> getPortfolio() async {
    final res = await http
        .get(Uri.parse('$baseUrl/portfolio'))
        .timeout(_timeout);
    return _decodeObject(res);
  }

  /// `GET /performance` — closed-trade stats for current execution mode.
  Future<Map<String, dynamic>> getBackendPerformance() async {
    final res = await http
        .get(Uri.parse('$baseUrl/performance'))
        .timeout(_timeout);
    return _decodeObject(res);
  }

  /// Multi-agent demo bot: `POST /bot/start`
  Future<bool> startBackendBot() async {
    final res = await http
        .post(Uri.parse('$baseUrl/bot/start'))
        .timeout(_timeout);
    if (res.statusCode != 200) return false;
    final decoded = jsonDecode(res.body);
    return decoded is Map<String, dynamic> && decoded['status'] == 'started';
  }

  /// `POST /bot/stop`
  Future<bool> stopBackendBot() async {
    final res = await http
        .post(Uri.parse('$baseUrl/bot/stop'))
        .timeout(_timeout);
    if (res.statusCode != 200) return false;
    final decoded = jsonDecode(res.body);
    return decoded is Map<String, dynamic> && decoded['status'] == 'stopped';
  }

  /// `POST /bot/force-close` — manual close (paper demo legs or Spot Testnet MARKET SELL).
  Future<Map<String, dynamic>> postBackendForceClose() async {
    final res = await http
        .post(Uri.parse('$baseUrl/bot/force-close'))
        .timeout(_timeout);
    if (res.statusCode != 200) {
      Object? detail;
      try {
        final decoded = jsonDecode(res.body);
        if (decoded is Map<String, dynamic>) {
          detail = decoded['detail'] ?? decoded['message'];
        }
      } catch (_) {
        detail = res.body;
      }
      throw Exception(
        detail?.toString() ?? 'Force close HTTP ${res.statusCode}',
      );
    }
    final decoded = jsonDecode(res.body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception('Invalid force-close JSON');
    }
    return decoded;
  }

  /// `POST /bot/tick` — full JSON (cycle or stopped message).
  Future<Map<String, dynamic>> tickBackendBot() async {
    final res = await http
        .post(Uri.parse('$baseUrl/bot/tick'))
        .timeout(_timeout);
    if (res.statusCode != 200) {
      throw Exception('Tick HTTP ${res.statusCode}');
    }
    final decoded = jsonDecode(res.body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception('Invalid tick JSON');
    }
    return decoded;
  }

  /// `GET /bot/status`
  Future<Map<String, dynamic>> getBackendBotStatus() async {
    final res = await http
        .get(Uri.parse('$baseUrl/bot/status'))
        .timeout(_timeout);
    return _decodeObject(res);
  }

  /// `GET /bot/execution-mode`
  Future<Map<String, dynamic>> getBackendExecutionMode() async {
    final res = await http
        .get(Uri.parse('$baseUrl/bot/execution-mode'))
        .timeout(_timeout);
    return _decodeObject(res);
  }

  /// `POST /bot/execution-mode` — `{ "mode": "PAPER_DEMO" | "BINANCE_TESTNET" }`
  Future<Map<String, dynamic>> setBackendExecutionMode(String mode) async {
    final uri = Uri.parse('$baseUrl/bot/execution-mode');
    final res = await http
        .post(
          uri,
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode({'mode': mode}),
        )
        .timeout(_timeout);
    if (res.statusCode != 200) {
      final decoded = jsonDecode(res.body);
      final detail = decoded is Map<String, dynamic>
          ? decoded['detail']
          : res.body;
      throw Exception(detail?.toString() ?? 'HTTP ${res.statusCode}');
    }
    final decoded = jsonDecode(res.body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception('Invalid execution-mode response');
    }
    return decoded;
  }

  /// `GET /bot/testnet-orders` — `{ orders: [...], warning }`
  Future<Map<String, dynamic>> getBackendTestnetOrders() async {
    final res = await http
        .get(Uri.parse('$baseUrl/bot/testnet-orders'))
        .timeout(_timeout);
    return _decodeObject(res);
  }

  /// `GET /trades` — `{ open_trades, history }`
  Future<Map<String, dynamic>> getBackendTrades() async {
    final res = await http.get(Uri.parse('$baseUrl/trades')).timeout(_timeout);
    return _decodeObject(res);
  }

  /// `GET /decisions`
  Future<Map<String, dynamic>> getBackendDecisions() async {
    final res = await http
        .get(Uri.parse('$baseUrl/decisions'))
        .timeout(_timeout);
    return _decodeObject(res);
  }

  /// `GET /agents/latest`
  Future<Map<String, dynamic>> getBackendAgentsLatest() async {
    final res = await http
        .get(Uri.parse('$baseUrl/agents/latest'))
        .timeout(_timeout);
    return _decodeObject(res);
  }

  /// `GET /ai-team/preview` — 4-agent team plus Chief AI decision.
  Future<Map<String, dynamic>> getAiTeamPreview({
    String symbol = 'BTCUSDT',
  }) async {
    final uri = Uri.parse(
      '$baseUrl/ai-team/preview',
    ).replace(queryParameters: {'symbol': symbol});
    final res = await http.get(uri).timeout(_aiTimeout);
    return _decodeObject(res);
  }

  /// `GET /ai-team/status` — real/mock/connected status per AI team agent.
  Future<Map<String, dynamic>> getAiTeamStatus() async {
    final res = await http
        .get(Uri.parse('$baseUrl/ai-team/status'))
        .timeout(_aiTimeout);
    return _decodeObject(res);
  }

  /// `POST /ai-team/chat` — advisory-only multi-agent chat.
  Future<Map<String, dynamic>> postAiTeamChat({
    required String message,
    required String targetAgent,
    String symbol = 'BTCUSDT',
  }) async {
    final res = await http
        .post(
          Uri.parse('$baseUrl/ai-team/chat'),
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode({
            'message': message,
            'target_agent': targetAgent,
            'symbol': symbol,
          }),
        )
        .timeout(_aiTimeout);
    return _decodeObject(res);
  }

  /// `GET /system/health` — read-only full system health.
  Future<Map<String, dynamic>> getSystemHealth() async {
    final res = await http
        .get(Uri.parse('$baseUrl/system/health'))
        .timeout(_timeout);
    return _decodeObject(res);
  }

  /// `GET /demo-week/status` — read-only demo week limits/status.
  Future<Map<String, dynamic>> getDemoWeekStatus() async {
    final res = await http
        .get(Uri.parse('$baseUrl/demo-week/status'))
        .timeout(_timeout);
    return _decodeObject(res);
  }

  /// `GET /chief-bot/status` — read-only Chief autonomy status.
  Future<Map<String, dynamic>> getChiefBotStatus() async {
    final res = await http
        .get(Uri.parse('$baseUrl/chief-bot/status'))
        .timeout(_timeout);
    return _decodeObject(res);
  }

  /// `POST /ai-advisor/team-chat` — ask all agent personas for opinions.
  Future<Map<String, dynamic>> postAgentTeamChat(String message) async {
    final res = await http
        .post(
          Uri.parse('$baseUrl/ai-advisor/team-chat'),
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode({'message': message}),
        )
        .timeout(_aiTimeout);
    return _decodeObject(res);
  }

  /// `GET /lessons`
  Future<Map<String, dynamic>> getBackendLessons() async {
    final res = await http.get(Uri.parse('$baseUrl/lessons')).timeout(_timeout);
    return _decodeObject(res);
  }
}
