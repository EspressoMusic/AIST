import '../models/activity_log_model.dart';
import '../models/agent_result_model.dart';
import '../models/bot_settings_model.dart';
import '../models/coordinated_decision_model.dart';
import '../models/trade_lesson_model.dart';
import '../models/trade_model.dart';
import 'execution_agent.dart';
import 'learning_agent.dart';
import 'news_agent.dart';
import 'risk_agent.dart';
import 'strategy_agent.dart';
import 'technical_analysis_agent.dart';

class CoordinatorResult {
  const CoordinatorResult({
    required this.agentResults,
    required this.coordinatedDecision,
    required this.executionResult,
    required this.logs,
  });

  final List<AgentResultModel> agentResults;
  final CoordinatedDecisionModel coordinatedDecision;
  final ExecutionResult executionResult;
  final List<ActivityLogModel> logs;
}

class DecisionCoordinator {
  DecisionCoordinator({
    required NewsAgent newsAgent,
    required TechnicalAnalysisAgent technicalAgent,
    required RiskAgent riskAgent,
    required StrategyAgent strategyAgent,
    required ExecutionAgent executionAgent,
    LearningAgent? learningAgent,
  }) : _newsAgent = newsAgent,
       _technicalAgent = technicalAgent,
       _riskAgent = riskAgent,
       _strategyAgent = strategyAgent,
       _executionAgent = executionAgent,
       _learningAgent = learningAgent ?? LearningAgent();

  final NewsAgent _newsAgent;
  final TechnicalAnalysisAgent _technicalAgent;
  final RiskAgent _riskAgent;
  final StrategyAgent _strategyAgent;
  final ExecutionAgent _executionAgent;
  final LearningAgent _learningAgent;

  CoordinatorResult run({
    required String symbol,
    required List<double> recentPrices,
    required double currentPrice,
    required List<TradeModel> openTrades,
    required Map<String, double> prices,
    required BotSettingsModel settings,
    required int tradesOpenedToday,
    List<TradeLessonModel> recentLessons = const [],
  }) {
    final logs = <ActivityLogModel>[];
    final news = _newsAgent.analyze(symbol);
    logs.add(
      ActivityLogModel(
        event: 'News Agent',
        message: 'News Agent analyzed $symbol.',
        timestamp: news.createdAt,
      ),
    );

    final technical = _technicalAgent.analyze(
      symbol: symbol,
      recentPrices: recentPrices,
      currentPrice: currentPrice,
    );
    logs.add(
      ActivityLogModel(
        event: 'Technical Agent',
        message: technical.explanation,
        timestamp: technical.createdAt,
      ),
    );

    final preliminaryAction = technical.score >= 0 ? 'BUY' : 'SELL';
    final movement = recentPrices.length < 2
        ? 0.0
        : ((recentPrices.last - recentPrices.first) / recentPrices.first)
              .clamp(-1.0, 1.0)
              .toDouble();
    final confidenceHint = (news.score.abs() + technical.score.abs()) / 2;
    final risk = _riskAgent.evaluate(
      symbol: symbol,
      settings: settings,
      openTrades: openTrades,
      tradesOpenedToday: tradesOpenedToday,
      newsScore: news.score,
      technicalScore: technical.score,
      marketMovement: movement,
      confidenceHint: confidenceHint,
    );
    logs.add(
      ActivityLogModel(
        event: 'Risk Agent',
        message: risk.explanation,
        timestamp: risk.createdAt,
      ),
    );

    final strategy = _strategyAgent.decide(
      symbol: symbol,
      newsResult: news,
      technicalResult: technical,
      riskResult: risk.copyWithAction(preliminaryAction),
    );
    logs.add(
      ActivityLogModel(
        event: 'Strategy Agent',
        message: strategy.explanation,
        timestamp: strategy.createdAt,
      ),
    );

    final learning = _learningAgent.analyzePipeline(
      symbol: symbol,
      recentLessons: recentLessons,
    );
    logs.add(
      ActivityLogModel(
        event: 'Learning Agent',
        message: learning.explanation,
        timestamp: learning.createdAt,
      ),
    );

    final dynamicStopLoss =
        (1.0 + (technical.score.abs() / 100) * 2 + (100 - risk.score) / 100)
            .clamp(0.7, 4.5)
            .toDouble();
    final dynamicTakeProfit =
        (1.4 + (strategy.confidence ?? 0) / 100 * 4 + risk.score / 100)
            .clamp(1.0, 8.0)
            .toDouble();

    final coordinated = CoordinatedDecisionModel(
      symbol: symbol,
      finalAction: strategy.action ?? 'HOLD',
      confidence: strategy.confidence ?? 0,
      newsScore: news.score,
      technicalScore: technical.score,
      riskScore: risk.score,
      riskApproved: risk.approved ?? false,
      suggestedStopLossPercent: dynamicStopLoss,
      suggestedTakeProfitPercent: dynamicTakeProfit,
      explanation:
          'News ${news.score.toStringAsFixed(1)}, Technical ${technical.score.toStringAsFixed(1)}, Risk ${risk.score.toStringAsFixed(1)}. Agent SL ${dynamicStopLoss.toStringAsFixed(2)}%, TP ${dynamicTakeProfit.toStringAsFixed(2)}%. ${strategy.explanation} Learning: ${learning.explanation}',
      createdAt: DateTime.now(),
    );

    final agentsApprovedAtOpen = <String>[
      news.agentName,
      technical.agentName,
      if (risk.approved == true) risk.agentName,
      if ((strategy.action ?? 'HOLD') != 'HOLD') strategy.agentName,
      learning.agentName,
    ];

    final execution = _executionAgent.execute(
      symbol: symbol,
      finalAction: coordinated.finalAction,
      riskApproved: coordinated.riskApproved,
      openTrades: openTrades,
      prices: prices,
      settings: settings,
      suggestedStopLossPercent: coordinated.suggestedStopLossPercent,
      suggestedTakeProfitPercent: coordinated.suggestedTakeProfitPercent,
      agentsApprovedAtOpen: agentsApprovedAtOpen,
      coordinatorExplanationAtOpen: coordinated.explanation,
    );
    logs.addAll(execution.logs);

    final executionResult = AgentResultModel(
      agentName: 'Execution Agent',
      symbol: symbol,
      score: execution.openedTrades.isNotEmpty
          ? 80
          : (execution.closedTrades.isNotEmpty ? 65 : 40),
      approved: coordinated.riskApproved,
      action: execution.openedTrades.isNotEmpty
          ? coordinated.finalAction
          : 'HOLD',
      confidence: coordinated.confidence,
      explanation: execution.logs.isNotEmpty
          ? execution.logs.first.message
          : 'No execution action taken.',
      createdAt: DateTime.now(),
    );

    final coordinatorResult = AgentResultModel(
      agentName: 'Decision Coordinator',
      symbol: symbol,
      score: ((coordinated.newsScore + coordinated.technicalScore) / 2)
          .clamp(-100, 100)
          .toDouble(),
      approved: coordinated.riskApproved,
      action: coordinated.finalAction,
      confidence: coordinated.confidence,
      explanation: coordinated.explanation,
      createdAt: coordinated.createdAt,
    );

    return CoordinatorResult(
      agentResults: [
        news,
        technical,
        risk,
        strategy,
        learning,
        executionResult,
        coordinatorResult,
      ],
      coordinatedDecision: coordinated,
      executionResult: execution,
      logs: logs,
    );
  }
}

extension on AgentResultModel {
  AgentResultModel copyWithAction(String action) {
    return AgentResultModel(
      agentName: agentName,
      symbol: symbol,
      score: score,
      approved: approved,
      action: action,
      confidence: confidence,
      explanation: explanation,
      createdAt: createdAt,
    );
  }
}
