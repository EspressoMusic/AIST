import 'dart:math';

import '../models/agent_result_model.dart';

class NewsAgent {
  NewsAgent() : _random = Random();

  final Random _random;

  AgentResultModel analyze(String symbol) {
    final score = -100 + _random.nextDouble() * 200;
    final explanation = score > 35
        ? 'Positive crypto ETF news detected for $symbol.'
        : score < -35
        ? 'Negative regulation headline detected for $symbol.'
        : 'No major news impact detected for $symbol.';
    return AgentResultModel(
      agentName: 'News Agent',
      symbol: symbol,
      score: score,
      explanation: explanation,
      createdAt: DateTime.now(),
    );
  }
}
