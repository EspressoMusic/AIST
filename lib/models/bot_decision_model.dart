import 'agent_result_model.dart';

class BotDecisionModel {
  const BotDecisionModel({
    required this.symbol,
    required this.action,
    required this.confidence,
    required this.newsScore,
    required this.technicalScore,
    required this.riskScore,
    required this.riskApproved,
    required this.explanation,
    required this.agentResults,
    required this.timestamp,
  });

  final String symbol;
  final String action;
  final double confidence;
  final double newsScore;
  final double technicalScore;
  final double riskScore;
  final bool riskApproved;
  final String explanation;
  final List<AgentResultModel> agentResults;
  final DateTime timestamp;
}
