class AgentResultModel {
  const AgentResultModel({
    required this.agentName,
    required this.symbol,
    required this.score,
    this.approved,
    this.action,
    this.confidence,
    required this.explanation,
    required this.createdAt,
  });

  final String agentName;
  final String symbol;
  final double score;
  final bool? approved;
  final String? action;
  final double? confidence;
  final String explanation;
  final DateTime createdAt;
}
