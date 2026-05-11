class TradeModel {
  const TradeModel({
    required this.id,
    required this.symbol,
    required this.side,
    required this.quantity,
    required this.entryPrice,
    required this.currentPrice,
    required this.profitLoss,
    required this.reason,
    required this.openedAt,
    this.agentStopLossPrice,
    this.agentTakeProfitPrice,
    this.closedAt,
    this.isOpen = true,
    this.agentsApprovedAtOpen = const [],
    this.coordinatorExplanationAtOpen = '',
  });

  final String id;
  final String symbol;
  final String side;
  final double quantity;
  final double entryPrice;
  final double currentPrice;
  final double profitLoss;
  final String reason;
  final DateTime openedAt;
  final double? agentStopLossPrice;
  final double? agentTakeProfitPrice;
  final DateTime? closedAt;
  final bool isOpen;
  /// Agents that contributed sign-off when the trade was opened (simulation).
  final List<String> agentsApprovedAtOpen;
  /// Coordinator narrative captured at trade open.
  final String coordinatorExplanationAtOpen;

  TradeModel copyWith({
    String? id,
    String? symbol,
    String? side,
    double? quantity,
    double? entryPrice,
    double? currentPrice,
    double? profitLoss,
    String? reason,
    DateTime? openedAt,
    double? agentStopLossPrice,
    double? agentTakeProfitPrice,
    DateTime? closedAt,
    bool? isOpen,
    List<String>? agentsApprovedAtOpen,
    String? coordinatorExplanationAtOpen,
  }) {
    return TradeModel(
      id: id ?? this.id,
      symbol: symbol ?? this.symbol,
      side: side ?? this.side,
      quantity: quantity ?? this.quantity,
      entryPrice: entryPrice ?? this.entryPrice,
      currentPrice: currentPrice ?? this.currentPrice,
      profitLoss: profitLoss ?? this.profitLoss,
      reason: reason ?? this.reason,
      openedAt: openedAt ?? this.openedAt,
      agentStopLossPrice: agentStopLossPrice ?? this.agentStopLossPrice,
      agentTakeProfitPrice: agentTakeProfitPrice ?? this.agentTakeProfitPrice,
      closedAt: closedAt ?? this.closedAt,
      isOpen: isOpen ?? this.isOpen,
      agentsApprovedAtOpen: agentsApprovedAtOpen ?? this.agentsApprovedAtOpen,
      coordinatorExplanationAtOpen:
          coordinatorExplanationAtOpen ?? this.coordinatorExplanationAtOpen,
    );
  }
}
