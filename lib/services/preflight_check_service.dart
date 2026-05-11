import '../models/preflight_check_model.dart';
import '../providers/bot_provider.dart';
import '../providers/broker_provider.dart';

class PreflightCheckService {
  List<PreflightCheckModel> runChecks({
    required BrokerProvider brokerProvider,
    required BotProvider botProvider,
  }) {
    final settings = botProvider.settings;

    final strategyValid =
        settings.maxOpenPositions > 0 &&
        settings.maxTradesPerDay > 0 &&
        settings.riskScoreCutoff >= 1 &&
        settings.riskScoreCutoff <= 10 &&
        settings.positionSizeUsd > 0;

    return [
      PreflightCheckModel(
        title: 'Paper demo broker ready',
        passed:
            brokerProvider.isConnected && brokerProvider.isPaperOrDemo,
        message: brokerProvider.isConnected && brokerProvider.isPaperOrDemo
            ? 'Using local demo / paper connection.'
            : 'Demo broker profile not ready.',
      ),
      PreflightCheckModel(
        title: 'Market simulation stream',
        passed: botProvider.marketConnected,
        message: botProvider.marketConnected
            ? 'Simulated tape is connected.'
            : 'Waiting for the simulator (retry in a moment).',
      ),
      PreflightCheckModel(
        title: 'Internal safeguards',
        passed: strategyValid,
        message: strategyValid
            ? 'Default engine limits loaded.'
            : 'Engine defaults invalid — reset app data if this persists.',
      ),
    ];
  }
}
