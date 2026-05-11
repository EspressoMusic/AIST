class CoordinatedDecisionModel {
  const CoordinatedDecisionModel({
    required this.symbol,
    required this.finalAction,
    required this.confidence,
    required this.newsScore,
    required this.technicalScore,
    required this.riskScore,
    required this.riskApproved,
    required this.suggestedStopLossPercent,
    required this.suggestedTakeProfitPercent,
    required this.explanation,
    required this.createdAt,
  });

  final String symbol;
  final String finalAction;
  final double confidence;
  final double newsScore;
  final double technicalScore;
  final double riskScore;
  final bool riskApproved;
  final double suggestedStopLossPercent;
  final double suggestedTakeProfitPercent;
  final String explanation;
  final DateTime createdAt;
}
