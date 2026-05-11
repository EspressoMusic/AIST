enum DisplayMode { simple, advanced }

extension DisplayModeLabels on DisplayMode {
  String get label => switch (this) {
    DisplayMode.simple => 'Simple',
    DisplayMode.advanced => 'Advanced',
  };

  String get storageValue => switch (this) {
    DisplayMode.simple => 'simple',
    DisplayMode.advanced => 'advanced',
  };

  static DisplayMode fromStorage(Object? _) => DisplayMode.simple;
}

class BotSettingsModel {
  const BotSettingsModel({
    required this.displayMode,
    required this.maxOpenPositions,
    required this.maxTradesPerDay,
    required this.riskScoreCutoff,
    required this.volatilityThreshold,
    required this.stopLossPercent,
    required this.takeProfitPercent,
    required this.positionSizeUsd,
  });

  final DisplayMode displayMode;
  final int maxOpenPositions;
  final int maxTradesPerDay;
  final double riskScoreCutoff;
  final double volatilityThreshold;
  final double stopLossPercent;
  final double takeProfitPercent;
  final double positionSizeUsd;

  static const defaults = BotSettingsModel(
    displayMode: DisplayMode.simple,
    maxOpenPositions: 5,
    maxTradesPerDay: 20,
    riskScoreCutoff: 6.5,
    volatilityThreshold: 65,
    stopLossPercent: 1.5,
    takeProfitPercent: 2.5,
    positionSizeUsd: 1000,
  );

  BotSettingsModel copyWith({
    DisplayMode? displayMode,
    int? maxOpenPositions,
    int? maxTradesPerDay,
    double? riskScoreCutoff,
    double? volatilityThreshold,
    double? stopLossPercent,
    double? takeProfitPercent,
    double? positionSizeUsd,
  }) {
    return BotSettingsModel(
      displayMode: DisplayMode.simple,
      maxOpenPositions: maxOpenPositions ?? this.maxOpenPositions,
      maxTradesPerDay: maxTradesPerDay ?? this.maxTradesPerDay,
      riskScoreCutoff: riskScoreCutoff ?? this.riskScoreCutoff,
      volatilityThreshold: volatilityThreshold ?? this.volatilityThreshold,
      stopLossPercent: stopLossPercent ?? this.stopLossPercent,
      takeProfitPercent: takeProfitPercent ?? this.takeProfitPercent,
      positionSizeUsd: positionSizeUsd ?? this.positionSizeUsd,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'maxOpenPositions': maxOpenPositions,
      'displayMode': DisplayMode.simple.storageValue,
      'maxTradesPerDay': maxTradesPerDay,
      'riskScoreCutoff': riskScoreCutoff,
      'volatilityThreshold': volatilityThreshold,
      'stopLossPercent': stopLossPercent,
      'takeProfitPercent': takeProfitPercent,
      'positionSizeUsd': positionSizeUsd,
    };
  }

  factory BotSettingsModel.fromMap(Map<String, Object?> map) {
    return BotSettingsModel(
      displayMode: DisplayMode.simple,
      maxOpenPositions:
          (map['maxOpenPositions'] as num?)?.toInt() ??
          defaults.maxOpenPositions,
      maxTradesPerDay:
          (map['maxTradesPerDay'] as num?)?.toInt() ?? defaults.maxTradesPerDay,
      riskScoreCutoff:
          (map['riskScoreCutoff'] as num?)?.toDouble() ??
          defaults.riskScoreCutoff,
      volatilityThreshold:
          (map['volatilityThreshold'] as num?)?.toDouble() ??
          defaults.volatilityThreshold,
      stopLossPercent:
          (map['stopLossPercent'] as num?)?.toDouble() ??
          defaults.stopLossPercent,
      takeProfitPercent:
          (map['takeProfitPercent'] as num?)?.toDouble() ??
          defaults.takeProfitPercent,
      positionSizeUsd:
          (map['positionSizeUsd'] as num?)?.toDouble() ??
          defaults.positionSizeUsd,
    );
  }
}
