import 'package:flutter/material.dart';

import '../providers/backend_provider.dart';
import '../utils/app_theme.dart';
import 'app_card.dart';
import 'empty_state.dart';

/// Closed-trade stats from `GET /performance` (same scope as Trades history).
class PerformancePanel extends StatelessWidget {
  const PerformancePanel({super.key, required this.backendProvider});

  final BackendProvider backendProvider;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: backendProvider,
      builder: (context, _) {
        final backend = backendProvider;
        final scheme = Theme.of(context).colorScheme;

        if (backend.isPerformanceLoading &&
            backend.backendPerformance == null) {
          return const Padding(
            padding: EdgeInsets.symmetric(vertical: 32),
            child: Center(child: CircularProgressIndicator()),
          );
        }

        if (backend.userVisiblePerformanceError != null &&
            backend.backendPerformance == null) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Column(
              children: [
                Icon(Icons.cloud_off, size: 40, color: scheme.error),
                const SizedBox(height: 8),
                Text(
                  backend.userVisiblePerformanceError!,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: scheme.error,
                    height: 1.35,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: () => backend.refreshBackendPerformance(),
                  child: const Text('נסה שוב'),
                ),
              ],
            ),
          );
        }

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (backend.isPerformanceLoading)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: LinearProgressIndicator(
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            _buildBody(context, backend),
          ],
        );
      },
    );
  }

  Widget _buildBody(BuildContext context, BackendProvider backend) {
    final m = backend.backendPerformance;
    if (m == null) {
      return const EmptyState(
        title: 'אין נתונים',
        subtitle: 'משוך למטה לרענון או פתח את הטאב מחדש.',
      );
    }

    final scheme = Theme.of(context).colorScheme;
    final mode = m['execution_mode']?.toString() ?? '—';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'מצב ביצוע',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: scheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                mode,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 16,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'סיכום',
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 10),
              _metricRow(
                context,
                'סך עסקאות',
                _asInt(m['total_trades']).toString(),
              ),
              _metricRow(
                context,
                'מרוויחות / מפסידות',
                '${_asInt(m['winning_trades'])} / ${_asInt(m['losing_trades'])}',
              ),
              _metricRow(
                context,
                'אחוז הצלחה',
                '${_asDouble(m['win_rate']).toStringAsFixed(1)}%',
              ),
              _metricRow(
                context,
                'רווח/הפסד ממומש',
                _fmtSignedUsd(_asDouble(m['total_realized_profit_loss'])),
              ),
              _metricRow(
                context,
                'רווח ממוצע בעסקאות מרוויחות',
                _fmtNullableUsd(_nullableDouble(m['average_profit'])),
              ),
              _metricRow(
                context,
                'הפסד ממוצע בעסקאות מפסידות',
                _fmtNullableUsd(_nullableDouble(m['average_loss'])),
              ),
              _metricRow(
                context,
                'ממוצע לעסקה',
                _fmtNullableUsd(
                  _nullableDouble(m['average_trade_profit_loss']),
                ),
              ),
              _metricRow(
                context,
                'יחס רווח',
                _fmtNullableRatio(_nullableDouble(m['profit_factor'])),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'הטובה והחלשה ביותר',
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 10),
              _tradeHighlight(context, 'העסקה הטובה ביותר', m['best_trade']),
              const SizedBox(height: 10),
              _tradeHighlight(context, 'העסקה החלשה ביותר', m['worst_trade']),
            ],
          ),
        ),
        const SizedBox(height: 12),
        _symbolsSection(context, m['symbols']),
      ],
    );
  }

  Widget _metricRow(BuildContext context, String label, String value) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 5,
            child: Text(
              label,
              style: TextStyle(fontSize: 13, color: scheme.onSurfaceVariant),
            ),
          ),
          Expanded(
            flex: 4,
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }

  Widget _tradeHighlight(BuildContext context, String title, dynamic raw) {
    final scheme = Theme.of(context).colorScheme;
    if (raw is! Map) {
      return Text(
        '$title: —',
        style: TextStyle(color: scheme.onSurfaceVariant),
      );
    }
    final map = Map<String, dynamic>.from(
      raw.map((k, v) => MapEntry(k.toString(), v)),
    );
    final id = map['id']?.toString() ?? '—';
    final sym = map['symbol']?.toString() ?? '—';
    final pl = _asDouble(map['profit_loss']);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: scheme.primary,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '$sym · $id',
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
        ),
        Text(
          _fmtSignedUsd(pl),
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w800,
            color: pl >= 0 ? AppTheme.positive : AppTheme.negative,
          ),
        ),
      ],
    );
  }

  Widget _symbolsSection(BuildContext context, dynamic raw) {
    final scheme = Theme.of(context).colorScheme;
    if (raw is! List || raw.isEmpty) {
      return AppCard(
        child: Text(
          'סיכום סימבולים: אין עסקאות סגורות עדיין.',
          style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
        ),
      );
    }

    final rows = <Widget>[
      Text(
        'לפי סימבול',
        style: Theme.of(
          context,
        ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
      ),
      const SizedBox(height: 10),
    ];

    final list = raw.whereType<Map>().toList();
    for (var i = 0; i < list.length; i++) {
      final item = list[i];
      final symMap = Map<String, dynamic>.from(
        item.map((k, v) => MapEntry(k.toString(), v)),
      );
      final sym = symMap['symbol']?.toString() ?? '—';
      final n = _asInt(symMap['total_trades']);
      final w = _asInt(symMap['winning_trades']);
      final l = _asInt(symMap['losing_trades']);
      final tpl = _asDouble(symMap['total_realized_profit_loss']);
      final isLast = i == list.length - 1;
      rows.add(
        Padding(
          padding: EdgeInsets.only(bottom: isLast ? 0 : 12),
          child: DecoratedBox(
            decoration: BoxDecoration(
              border: isLast
                  ? null
                  : Border(
                      bottom: BorderSide(
                        color: scheme.outlineVariant.withValues(alpha: 0.5),
                      ),
                    ),
            ),
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    sym,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'עסקאות: $n · רווח/הפסד: $w / $l',
                    style: TextStyle(
                      fontSize: 12,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                  Text(
                    'רווח/הפסד כולל: ${_fmtSignedUsd(tpl)}',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: rows,
      ),
    );
  }

  static int _asInt(dynamic v) {
    if (v == null) return 0;
    if (v is int) return v;
    if (v is num) return v.toInt();
    return int.tryParse(v.toString()) ?? 0;
  }

  static double _asDouble(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }

  static double? _nullableDouble(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString());
  }

  static String _fmtSignedUsd(double v) {
    if (v.isNaN) return '—';
    final sign = v >= 0 ? '+' : '';
    return '$sign${v.toStringAsFixed(4)} USDT';
  }

  static String _fmtNullableUsd(double? v) {
    if (v == null) return '—';
    return _fmtSignedUsd(v);
  }

  static String _fmtNullableRatio(double? v) {
    if (v == null) return '—';
    if (v.isNaN) return '—';
    return v.toStringAsFixed(4);
  }
}
