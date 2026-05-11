import '../models/agent_result_model.dart';

class StrategyAgent {
  AgentResultModel decide({
    required String symbol,
    required AgentResultModel newsResult,
    required AgentResultModel technicalResult,
    required AgentResultModel riskResult,
  }) {
    if (riskResult.approved != true) {
      return AgentResultModel(
        agentName: 'Strategy Agent',
        symbol: symbol,
        score: 0,
        action: 'HOLD',
        confidence: 15,
        explanation: 'Risk agent rejected trade, strategy falls back to HOLD.',
        createdAt: DateTime.now(),
      );
    }

    final combined = newsResult.score * 0.3 + technicalResult.score * 0.7;
    final action = combined > 10
        ? 'BUY'
        : combined < -10
        ? 'SELL'
        : 'HOLD';
    final confidence = (combined.abs() + riskResult.score * 0.35)
        .clamp(0, 100)
        .toDouble();

    return AgentResultModel(
      agentName: 'Strategy Agent',
      symbol: symbol,
      score: combined,
      action: action,
      confidence: confidence,
      explanation:
          'Strategy recommends $action with confidence ${confidence.toStringAsFixed(1)}.',
      createdAt: DateTime.now(),
    );
  }
}
