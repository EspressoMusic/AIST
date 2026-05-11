class BotStatusModel {
  const BotStatusModel({
    required this.isActive,
    required this.demoBalance,
    required this.profitLoss,
    required this.openTradesCount,
  });

  final bool isActive;
  final double demoBalance;
  final double profitLoss;
  final int openTradesCount;

  BotStatusModel copyWith({
    bool? isActive,
    double? demoBalance,
    double? profitLoss,
    int? openTradesCount,
  }) {
    return BotStatusModel(
      isActive: isActive ?? this.isActive,
      demoBalance: demoBalance ?? this.demoBalance,
      profitLoss: profitLoss ?? this.profitLoss,
      openTradesCount: openTradesCount ?? this.openTradesCount,
    );
  }
}
