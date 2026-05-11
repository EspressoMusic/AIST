import 'dart:async';

import 'package:flutter/material.dart';

import '../providers/backend_provider.dart';
import '../providers/broker_provider.dart';
import '../providers/bot_provider.dart';
import '../providers/theme_provider.dart';
import '../widgets/app_bottom_nav.dart';
import 'agents_screen.dart';
import 'dashboard_screen.dart';
import 'settings_screen.dart';
import 'trades_screen.dart';

class MainShellScreen extends StatefulWidget {
  const MainShellScreen({
    super.key,
    required this.botProvider,
    required this.brokerProvider,
    required this.backendProvider,
    required this.themeProvider,
  });

  final BotProvider botProvider;
  final BrokerProvider brokerProvider;
  final BackendProvider backendProvider;
  final ThemeProvider themeProvider;

  @override
  State<MainShellScreen> createState() => _MainShellScreenState();
}

class _MainShellScreenState extends State<MainShellScreen>
    with WidgetsBindingObserver {
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final backend = widget.backendProvider;
    switch (state) {
      case AppLifecycleState.paused:
      case AppLifecycleState.detached:
        backend.onAppLifecyclePaused();
        break;
      case AppLifecycleState.resumed:
        unawaited(backend.onAppLifecycleResumed());
        break;
      case AppLifecycleState.inactive:
      case AppLifecycleState.hidden:
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      DashboardScreen(
        botProvider: widget.botProvider,
        brokerProvider: widget.brokerProvider,
        backendProvider: widget.backendProvider,
      ),
      TradesScreen(
        botProvider: widget.botProvider,
        backendProvider: widget.backendProvider,
      ),
      AgentsScreen(
        botProvider: widget.botProvider,
        backendProvider: widget.backendProvider,
      ),
      SettingsScreen(
        botProvider: widget.botProvider,
        themeProvider: widget.themeProvider,
        backendProvider: widget.backendProvider,
      ),
    ];

    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: IndexedStack(index: _currentIndex, children: screens),
      ),
      bottomNavigationBar: AppBottomNav(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() => _currentIndex = index);
          widget.backendProvider.refreshForShellTab(index);
        },
      ),
    );
  }
}
