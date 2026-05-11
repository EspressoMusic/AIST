import 'dart:math';

import '../models/agent_result_model.dart';
import '../models/trade_lesson_model.dart';
import '../models/trade_model.dart';

/// Dummy learning layer: reviews closed trades and summarizes posture for the pipeline.
class LearningAgent {
  LearningAgent({Random? random}) : _random = random ?? Random();

  final Random _random;

  AgentResultModel analyzePipeline({
    required String symbol,
    required List<TradeLessonModel> recentLessons,
  }) {
    final now = DateTime.now();
    if (recentLessons.isEmpty) {
      return AgentResultModel(
        agentName: 'Learning Agent',
        symbol: symbol,
        score: 50,
        approved: true,
        action: 'LEARN',
        confidence: 55,
        explanation:
            'Baseline posture: waiting for closed-trade samples to refine heuristics.',
        createdAt: now,
      );
    }

    final wins = recentLessons.where((l) => l.wasSuccessful).length;
    final winRate = wins / recentLessons.length;
    final last = recentLessons.first;
    return AgentResultModel(
      agentName: 'Learning Agent',
      symbol: symbol,
      score: (winRate * 100).clamp(0, 100),
      approved: true,
      action: 'LEARN',
      confidence: (55 + winRate * 30).clamp(0, 100),
      explanation:
          'Recent lessons: ${recentLessons.length} trades reviewed '
          '($wins favorable). Latest: ${last.lesson}',
      createdAt: now,
    );
  }

  TradeLessonModel lessonFromClosedTrade(TradeModel trade) {
    final ok = trade.profitLoss >= 0;
    final volatilityHint = trade.profitLoss.abs() > 200 ? 'high' : 'moderate';

    late final String lesson;
    late final String improvement;

    if (!_randomBool(0.85)) {
      lesson =
          'News signal was strong and helped the outcome on ${trade.symbol}.';
      improvement =
          ok
              ? 'Keep aligning entries when sentiment and tape agree.'
              : 'Require stronger technical confirmation before trusting headlines.';
    } else if (trade.profitLoss < -80) {
      lesson = 'Risk was too high for current volatility regime.';
      improvement =
          'Tighten sizing when volatility is $volatilityHint and trail exits sooner.';
    } else if (trade.profitLoss > 120) {
      lesson = 'Entry was good; capture worked with the simulated tape.';
      improvement =
          ok
              ? 'Reuse similar setups but avoid chasing extended moves.'
              : 'Book partial profits earlier when momentum stalls.';
    } else if (!_randomBool(0.5)) {
      lesson = 'Technical signal was weak; setup was marginal.';
      improvement =
          'Skip similar ranges until breakout volume confirms.';
    } else {
      lesson = 'Exit timing was ${ok ? 'reasonable' : 'too late'} for this swing.';
      improvement =
          ok
              ? 'Consider scaling out into strength.'
              : 'Define exit triggers earlier relative to agent TP.';
    }

    return TradeLessonModel(
      tradeId: trade.id,
      symbol: trade.symbol,
      wasSuccessful: ok,
      lesson: lesson,
      improvementSuggestion: improvement,
      createdAt: trade.closedAt ?? DateTime.now(),
    );
  }

  bool _randomBool(double trueProbability) =>
      _random.nextDouble() < trueProbability;
}
