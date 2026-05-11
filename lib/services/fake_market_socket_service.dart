import 'dart:async';
import 'dart:math';

class FakeMarketSocketService {
  final StreamController<Map<String, double>> _controller =
      StreamController<Map<String, double>>.broadcast();
  final Random _random = Random();

  final Map<String, double> _prices = {'BTCUSDT': 63500, 'ETHUSDT': 3120};

  Timer? _timer;

  Stream<Map<String, double>> get priceStream => _controller.stream;
  Map<String, double> get currentPrices => Map.unmodifiable(_prices);

  void connect({List<String> symbols = const ['BTCUSDT', 'ETHUSDT']}) {
    _timer?.cancel();
    for (final symbol in symbols) {
      _prices.putIfAbsent(symbol, () => 100 + _random.nextDouble() * 300);
    }
    _controller.add(Map<String, double>.from(_prices));

    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      for (final symbol in symbols) {
        final current = _prices[symbol] ?? 1000;
        final drift = symbol == 'BTCUSDT' ? 120 : 12;
        final delta = (_random.nextDouble() - 0.5) * drift;
        final updated = (current + delta).clamp(0.0001, double.infinity);
        _prices[symbol] = updated;
      }
      _controller.add(Map<String, double>.from(_prices));
    });
  }

  void disconnect() {
    _timer?.cancel();
    _timer = null;
  }

  void dispose() {
    disconnect();
    _controller.close();
  }
}
