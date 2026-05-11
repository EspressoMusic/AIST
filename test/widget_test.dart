// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';

import 'package:trading_bot_dashboard/main.dart';

void main() {
  testWidgets('App starts with auth flow', (WidgetTester tester) async {
    await tester.pumpWidget(const TradingBotApp());
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    final hasLogin = find.text('Welcome Back').evaluate().isNotEmpty;
    final hasDashboard = find.text('Dashboard').evaluate().isNotEmpty;
    final hasSplash = find
        .text('Initializing Trading Terminal...')
        .evaluate()
        .isNotEmpty;
    expect(hasSplash || hasLogin || hasDashboard, isTrue);
  });
}
