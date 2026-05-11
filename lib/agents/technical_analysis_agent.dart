import '../models/agent_result_model.dart';

class TechnicalAnalysisAgent {
  AgentResultModel analyze({
    required String symbol,
    required List<double> recentPrices,
    required double currentPrice,
  }) {
    if (recentPrices.length < 2) {
      return AgentResultModel(
        agentName: 'Technical Analysis Agent',
        symbol: symbol,
        score: 0,
        explanation: 'Insufficient candles, market considered sideways.',
        createdAt: DateTime.now(),
      );
    }

    final first = recentPrices.first;
    final last = recentPrices.last;
    final trendPercent = ((last - first) / first) * 100;

    double momentum = 0;
    for (var i = 1; i < recentPrices.length; i++) {
      momentum += (recentPrices[i] - recentPrices[i - 1]).abs();
    }
    momentum = momentum / recentPrices.length;

    final mean = recentPrices.reduce((a, b) => a + b) / recentPrices.length;
    double variance = 0;
    for (final p in recentPrices) {
      final diff = p - mean;
      variance += diff * diff;
    }
    final volatility = (variance / recentPrices.length).sqrtSafe();

    final normalizedMomentum = (momentum / currentPrice) * 1000;
    final normalizedVolatility = (volatility / currentPrice) * 1000;
    final score = (trendPercent * 6 + normalizedMomentum * 12)
        .clamp(-100, 100)
        .toDouble();

    final trendLabel = score > 20
        ? 'uptrend'
        : score < -20
        ? 'downtrend'
        : 'sideways market';
    final explanation =
        'Detected $trendLabel. Momentum ${normalizedMomentum.toStringAsFixed(2)}, volatility ${normalizedVolatility.toStringAsFixed(2)}.';

    return AgentResultModel(
      agentName: 'Technical Analysis Agent',
      symbol: symbol,
      score: score,
      explanation: explanation,
      createdAt: DateTime.now(),
    );
  }
}

extension on double {
  double sqrtSafe() {
    if (this <= 0) return 0;
    var x = this;
    var y = 1.0;
    const e = 0.000001;
    while (x - y > e) {
      x = (x + y) / 2;
      y = this / x;
    }
    return x;
  }
}
