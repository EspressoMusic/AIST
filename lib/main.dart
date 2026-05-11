import 'package:flutter/material.dart';

import 'providers/backend_provider.dart';
import 'providers/broker_provider.dart';
import 'providers/bot_provider.dart';
import 'providers/theme_provider.dart';
import 'screens/main_shell_screen.dart';
import 'utils/app_theme.dart';

void main() {
  runApp(const TradingBotApp());
}

class TradingBotApp extends StatefulWidget {
  const TradingBotApp({super.key});

  @override
  State<TradingBotApp> createState() => _TradingBotAppState();
}

class _TradingBotAppState extends State<TradingBotApp> {
  final BrokerProvider _brokerProvider = BrokerProvider();
  final BotProvider _botProvider = BotProvider();
  final BackendProvider _backendProvider = BackendProvider();
  final ThemeProvider _themeProvider = ThemeProvider();

  @override
  void initState() {
    super.initState();
    _brokerProvider.init();
    _themeProvider.load();
  }

  @override
  void dispose() {
    _brokerProvider.dispose();
    _botProvider.dispose();
    _backendProvider.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _themeProvider,
      builder: (context, _) {
        return MaterialApp(
          title: 'בוט מסחר',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.lightTheme,
          darkTheme: AppTheme.darkTheme,
          themeMode: _themeProvider.themeMode,
          builder: (context, child) {
            return Directionality(
              textDirection: TextDirection.rtl,
              child: child ?? const SizedBox.shrink(),
            );
          },
          home: MainShellScreen(
            botProvider: _botProvider,
            brokerProvider: _brokerProvider,
            backendProvider: _backendProvider,
            themeProvider: _themeProvider,
          ),
        );
      },
    );
  }
}
