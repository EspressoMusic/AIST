import 'package:flutter/material.dart';

class AppTheme {
  static const Color positive = Color(0xFF22C55E);
  static const Color negative = Color(0xFFEF4444);
  static const Color warning = Color(0xFFF59E0B);
  static const String fontFamily = 'PaperlogyBold';
  static const List<String> fontFallbacks = [
    'Noto Sans Hebrew',
    'Arial',
    'Roboto',
  ];

  static const Color _darkBackground = Color(0xFF0B0F19);
  static const Color _darkSurface = Color(0xFF151A27);
  static const Color _darkSurfaceAlt = Color(0xFF1C2233);

  static TextTheme _fontTextTheme(TextTheme theme) {
    return theme.apply(
      fontFamily: fontFamily,
      fontFamilyFallback: fontFallbacks,
    );
  }

  static ThemeData get darkTheme {
    final colorScheme =
        ColorScheme.fromSeed(
          seedColor: const Color(0xFF2E90FA),
          brightness: Brightness.dark,
        ).copyWith(
          surface: _darkSurface,
          onSurface: Colors.white,
          secondary: const Color(0xFF7C3AED),
        );

    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      fontFamily: fontFamily,
      fontFamilyFallback: fontFallbacks,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: _darkBackground,
      cardTheme: const CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        color: _darkSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(16)),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: _darkSurface,
        indicatorColor: colorScheme.primary.withValues(alpha: 0.28),
        surfaceTintColor: Colors.transparent,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysHide,
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        backgroundColor: _darkBackground,
        foregroundColor: Colors.white,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: _darkSurfaceAlt,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
      ),
    );
    return base.copyWith(
      textTheme: _fontTextTheme(base.textTheme),
      primaryTextTheme: _fontTextTheme(base.primaryTextTheme),
    );
  }

  static ThemeData get lightTheme {
    final colorScheme =
        ColorScheme.fromSeed(
          seedColor: const Color(0xFF2563EB),
          brightness: Brightness.light,
        ).copyWith(
          surface: const Color(0xFFF8FAFC),
          onSurface: const Color(0xFF0F172A),
        );

    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      fontFamily: fontFamily,
      fontFamilyFallback: fontFallbacks,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: const Color(0xFFEEF2F7),
      cardTheme: CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        color: colorScheme.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(
            color: colorScheme.outlineVariant.withValues(alpha: 0.5),
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: colorScheme.surface,
        indicatorColor: colorScheme.primary.withValues(alpha: 0.2),
        surfaceTintColor: Colors.transparent,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysHide,
      ),
      appBarTheme: AppBarTheme(
        centerTitle: false,
        backgroundColor: colorScheme.surface,
        foregroundColor: colorScheme.onSurface,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colorScheme.surfaceContainerHighest,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
      ),
    );
    return base.copyWith(
      textTheme: _fontTextTheme(base.textTheme),
      primaryTextTheme: _fontTextTheme(base.primaryTextTheme),
    );
  }
}
