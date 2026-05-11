import 'package:shared_preferences/shared_preferences.dart';

import '../models/bot_settings_model.dart';

class SettingsStorageService {
  static const _displayMode = 'settings.displayMode';
  static const _maxOpenPositions = 'settings.maxOpenPositions';
  static const _maxTradesPerDay = 'settings.maxTradesPerDay';
  static const _riskScoreCutoff = 'settings.riskScoreCutoff';
  static const _volatilityThreshold = 'settings.volatilityThreshold';
  static const _stopLossPercent = 'settings.stopLossPercent';
  static const _takeProfitPercent = 'settings.takeProfitPercent';
  static const _positionSizeUsd = 'settings.positionSizeUsd';

  Future<BotSettingsModel> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    return BotSettingsModel(
      displayMode: DisplayMode.simple,
      maxOpenPositions:
          prefs.getInt(_maxOpenPositions) ??
          BotSettingsModel.defaults.maxOpenPositions,
      maxTradesPerDay:
          prefs.getInt(_maxTradesPerDay) ??
          BotSettingsModel.defaults.maxTradesPerDay,
      riskScoreCutoff:
          prefs.getDouble(_riskScoreCutoff) ??
          BotSettingsModel.defaults.riskScoreCutoff,
      volatilityThreshold:
          prefs.getDouble(_volatilityThreshold) ??
          BotSettingsModel.defaults.volatilityThreshold,
      stopLossPercent:
          prefs.getDouble(_stopLossPercent) ??
          BotSettingsModel.defaults.stopLossPercent,
      takeProfitPercent:
          prefs.getDouble(_takeProfitPercent) ??
          BotSettingsModel.defaults.takeProfitPercent,
      positionSizeUsd:
          prefs.getDouble(_positionSizeUsd) ??
          BotSettingsModel.defaults.positionSizeUsd,
    );
  }

  Future<void> saveSettings(BotSettingsModel settings) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_displayMode, DisplayMode.simple.storageValue);
    await prefs.setInt(_maxOpenPositions, settings.maxOpenPositions);
    await prefs.setInt(_maxTradesPerDay, settings.maxTradesPerDay);
    await prefs.setDouble(_riskScoreCutoff, settings.riskScoreCutoff);
    await prefs.setDouble(_volatilityThreshold, settings.volatilityThreshold);
    await prefs.setDouble(_stopLossPercent, settings.stopLossPercent);
    await prefs.setDouble(_takeProfitPercent, settings.takeProfitPercent);
    await prefs.setDouble(_positionSizeUsd, settings.positionSizeUsd);
  }
}
