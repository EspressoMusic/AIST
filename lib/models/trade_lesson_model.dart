class TradeLessonModel {
  const TradeLessonModel({
    required this.tradeId,
    required this.symbol,
    required this.wasSuccessful,
    required this.lesson,
    required this.improvementSuggestion,
    required this.createdAt,
  });

  final String tradeId;
  final String symbol;
  final bool wasSuccessful;
  final String lesson;
  final String improvementSuggestion;
  final DateTime createdAt;
}
