import '../models/agent_result_model.dart';
import '../models/bot_settings_model.dart';
import '../models/trade_model.dart';

class RiskAgent {
  AgentResultModel evaluate({
    required String symbol,
    required BotSettingsModel settings,
    required List<TradeModel> openTrades,
    required int tradesOpenedToday,
    required double newsScore,
    required double technicalScore,
    required double marketMovement,
    required double confidenceHint,
  }) {
    final volatilityPenalty = (technicalScore.abs() / 100) * 25;
    final movementPenalty = marketMovement.abs() * 4;
    final positionPenalty = (settings.positionSizeUsd / 10000) * 12;
    final confidenceBonus = confidenceHint * 0.18;
    final base =
        ((newsScore + 100) / 2) * 0.35 + ((technicalScore + 100) / 2) * 0.65;
    final riskScore =
        (base -
                volatilityPenalty -
                movementPenalty -
                positionPenalty +
                confidenceBonus)
            .clamp(0, 100)
            .toDouble();
    final cutoff = (settings.riskScoreCutoff * 10).clamp(0, 100);

    String? rejection;
    if (openTrades.length >= settings.maxOpenPositions) {
      rejection = 'Max positions reached';
    } else if (tradesOpenedToday >= settings.maxTradesPerDay) {
      rejection = 'Daily trade limit reached';
    } else if (riskScore < cutoff) {
      rejection = 'Risk score too low';
    } else if (settings.positionSizeUsd <= 0) {
      rejection = 'Position size is invalid';
    }

    return AgentResultModel(
      agentName: 'Risk Agent',
      symbol: symbol,
      score: riskScore,
      approved: rejection == null,
      explanation: rejection == null
          ? 'Trade approved. Dynamic risk score ${riskScore.toStringAsFixed(1)} based on volatility, movement, confidence and position size.'
          : 'Trade rejected: $rejection.',
      createdAt: DateTime.now(),
    );
  }
}
