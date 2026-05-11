import 'package:flutter/material.dart';

import '../models/bot_settings_model.dart';
import '../models/trade_model.dart';
import '../providers/backend_provider.dart';
import '../providers/bot_provider.dart';
import '../utils/app_theme.dart';
import '../widgets/app_card.dart';
import '../widgets/empty_state.dart';
import '../widgets/segmented_tabs.dart';
import '../utils/format_dates.dart';
import '../widgets/status_badge.dart';
import 'trade_details_screen.dart';

class TradesScreen extends StatefulWidget {
  const TradesScreen({
    super.key,
    required this.botProvider,
    required this.backendProvider,
  });

  final BotProvider botProvider;
  final BackendProvider backendProvider;

  @override
  State<TradesScreen> createState() => _TradesScreenState();
}

class _TradesScreenState extends State<TradesScreen> {
  /// Shown only after tapping the bug icon (local simulation fallback).
  bool _debugLocalSource = false;

  /// 0 = local demo, 1 = backend demo — meaningful when [_debugLocalSource].
  int _sourceMode = 1;

  int _tab = 0;

  int get _effectiveSource => _debugLocalSource ? _sourceMode : 1;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.backendProvider.refreshBackendTrades();
    });
  }

  void _onSourceChanged(int value) {
    setState(() => _sourceMode = value);
    if (value == 1) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        widget.backendProvider.refreshBackendTrades();
      });
    }
  }

  Future<void> _confirmForceCloseFromTrades(BuildContext context) async {
    final backend = widget.backendProvider;
    final execMode = backend.backendExecutionModeLabel.trim();
    final title = execMode == 'BINANCE_TESTNET'
        ? 'סגירת פוזיציית טסטנט Binance'
        : 'סגירת עסקת דמו';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: const Text('לסגור עכשיו את הפוזיציה הפתוחה?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('ביטול'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('סגור'),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    final r = await backend.forceCloseBackendPosition();
    if (!context.mounted) return;
    final status = r?['status']?.toString();
    final closedIds = r?['closed_trade_ids'];
    final closedOk =
        status == 'closed' && closedIds is List && closedIds.isNotEmpty;
    if (closedOk) {
      setState(() => _tab = 1);
    }
    final msg = r != null
        ? (status == 'noop'
              ? '${r['message'] ?? 'אין פוזיציה פתוחה'} · פתח "עסקאות" → היסטוריה.'
              : (closedOk
                    ? '${r['message'] ?? 'בוצע'} · היסטוריה עודכנה למטה.'
                    : (r['message']?.toString() ?? 'בוצע')))
        : (backend.userVisibleBotError ?? 'הסגירה נכשלה');
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([widget.botProvider, widget.backendProvider]),
      builder: (context, _) {
        final openTrades = widget.botProvider.openTrades;
        final history = widget.botProvider.tradeHistory;
        final backend = widget.backendProvider;
        final scheme = Theme.of(context).colorScheme;
        final primary = _effectiveSource == 1;
        final simple =
            widget.botProvider.settings.displayMode == DisplayMode.simple;

        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 8, 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: simple
                        ? const SizedBox.shrink()
                        : _debugLocalSource
                        ? SegmentedTabs(
                            labels: const ['דמו מקומי', 'דמו שרת'],
                            selectedIndex: _sourceMode,
                            onChanged: _onSourceChanged,
                          )
                        : const SizedBox.shrink(),
                  ),
                  if (!simple)
                    IconButton(
                      tooltip: 'סימולציה מקומית (דיבאג)',
                      onPressed: () => setState(() {
                        _debugLocalSource = !_debugLocalSource;
                        if (!_debugLocalSource) {
                          _sourceMode = 1;
                          widget.backendProvider.refreshBackendTrades();
                        }
                      }),
                      icon: Icon(
                        Icons.bug_report_outlined,
                        color: _debugLocalSource
                            ? scheme.primary
                            : scheme.outline,
                      ),
                    ),
                ],
              ),
            ),
            if (primary && backend.userVisibleBotError != null)
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 4,
                ),
                child: Text(
                  backend.userVisibleBotError!,
                  style: TextStyle(fontSize: 12, color: scheme.error),
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
              child: SegmentedTabs(
                labels: const ['פתוחות', 'היסטוריה'],
                selectedIndex: _tab,
                onChanged: (value) => setState(() => _tab = value),
              ),
            ),
            Expanded(
              child: _effectiveSource == 0
                  ? (_tab == 0
                        ? _localTradeList(
                            context,
                            openTrades,
                            simple: simple,
                            emptyTitle: 'אין עסקאות פתוחות',
                            emptySubtitle:
                                'הפעל סימולציה מקומית מהדשבורד (דיבאג).',
                          )
                        : _localTradeList(
                            context,
                            history,
                            simple: simple,
                            emptyTitle: 'אין היסטוריה',
                            emptySubtitle: 'עסקאות סגורות יופיעו כאן.',
                          ))
                  : (_tab == 0
                        ? _backendTradeList(
                            context,
                            backend,
                            backend.backendOpenTrades,
                            simple: simple,
                            showForceCloseButton:
                                !simple && primary && _effectiveSource == 1,
                            emptyTitle: 'אין עסקאות פתוחות',
                            emptySubtitle:
                                'הפעל את הבוט בדשבורד — העסקאות יתעדכנו אוטומטית.',
                          )
                        : _backendTradeList(
                            context,
                            backend,
                            backend.backendTradeHistory,
                            simple: simple,
                            showForceCloseButton: false,
                            emptyTitle: 'אין היסטוריה',
                            emptySubtitle: 'עסקאות דמו סגורות יופיעו כאן.',
                          )),
            ),
          ],
        );
      },
    );
  }

  Widget _localTradeList(
    BuildContext context,
    List<TradeModel> trades, {
    bool simple = false,
    required String emptyTitle,
    required String emptySubtitle,
  }) {
    if (trades.isEmpty) {
      return EmptyState(title: emptyTitle, subtitle: emptySubtitle);
    }

    final scheme = Theme.of(context).colorScheme;

    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      itemCount: trades.length,
      separatorBuilder: (_, index) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final trade = trades[index];
        final statusLabel = trade.isOpen ? 'פתוחה' : 'סגורה';
        final plColor = trade.profitLoss >= 0
            ? AppTheme.positive
            : AppTheme.negative;

        return Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: simple
                ? null
                : () {
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => TradeDetailsScreen(
                          tradeId: trade.id,
                          botProvider: widget.botProvider,
                        ),
                      ),
                    );
                  },
            child: AppCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              trade.symbol,
                              style: const TextStyle(
                                fontWeight: FontWeight.w800,
                                fontSize: 16,
                              ),
                            ),
                            const SizedBox(width: 8),
                            StatusBadge(
                              label: _heSide(trade.side),
                              type: trade.side.toLowerCase() == 'buy'
                                  ? StatusBadgeType.positive
                                  : StatusBadgeType.negative,
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        if (!simple)
                          Text(
                            'נפתחה ${formatShortDateTime(trade.openedAt)} · $statusLabel',
                            style: TextStyle(
                              fontSize: 12,
                              color: scheme.onSurfaceVariant,
                            ),
                          )
                        else
                          Text(
                            statusLabel,
                            style: TextStyle(
                              fontSize: 12,
                              color: scheme.onSurfaceVariant,
                            ),
                          ),
                      ],
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        '${trade.profitLoss >= 0 ? '+' : ''}'
                        '${trade.profitLoss.toStringAsFixed(2)}',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          color: plColor,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'רווח/הפסד',
                        style: TextStyle(
                          fontSize: 11,
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                  if (!simple) const Icon(Icons.chevron_right),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _backendTradeList(
    BuildContext context,
    BackendProvider backend,
    List<dynamic> rows, {
    bool simple = false,
    required bool showForceCloseButton,
    required String emptyTitle,
    required String emptySubtitle,
  }) {
    if (rows.isEmpty) {
      return EmptyState(title: emptyTitle, subtitle: emptySubtitle);
    }

    final scheme = Theme.of(context).colorScheme;

    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      itemCount: rows.length,
      separatorBuilder: (_, index) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final raw = rows[index];
        if (raw is! Map) {
          return const SizedBox.shrink();
        }
        final m = Map<String, dynamic>.from(
          raw.map((k, v) => MapEntry(k.toString(), v)),
        );
        final symbol = m['symbol']?.toString() ?? '—';
        final side = (m['side']?.toString() ?? '—').toUpperCase();
        final sideHe = _heSide(side);
        final entryPx = _asDouble(m['entry_price']);
        final qty = _asDouble(m['quantity']);
        final pl = _asDouble(m['profit_loss']);
        final status = m['status']?.toString() ?? '—';
        final openedAt = _parseDate(m['opened_at']);
        final reason = m['reason']?.toString() ?? '';
        final tradeSource = (m['source']?.toString() ?? '')
            .trim()
            .toUpperCase();
        final plColor = pl >= 0 ? AppTheme.positive : AppTheme.negative;
        final statusUpper = status.toUpperCase();
        final statusBadge = statusUpper == 'OPEN'
            ? StatusBadgeType.positive
            : StatusBadgeType.neutral;
        final exitRaw = m['exit_price'];
        final exitPx = exitRaw != null
            ? _asDouble(exitRaw)
            : (statusUpper == 'CLOSED' ? _asDouble(m['current_price']) : 0.0);

        return AppCard(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      symbol,
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
                  ),
                  StatusBadge(
                    label: sideHe,
                    type: side == 'BUY'
                        ? StatusBadgeType.positive
                        : StatusBadgeType.negative,
                  ),
                  const SizedBox(width: 8),
                  StatusBadge(label: statusUpper, type: statusBadge),
                ],
              ),
              if (!simple && tradeSource == 'BINANCE_TESTNET') ...[
                const SizedBox(height: 6),
                Text(
                  'טסטנט Binance',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: scheme.primary,
                  ),
                ),
              ],
              if (!simple && statusUpper == 'CLOSED') ...[
                const SizedBox(height: 6),
                Text(
                  'כניסה ${_fmtPx(entryPx)} · יציאה ${_fmtPx(exitPx)} · '
                  'כמות ${_fmtQty(qty)}',
                  style: TextStyle(
                    fontSize: 12,
                    height: 1.3,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              ],
              const SizedBox(height: 8),
              Row(
                children: [
                  Text(
                    statusUpper == 'CLOSED' ? 'רווח/הפסד סופי ' : 'רווח/הפסד ',
                    style: TextStyle(
                      fontSize: 13,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                  Text(
                    '${pl >= 0 ? '+' : ''}${pl.toStringAsFixed(4)}',
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      color: plColor,
                      fontSize: 15,
                    ),
                  ),
                  const Spacer(),
                  if (!simple && openedAt != null)
                    Text(
                      formatShortDateTime(openedAt),
                      style: TextStyle(
                        fontSize: 12,
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                ],
              ),
              if (!simple && reason.isNotEmpty)
                Theme(
                  data: Theme.of(
                    context,
                  ).copyWith(dividerColor: Colors.transparent),
                  child: ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    dense: true,
                    title: Text(
                      'פרטים',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: scheme.primary,
                      ),
                    ),
                    children: [
                      Text(
                        reason,
                        style: TextStyle(
                          fontSize: 12,
                          height: 1.35,
                          color: scheme.onSurface.withValues(alpha: 0.88),
                        ),
                      ),
                    ],
                  ),
                ),
              if (showForceCloseButton && statusUpper == 'OPEN')
                Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      onPressed: backend.isBackendBotLoading
                          ? null
                          : () => _confirmForceCloseFromTrades(context),
                      icon: Icon(
                        Icons.emergency_outlined,
                        color: scheme.error,
                        size: 18,
                      ),
                      label: Text(
                        backend.backendExecutionModeLabel.trim() ==
                                'BINANCE_TESTNET'
                            ? 'סגור פוזיציית טסטנט Binance'
                            : 'סגור עסקת דמו',
                        style: TextStyle(
                          color: scheme.error,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }

  String _fmtPx(double v) {
    if (v.isNaN) return '—';
    if (v == 0) return '0';
    final a = v.abs();
    final decimals = a >= 1000 ? 2 : (a >= 1 ? 4 : 8);
    var s = v.toStringAsFixed(decimals);
    while (s.contains('.') && (s.endsWith('0') || s.endsWith('.'))) {
      if (s.endsWith('.')) {
        return s.substring(0, s.length - 1);
      }
      s = s.substring(0, s.length - 1);
    }
    return s;
  }

  String _fmtQty(double v) {
    if (v.isNaN || v == 0) return '—';
    final a = v.abs();
    final decimals = a >= 1 ? 6 : 8;
    var s = v.toStringAsFixed(decimals);
    while (s.contains('.') && (s.endsWith('0') || s.endsWith('.'))) {
      if (s.endsWith('.')) {
        return s.substring(0, s.length - 1);
      }
      s = s.substring(0, s.length - 1);
    }
    return s;
  }

  double _asDouble(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }

  DateTime? _parseDate(dynamic v) {
    if (v == null) return null;
    if (v is String) return DateTime.tryParse(v);
    return null;
  }

  String _heSide(String side) {
    final s = side.toUpperCase();
    if (s == 'BUY' || s == 'BUY/SELL') {
      return s == 'BUY' ? 'קנייה' : 'קנייה/מכירה';
    }
    if (s == 'SELL') return 'מכירה';
    return side;
  }
}
