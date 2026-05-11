import 'package:flutter/material.dart';

import '../models/bot_settings_model.dart';
import '../providers/backend_provider.dart';
import '../providers/bot_provider.dart';
import '../providers/broker_provider.dart';
import '../utils/app_theme.dart';
import '../widgets/app_card.dart';
import '../widgets/pl_gauge.dart';
import 'preflight_check_screen.dart';

String? _executionModeDropdownValue(BackendProvider backend) {
  final em = backend.backendExecutionModeLabel.trim();
  if (em == 'PAPER_DEMO' || em == 'BINANCE_TESTNET') return em;
  return 'BINANCE_TESTNET';
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({
    super.key,
    required this.botProvider,
    required this.brokerProvider,
    required this.backendProvider,
  });

  final BotProvider botProvider;
  final BrokerProvider brokerProvider;
  final BackendProvider backendProvider;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.backendProvider.refreshPortfolio();
      widget.backendProvider.refreshMarketPrices();
      widget.backendProvider.refreshAfterBotAction();
    });
  }

  Future<void> _confirmForceClosePosition(BuildContext context) async {
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
    final msg = r != null
        ? (status == 'noop'
              ? '${r['message'] ?? 'אין פוזיציה פתוחה'} · פתח עסקאות → היסטוריה לבדיקה.'
              : (closedOk
                    ? '${r['message'] ?? 'בוצע'} · בדוק בעסקאות → היסטוריה.'
                    : (r['message']?.toString() ?? 'בוצע')))
        : (backend.userVisibleBotError ?? 'הסגירה נכשלה');
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Future<void> _runManualTick(BuildContext context) async {
    final backend = widget.backendProvider;
    try {
      final r = await backend.tickBackendBot();
      await backend.refreshAfterBotAction();
      backend.recordBackendSyncComplete();
      if (!context.mounted) return;
      if (r['status'] == 'stopped') {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              r['message']?.toString() ??
                  'צריך להפעיל את הבוט לפני הרצה ידנית.',
            ),
          ),
        );
      }
    } catch (_) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(backend.userVisibleBotError ?? 'הרצה ידנית נכשלה'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([
        widget.botProvider,
        widget.brokerProvider,
        widget.backendProvider,
      ]),
      builder: (context, _) {
        final backend = widget.backendProvider;
        final startBal = backend.portfolioNumber('starting_balance', 10000);
        final currentVal = backend.portfolioNumber('current_value');
        final totalPl = backend.portfolioNumber('total_profit_loss');
        final changePct = backend.portfolioNumber('change_percent');
        final realized = backend.portfolioNumber('realized_profit_loss');
        final unrealized = backend.portfolioNumber('unrealized_profit_loss');
        final openC = backend.portfolioInt('open_trades_count');
        final closedC = backend.portfolioInt('closed_trades_count');
        final gaugeBase = startBal <= 0 ? 10000.0 : startBal;

        final valueAccent = _portfolioAccent(context, totalPl, changePct);
        final scheme = Theme.of(context).colorScheme;
        final hasPortfolio = backend.backendPortfolio != null;
        final started = _backendStarted(backend);
        final execMode = backend.backendExecutionModeLabel.trim();
        final statusHasOpen =
            backend.backendBotStatusDetails?['has_open_position'];
        final hasOpenPosition =
            (statusHasOpen is bool && statusHasOpen) || openC > 0;
        final simple =
            widget.botProvider.settings.displayMode == DisplayMode.simple;

        if (simple) {
          return _simpleDashboard(
            context,
            backend,
            totalPl,
            gaugeBase,
            hasOpenPosition,
            scheme,
          );
        }

        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          children: [
            Center(
              child: PlGauge(profitLoss: totalPl, balanceBase: gaugeBase),
            ),
            const SizedBox(height: 16),
            AppCard(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (hasPortfolio)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Text(
                        'עסקאות פתוחות: $openC · סגורות: $closedC',
                        style: TextStyle(
                          fontSize: 11,
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  const SizedBox(height: 10),
                  if (backend.userVisiblePortfolioError != null &&
                      !hasPortfolio)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Text(
                        backend.userVisiblePortfolioError!,
                        style: TextStyle(fontSize: 12, color: scheme.error),
                      ),
                    )
                  else if (backend.isBackendLoading && !hasPortfolio)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(
                        'טוען תיק…',
                        style: TextStyle(
                          fontSize: 12,
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  _portfolioRow(
                    context,
                    'יתרת פתיחה',
                    _fmtUsd(hasPortfolio ? startBal : 10000),
                    Theme.of(context).colorScheme.onSurface,
                  ),
                  _portfolioRow(
                    context,
                    'שווי תיק נוכחי',
                    _fmtUsd(hasPortfolio ? currentVal : 10000),
                    valueAccent,
                  ),
                  _portfolioRow(
                    context,
                    'רווח/הפסד מעסקאות סגורות',
                    _fmtUsdSigned(hasPortfolio ? realized : 0),
                    _portfolioAccent(context, realized, 0),
                  ),
                  _portfolioRow(
                    context,
                    'רווח/הפסד פתוח',
                    _fmtUsdSigned(hasPortfolio ? unrealized : 0),
                    _portfolioAccent(context, unrealized, 0),
                  ),
                  _portfolioRow(
                    context,
                    'רווח / הפסד כולל',
                    _fmtUsdSigned(hasPortfolio ? totalPl : 0),
                    valueAccent,
                  ),
                  _portfolioRow(
                    context,
                    'שינוי בתיק',
                    _fmtPctSigned(hasPortfolio ? changePct : 0),
                    valueAccent,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            AppCard(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (backend.isMarketPricesLoading)
                    Align(
                      alignment: Alignment.centerRight,
                      child: SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: scheme.primary,
                        ),
                      ),
                    ),
                  if (backend.backendMarketPrices != null) ...[
                    _liveRow(
                      scheme,
                      'BTCUSDT',
                      backend.backendMarketPrices!.btcUsdt.toStringAsFixed(2),
                    ),
                    _liveRow(
                      scheme,
                      'ETHUSDT',
                      backend.backendMarketPrices!.ethUsdt.toStringAsFixed(2),
                    ),
                    _liveRow(
                      scheme,
                      'מקור',
                      backend.backendMarketPrices!.sourceDisplayLabel,
                    ),
                  ] else ...[
                    Text(
                      'עדיין אין מחירים.',
                      style: TextStyle(
                        fontSize: 13,
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                  if (backend.lastMarketPriceUpdatedAt != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        'עודכן לאחרונה ${_fmtClock(backend.lastMarketPriceUpdatedAt!)}',
                        style: TextStyle(
                          fontSize: 11,
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  if (backend.userVisibleMarketError != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        backend.userVisibleMarketError!,
                        style: TextStyle(fontSize: 11, color: scheme.error),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            AppCard(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (backend.userVisibleBotError != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Text(
                        backend.userVisibleBotError!,
                        style: TextStyle(
                          fontSize: 12,
                          height: 1.35,
                          color: scheme.error,
                        ),
                      ),
                    ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (backend.isBackendBotLoading)
                        Padding(
                          padding: const EdgeInsets.only(right: 10),
                          child: SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: scheme.primary,
                            ),
                          ),
                        ),
                      Icon(
                        started ? Icons.play_circle_fill : Icons.pause_circle,
                        color: started ? scheme.primary : scheme.outline,
                        size: 22,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        started ? 'הבוט פעיל' : 'הבוט כבוי',
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 18,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  _backendBotRow(
                    scheme,
                    'עדכון אוטומטי',
                    started && backend.backendAutoRunActive
                        ? 'כן · כל ${BackendProvider.backendAutoRunInterval.inSeconds} שניות'
                        : 'לא',
                  ),
                  _backendBotRow(
                    scheme,
                    'עודכן לאחרונה',
                    backend.lastBackendSyncAt != null
                        ? _fmtClock(backend.lastBackendSyncAt!)
                        : '—',
                  ),
                  const SizedBox(height: 6),
                  _backendBotRow(
                    scheme,
                    'מצב ביצוע',
                    backend.backendExecutionModeLabel,
                  ),
                  _backendBotRow(
                    scheme,
                    'סטטוס שרת',
                    backend.backendBotStatusDetails?['status']?.toString() ??
                        backend.backendBotStatusLabel,
                  ),
                  _backendBotRow(
                    scheme,
                    'עסקאות פתוחות',
                    '${backend.backendBotStatusDetails?['open_trades_count'] ?? '—'}',
                  ),
                  _backendBotRow(
                    scheme,
                    'החלטות בהיסטוריה',
                    '${backend.backendBotStatusDetails?['decisions_count'] ?? '—'}',
                  ),
                  Builder(
                    builder: (context) {
                      final skip = backend
                          .backendBotStatusDetails?['last_open_skipped_reason']
                          ?.toString()
                          .trim();
                      if (!started || skip == null || skip.isEmpty) {
                        return const SizedBox.shrink();
                      }
                      return Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            'דילוג אחרון (למה לא נפתחה עסקה): $skip',
                            style: TextStyle(
                              fontSize: 11,
                              height: 1.35,
                              color: scheme.onSurfaceVariant,
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'הפעלת הבוט מחברת לשרת, מפעילה הרצות אוטומטיות ומרעננת תיק ומחירים. כיבוי עוצר מיד.',
                    style: TextStyle(
                      fontSize: 10,
                      height: 1.35,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: backend.isBackendBotLoading || started
                        ? null
                        : () async {
                            final ok = await backend.startBackendBot();
                            if (!context.mounted) return;
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  ok
                                      ? 'הבוט הופעל · עדכון אוטומטי'
                                      : backend.userVisibleBotError ??
                                            'הפעלה נכשלה',
                                ),
                              ),
                            );
                          },
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('הפעל בוט'),
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                      textStyle: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 15,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    style: FilledButton.styleFrom(
                      backgroundColor: scheme.errorContainer,
                      foregroundColor: scheme.onErrorContainer,
                      minimumSize: const Size.fromHeight(48),
                      textStyle: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 15,
                      ),
                    ),
                    onPressed: !backend.isBackendBotLoading && started
                        ? () async {
                            final ok = await backend.stopBackendBot();
                            if (!context.mounted) return;
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  ok
                                      ? 'הבוט כובה'
                                      : backend.userVisibleBotError ??
                                            'כיבוי נכשל',
                                ),
                              ),
                            );
                          }
                        : null,
                    icon: const Icon(Icons.stop_circle_outlined),
                    label: const Text('כבה בוט'),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: scheme.error,
                      side: BorderSide(color: scheme.error),
                      minimumSize: const Size.fromHeight(48),
                      textStyle: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 15,
                      ),
                    ),
                    onPressed: !backend.isBackendBotLoading && hasOpenPosition
                        ? () => _confirmForceClosePosition(context)
                        : null,
                    icon: const Icon(Icons.emergency_outlined),
                    label: Text(
                      execMode == 'BINANCE_TESTNET'
                          ? 'סגור פוזיציית טסטנט Binance'
                          : 'סגור עסקת דמו',
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Theme(
              data: Theme.of(
                context,
              ).copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                initiallyExpanded: false,
                title: Text(
                  'פיתוח / דיבאג',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
                subtitle: Text(
                  'רענון ידני וסימולציה מקומית · מוסתר מהמסך הראשי',
                  style: TextStyle(
                    fontSize: 11,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
                childrenPadding: const EdgeInsets.only(bottom: 4),
                children: [
                  Text(
                    'הבוט בשרת מתעדכן בדרך כלל כל '
                    '${BackendProvider.backendAutoRunInterval.inSeconds} שניות אחרי הפעלה.',
                    style: TextStyle(
                      fontSize: 12,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: backend.isBackendLoading
                          ? null
                          : () => backend.refreshPortfolio(),
                      icon: const Icon(Icons.refresh, size: 18),
                      label: const Text('רענן תיק'),
                    ),
                  ),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: backend.isMarketPricesLoading
                          ? null
                          : () => backend.refreshMarketPrices(),
                      icon: const Icon(Icons.refresh, size: 18),
                      label: const Text('רענן מחירים'),
                    ),
                  ),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: backend.isBackendBotLoading || !started
                          ? null
                          : () => _runManualTick(context),
                      icon: const Icon(Icons.skip_next, size: 18),
                      label: const Text('הרצה ידנית'),
                    ),
                  ),
                  const Divider(height: 20),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: scheme.errorContainer.withValues(alpha: 0.35),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Binance Testnet בלבד — בלי כסף אמיתי',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 12,
                            color: scheme.error,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'השרת חייב להגדיר USE_BINANCE_TESTNET ומפתחות טסטנט בקובץ backend/.env. '
                          'לא שמים מפתחות באפליקציה.',
                          style: TextStyle(
                            fontSize: 11,
                            height: 1.35,
                            color: scheme.onSurfaceVariant,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'מצב ביצוע',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: scheme.onSurfaceVariant,
                          ),
                        ),
                        const SizedBox(height: 4),
                        DropdownButton<String>(
                          isExpanded: true,
                          value: _executionModeDropdownValue(backend),
                          items: const [
                            DropdownMenuItem(
                              value: 'PAPER_DEMO',
                              child: Text('דמו נייר'),
                            ),
                            DropdownMenuItem(
                              value: 'BINANCE_TESTNET',
                              child: Text('טסטנט Binance (ברירת מחדל)'),
                            ),
                          ],
                          onChanged: backend.isBackendBotLoading
                              ? null
                              : (v) async {
                                  if (v == null) return;
                                  final ok = await backend
                                      .setBackendExecutionMode(v);
                                  if (!context.mounted) return;
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        ok
                                            ? 'מצב ביצוע: $v'
                                            : backend.userVisibleBotError ??
                                                  'נכשל',
                                      ),
                                    ),
                                  );
                                },
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Divider(height: 20),
                  Text(
                    'סימולציה מקומית בלבד (לא מפעילה את FastAPI)',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: () {
                        Navigator.of(context).push<void>(
                          MaterialPageRoute<void>(
                            builder: (_) => PreflightCheckScreen(
                              brokerProvider: widget.brokerProvider,
                              botProvider: widget.botProvider,
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.science_outlined, size: 18),
                      label: const Text('פתח סימולציה מקומית'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _backendBotRow(ColorScheme scheme, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
            ),
          ),
          Text(
            value,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }

  Widget _simpleDashboard(
    BuildContext context,
    BackendProvider backend,
    double totalPl,
    double gaugeBase,
    bool hasOpenPosition,
    ColorScheme scheme,
  ) {
    final open = _firstOpenTradeMap(backend);
    final symbol =
        open?['symbol']?.toString() ??
        backend.backendBotStatusDetails?['open_position_symbol']?.toString() ??
        '—';
    final side = _heSide(
      (open?['side']?.toString() ?? 'BUY/SELL').toUpperCase(),
    );
    final plRaw =
        open?['profit_loss'] ??
        backend.backendBotStatusDetails?['open_position_pnl'];
    final currentPl = _asDouble(plRaw);
    final plColor = _portfolioAccent(context, totalPl, 0);

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
      children: [
        Center(
          child: PlGauge(profitLoss: totalPl, balanceBase: gaugeBase),
        ),
        const SizedBox(height: 18),
        AppCard(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'רווח / הפסד כולל',
                style: TextStyle(fontSize: 13, color: scheme.onSurfaceVariant),
              ),
              const SizedBox(height: 6),
              Text(
                _fmtUsdSigned(totalPl),
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w900,
                  color: plColor,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        AppCard(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'פוזיציה',
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              Text(
                hasOpenPosition
                    ? 'עסקה פתוחה: $symbol, $side, ${_fmtUsdSigned(currentPl)}'
                    : 'אין עסקה פתוחה',
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Map<String, dynamic>? _firstOpenTradeMap(BackendProvider backend) {
    for (final raw in backend.backendOpenTrades) {
      if (raw is Map) {
        return Map<String, dynamic>.from(
          raw.map((k, v) => MapEntry(k.toString(), v)),
        );
      }
    }
    return null;
  }

  double _asDouble(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }

  Widget _liveRow(ColorScheme scheme, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(fontSize: 13, color: scheme.onSurfaceVariant),
            ),
          ),
          Text(
            value,
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }

  String _fmtClock(DateTime dt) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(dt.hour)}:${two(dt.minute)}:${two(dt.second)}';
  }

  Color _portfolioAccent(
    BuildContext context,
    double totalProfitLoss,
    double portfolioChangePercent,
  ) {
    const neutralBandUsd = 12.0;
    const neutralBandPct = 0.15;
    if (totalProfitLoss.abs() < neutralBandUsd &&
        portfolioChangePercent.abs() < neutralBandPct) {
      return Theme.of(context).colorScheme.onSurfaceVariant;
    }
    if (totalProfitLoss > 0) return AppTheme.positive;
    if (totalProfitLoss < 0) return AppTheme.negative;
    return Theme.of(context).colorScheme.onSurfaceVariant;
  }

  Widget _portfolioRow(
    BuildContext context,
    String label,
    String value,
    Color valueColor,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 13,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: valueColor,
            ),
          ),
        ],
      ),
    );
  }

  String _fmtUsd(double v) => '\$${v.toStringAsFixed(2)}';

  String _fmtUsdSigned(double v) {
    final sign = v >= 0 ? '+' : '-';
    return '$sign\$${v.abs().toStringAsFixed(2)}';
  }

  String _fmtPctSigned(double pct) {
    final sign = pct >= 0 ? '+' : '';
    return '$sign${pct.toStringAsFixed(2)}%';
  }

  String _heSide(String side) {
    final s = side.toUpperCase();
    if (s == 'BUY' || s == 'BUY/SELL') {
      return s == 'BUY' ? 'קנייה' : 'קנייה/מכירה';
    }
    if (s == 'SELL') return 'מכירה';
    return side;
  }

  bool _backendStarted(BackendProvider backend) {
    return backend.backendBotStatusDetails?['status'] == 'started';
  }
}
