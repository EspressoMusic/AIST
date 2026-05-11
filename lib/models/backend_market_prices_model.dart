/// Parsed body of `GET /market/prices` from our FastAPI backend.
class BackendMarketPricesModel {
  const BackendMarketPricesModel({
    required this.btcUsdt,
    required this.ethUsdt,
    required this.source,
  });

  final double btcUsdt;
  final double ethUsdt;
  /// Backend raw value, e.g. `binance_public` or `fallback_dummy`.
  final String source;

  factory BackendMarketPricesModel.fromJson(Map<String, dynamic> json) {
    final btc = json['BTCUSDT'];
    final eth = json['ETHUSDT'];
    final src = json['source'];
    if (btc == null || eth == null) {
      throw FormatException('Missing BTCUSDT or ETHUSDT in market prices JSON');
    }
    return BackendMarketPricesModel(
      btcUsdt: (btc as num).toDouble(),
      ethUsdt: (eth as num).toDouble(),
      source: src?.toString() ?? 'fallback_dummy',
    );
  }

  String get sourceDisplayLabel {
    switch (source) {
      case 'binance_public':
        return 'Binance public';
      case 'fallback_dummy':
        return 'Fallback demo';
      default:
        return source;
    }
  }
}
