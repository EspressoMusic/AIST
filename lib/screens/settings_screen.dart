import 'dart:io';

import 'package:flutter/material.dart';

import '../providers/backend_provider.dart';
import '../providers/bot_provider.dart';
import '../providers/theme_provider.dart';
import '../widgets/segmented_tabs.dart';

enum _ReportPeriod { daily, weekly, monthly }

enum _ReadinessState { ok, warning, blocked }

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({
    super.key,
    required this.botProvider,
    required this.themeProvider,
    required this.backendProvider,
  });

  final BotProvider botProvider;
  final ThemeProvider themeProvider;
  final BackendProvider backendProvider;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  _ReportPeriod _period = _ReportPeriod.daily;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.backendProvider.refreshDemoStatus(showLoading: false);
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([
        widget.botProvider,
        widget.themeProvider,
        widget.backendProvider,
      ]),
      builder: (context, _) {
        return RefreshIndicator(
          onRefresh: () async {
            await widget.backendProvider.refreshBackendTrades();
            await widget.backendProvider.refreshBackendPerformance();
            await widget.backendProvider.refreshBackendBotStatus();
            await widget.backendProvider.refreshDemoStatus();
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
            children: [
              _themeModeCard(context),
              const SizedBox(height: 16),
              _executionModeCard(context),
              const SizedBox(height: 16),
              _demoStatusCard(context),
              const SizedBox(height: 16),
              _botStatusCard(context),
              const SizedBox(height: 16),
              _reportCard(context),
            ],
          ),
        );
      },
    );
  }

  Widget _demoStatusCard(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final backend = widget.backendProvider;
    final health = backend.systemHealth ?? const <String, dynamic>{};
    final demo = backend.demoWeekStatus ?? const <String, dynamic>{};
    final chief = backend.chiefBotStatus ?? const <String, dynamic>{};
    final aiTeam = backend.aiTeamStatus ?? const <String, dynamic>{};
    final lastChief = _mapOf(chief['last_chief_decision']);
    final hasData =
        backend.systemHealth != null ||
        backend.demoWeekStatus != null ||
        backend.chiefBotStatus != null ||
        backend.aiTeamStatus != null ||
        backend.backendPortfolio != null ||
        backend.backendPerformance != null;
    final checklist = _readinessChecklist(
      health: health,
      aiTeam: aiTeam,
      demo: demo,
      chief: chief,
      portfolio: backend.backendPortfolio,
      performance: backend.backendPerformance,
    );
    final criticalBlocked = checklist.any(
      (item) => item.critical && item.state == _ReadinessState.blocked,
    );
    final lastUpdated = backend.lastDemoStatusUpdatedAt;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(Icons.health_and_safety_outlined, color: scheme.primary),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'סטטוס דמו ובדיקת מוכנות',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
                  ),
                ),
                if (backend.isDemoStatusLoading)
                  const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                else
                  Text(
                    'Read-only',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
              ],
            ),
            if (lastUpdated != null) ...[
              const SizedBox(height: 4),
              Text(
                'Last updated: ${_formatTime(lastUpdated)}',
                style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
              ),
            ],
            if (backend.userVisibleDemoStatusError != null) ...[
              const SizedBox(height: 8),
              Text(
                backend.userVisibleDemoStatusError!,
                style: TextStyle(color: scheme.error, fontSize: 12),
              ),
            ] else if (!hasData && backend.isDemoStatusLoading) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(),
            ] else if (!hasData) ...[
              const SizedBox(height: 8),
              Text(
                'אין סטטוס דמו עדיין. לחץ רענון או משוך לרענון.',
                style: TextStyle(color: scheme.onSurfaceVariant),
              ),
            ] else ...[
              const SizedBox(height: 8),
              _readinessBanner(context, criticalBlocked),
              const SizedBox(height: 10),
              for (final item in checklist) _checklistRow(context, item),
              const Divider(height: 20),
              _statusRow(
                context,
                'System Health',
                health['backend_ok'] == true ? 'תקין' : 'לא זמין',
                positive: health['backend_ok'] == true,
              ),
              _statusRow(
                context,
                'Execution Mode',
                _friendlyExecutionMode(
                  health['execution_mode'] ?? chief['execution_mode'],
                ),
              ),
              _statusRow(
                context,
                'Demo Week Mode',
                demo['enabled'] == true ? 'פעיל' : 'כבוי',
                positive: demo['enabled'] != true,
              ),
              _statusRow(
                context,
                'Chief AI Autonomy',
                chief['enabled'] == true ? 'פעיל' : 'כבוי',
                positive: chief['enabled'] != true,
              ),
              _statusRow(
                context,
                'Kill Switch',
                health['kill_switch_active'] == true ? 'פעיל' : 'כבוי',
                positive: health['kill_switch_active'] != true,
              ),
              _statusRow(
                context,
                'AI Provider',
                _friendlyStatus(health['ai_provider']),
              ),
              _statusRow(
                context,
                'Agents Ready',
                health['agents_ready'] == true ? 'כן' : 'לא',
                positive: health['agents_ready'] == true,
              ),
              _statusRow(
                context,
                'Chief Manager Ready',
                health['chief_manager_ready'] == true ? 'כן' : 'לא',
                positive: health['chief_manager_ready'] == true,
              ),
              if (lastChief.isNotEmpty) ...[
                const Divider(height: 18),
                Text(
                  'החלטת Chief אחרונה',
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    color: scheme.onSurface,
                  ),
                ),
                const SizedBox(height: 6),
                _statusRow(
                  context,
                  'פעולה',
                  _friendlyAction(lastChief['final_action']),
                ),
                _statusRow(
                  context,
                  'סימבול',
                  lastChief['selected_symbol']?.toString() ?? '—',
                ),
                _statusRow(
                  context,
                  'ביטחון',
                  lastChief['final_confidence']?.toString() ?? '—',
                ),
                Text(
                  lastChief['short_reason']?.toString() ?? '',
                  style: TextStyle(
                    fontSize: 12,
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  Widget _readinessBanner(BuildContext context, bool blocked) {
    final scheme = Theme.of(context).colorScheme;
    final color = blocked ? scheme.error : Colors.green;
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        blocked
            ? 'Demo is not ready yet — check the blocked items.'
            : 'Demo system is ready for manual testing.',
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w900,
          fontSize: 13,
        ),
      ),
    );
  }

  Widget _checklistRow(BuildContext context, _ReadinessItem item) {
    final scheme = Theme.of(context).colorScheme;
    final color = _readinessColor(context, item.state);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(_readinessIcon(item.state), size: 18, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              item.label,
              style: TextStyle(fontSize: 13, color: scheme.onSurface),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.13),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              _readinessLabel(item.state),
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _themeModeCard(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: SegmentedTabs(
          labels: const ['בהיר', 'חשוך'],
          selectedIndex: widget.themeProvider.isDarkMode ? 1 : 0,
          onChanged: (index) => widget.themeProvider.setDarkMode(index == 1),
        ),
      ),
    );
  }

  Widget _executionModeCard(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            DropdownButton<String>(
              isExpanded: true,
              value: _executionModeDropdownValue(widget.backendProvider),
              items: const [
                DropdownMenuItem(value: 'PAPER_DEMO', child: Text('דמו נייר')),
                DropdownMenuItem(
                  value: 'BINANCE_TESTNET',
                  child: Text('טסטנט Binance'),
                ),
              ],
              onChanged: widget.backendProvider.isBackendBotLoading
                  ? null
                  : (v) async {
                      if (v == null) return;
                      final ok = await widget.backendProvider
                          .setBackendExecutionMode(v);
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            ok
                                ? 'מצב ביצוע: $v'
                                : widget.backendProvider.userVisibleBotError ??
                                      'נכשל',
                          ),
                        ),
                      );
                    },
            ),
            Text(
              'הגדרת שרת בלבד. טסטנט נשאר סביבת בדיקה ולא Mainnet.',
              style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }

  Widget _botStatusCard(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final started =
        widget.backendProvider.backendBotStatusDetails?['status'] == 'started';
    final kill =
        widget.backendProvider.backendBotStatusDetails?['kill_switch'] ??
        widget.backendProvider.backendBotStatusDetails?['bot_kill_switch'];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: started,
              onChanged: widget.backendProvider.isBackendBotLoading
                  ? null
                  : (value) async {
                      final ok = value
                          ? await widget.backendProvider.startBackendBot()
                          : await widget.backendProvider.stopBackendBot();
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            ok
                                ? (value ? 'הבוט הופעל' : 'הבוט כובה')
                                : widget.backendProvider.userVisibleBotError ??
                                      (value ? 'הפעלה נכשלה' : 'כיבוי נכשל'),
                          ),
                        ),
                      );
                    },
              activeThumbColor: scheme.primary,
              title: Text(
                started ? 'הבוט פעיל' : 'הבוט כבוי',
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                  color: started ? scheme.primary : scheme.onSurfaceVariant,
                ),
              ),
              subtitle: Text(
                started ? 'לחץ על המתג כדי לכבות' : 'לחץ על המתג כדי להפעיל',
                style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
              ),
            ),
            if (kill != null) ...[
              const SizedBox(height: 2),
              Text(
                'מתג חירום: ${kill == true ? 'פעיל' : 'כבוי'}',
                style: TextStyle(
                  fontSize: 13,
                  color: kill == true ? scheme.error : scheme.onSurfaceVariant,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _reportCard(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final summary = _buildReportSummary();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SegmentedTabs(
              labels: const ['יומי', 'שבועי', 'חודשי'],
              selectedIndex: switch (_period) {
                _ReportPeriod.daily => 0,
                _ReportPeriod.weekly => 1,
                _ReportPeriod.monthly => 2,
              },
              onChanged: (index) {
                setState(() {
                  _period = switch (index) {
                    0 => _ReportPeriod.daily,
                    1 => _ReportPeriod.weekly,
                    _ => _ReportPeriod.monthly,
                  };
                });
              },
            ),
            const SizedBox(height: 12),
            _reportRow(context, 'עסקאות', summary.trades.toString()),
            _reportRow(
              context,
              'אחוז הצלחה',
              '${summary.winRate.toStringAsFixed(1)}%',
            ),
            _reportRow(
              context,
              'רווח/הפסד ממומש',
              _fmtUsdSigned(summary.realizedPnl),
              color: summary.realizedPnl >= 0 ? Colors.green : scheme.error,
            ),
            _reportRow(context, 'הסימבול הטוב ביותר', summary.bestSymbol),
            const SizedBox(height: 10),
            Text(
              summary.note,
              style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _exportReport(context, summary),
              icon: const Icon(Icons.file_download_outlined),
              label: const Text('ייצוא דוח לקובץ'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _reportRow(
    BuildContext context,
    String label,
    String value, {
    Color? color,
  }) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(fontSize: 13, color: scheme.onSurfaceVariant),
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _statusRow(
    BuildContext context,
    String label,
    String value, {
    bool? positive,
  }) {
    final scheme = Theme.of(context).colorScheme;
    final color = positive == null
        ? null
        : positive
        ? Colors.green
        : scheme.error;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(fontSize: 13, color: scheme.onSurfaceVariant),
            ),
          ),
          Text(
            value,
            textAlign: TextAlign.left,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  List<_ReadinessItem> _readinessChecklist({
    required Map<String, dynamic> health,
    required Map<String, dynamic> aiTeam,
    required Map<String, dynamic> demo,
    required Map<String, dynamic> chief,
    required Map<String, dynamic>? portfolio,
    required Map<String, dynamic>? performance,
  }) {
    final executionMode = (health['execution_mode'] ?? chief['execution_mode'])
        ?.toString();
    final binanceOk = health['binance_testnet_ok'] == true;
    final cryptoDemoState = binanceOk
        ? _ReadinessState.ok
        : executionMode == 'BINANCE_TESTNET'
        ? _ReadinessState.blocked
        : _ReadinessState.warning;
    final aiProvider = health['ai_provider']?.toString();
    final agentsTotal = _asInt(aiTeam['agents_total']);
    final demoWeekLoaded = demo.isNotEmpty;
    final chiefLoaded = chief.isNotEmpty;
    final chiefOff = chief['enabled'] == false;
    final liveTradingAllowed = chief['live_trading_allowed'] == true;
    final killSwitchActive = health['kill_switch_active'] == true;

    return [
      _ReadinessItem(
        label: 'Backend healthy',
        state: health['backend_ok'] == true
            ? _ReadinessState.ok
            : _ReadinessState.blocked,
        critical: true,
      ),
      _ReadinessItem(
        label: 'Crypto Demo connected',
        state: cryptoDemoState,
        critical: executionMode == 'BINANCE_TESTNET',
      ),
      _ReadinessItem(
        label: 'AI provider connected or fallback active',
        state: aiProvider == null || aiProvider.isEmpty
            ? _ReadinessState.warning
            : _ReadinessState.ok,
      ),
      _ReadinessItem(
        label: '4 agents available',
        state: agentsTotal == 4 ? _ReadinessState.ok : _ReadinessState.blocked,
        critical: true,
      ),
      _ReadinessItem(
        label: 'Chief AI Manager ready',
        state: health['chief_manager_ready'] == true
            ? _ReadinessState.ok
            : _ReadinessState.blocked,
        critical: true,
      ),
      _ReadinessItem(
        label: 'Demo Week Mode available',
        state: demoWeekLoaded ? _ReadinessState.ok : _ReadinessState.warning,
      ),
      _ReadinessItem(
        label: 'Chief Autonomy currently OFF',
        state: !chiefLoaded
            ? _ReadinessState.warning
            : chiefOff
            ? _ReadinessState.ok
            : _ReadinessState.blocked,
        critical: true,
      ),
      _ReadinessItem(
        label: 'Live trading disabled',
        state: liveTradingAllowed
            ? _ReadinessState.blocked
            : _ReadinessState.ok,
        critical: true,
      ),
      _ReadinessItem(
        label: 'Kill Switch inactive',
        state: killSwitchActive ? _ReadinessState.blocked : _ReadinessState.ok,
        critical: true,
      ),
      _ReadinessItem(
        label: 'Portfolio loads',
        state: portfolio == null ? _ReadinessState.blocked : _ReadinessState.ok,
        critical: true,
      ),
      _ReadinessItem(
        label: 'Performance loads',
        state: performance == null
            ? _ReadinessState.blocked
            : _ReadinessState.ok,
        critical: true,
      ),
    ];
  }

  int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  Color _readinessColor(BuildContext context, _ReadinessState state) {
    final scheme = Theme.of(context).colorScheme;
    return switch (state) {
      _ReadinessState.ok => Colors.green,
      _ReadinessState.warning => Colors.orange,
      _ReadinessState.blocked => scheme.error,
    };
  }

  IconData _readinessIcon(_ReadinessState state) {
    return switch (state) {
      _ReadinessState.ok => Icons.check_circle_outline,
      _ReadinessState.warning => Icons.warning_amber_outlined,
      _ReadinessState.blocked => Icons.block_outlined,
    };
  }

  String _readinessLabel(_ReadinessState state) {
    return switch (state) {
      _ReadinessState.ok => 'OK',
      _ReadinessState.warning => 'Warning',
      _ReadinessState.blocked => 'Blocked',
    };
  }

  String _formatTime(DateTime value) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(value.hour)}:${two(value.minute)}:${two(value.second)}';
  }

  Map<String, dynamic> _mapOf(dynamic raw) {
    if (raw is Map) {
      return Map<String, dynamic>.from(
        raw.map((key, value) => MapEntry(key.toString(), value)),
      );
    }
    return <String, dynamic>{};
  }

  String _friendlyExecutionMode(dynamic raw) {
    return switch (raw?.toString()) {
      'BINANCE_TESTNET' => 'Crypto Demo',
      'PAPER_DEMO' => 'Paper Demo',
      _ => raw?.toString() ?? '—',
    };
  }

  String _friendlyStatus(dynamic raw) {
    return switch (raw?.toString()) {
      'MOCK' => 'Demo Logic',
      'REAL_DATA' => 'Live Data',
      'AI_CONNECTED' => 'AI Connected',
      _ => raw?.toString() ?? '—',
    };
  }

  String _friendlyAction(dynamic raw) {
    return switch (raw?.toString().toUpperCase()) {
      'HOLD' => 'Waiting',
      'BUY' => 'Buy Signal',
      'SELL' => 'Sell Signal',
      _ => raw?.toString() ?? '—',
    };
  }

  String _executionModeDropdownValue(BackendProvider backend) {
    final em = backend.backendExecutionModeLabel.trim();
    if (em == 'PAPER_DEMO' || em == 'BINANCE_TESTNET') return em;
    return 'BINANCE_TESTNET';
  }

  _ReportSummary _buildReportSummary() {
    final now = DateTime.now();
    final start = switch (_period) {
      _ReportPeriod.daily => DateTime(now.year, now.month, now.day),
      _ReportPeriod.weekly => now.subtract(const Duration(days: 7)),
      _ReportPeriod.monthly => DateTime(now.year, now.month, 1),
    };
    final rows = <Map<String, dynamic>>[];
    for (final raw in widget.backendProvider.backendTradeHistory) {
      if (raw is! Map) continue;
      final m = Map<String, dynamic>.from(
        raw.map((k, v) => MapEntry(k.toString(), v)),
      );
      final closedAt = _parseDate(m['closed_at']) ?? _parseDate(m['opened_at']);
      if (closedAt == null || closedAt.isBefore(start)) continue;
      rows.add(m);
    }

    var wins = 0;
    var losses = 0;
    var pnl = 0.0;
    final bySymbol = <String, double>{};
    for (final row in rows) {
      final pl = _asDouble(row['profit_loss']);
      final sym = row['symbol']?.toString() ?? '—';
      pnl += pl;
      bySymbol[sym] = (bySymbol[sym] ?? 0) + pl;
      if (pl > 0) wins++;
      if (pl < 0) losses++;
    }

    var bestSymbol = '—';
    var bestValue = double.negativeInfinity;
    for (final entry in bySymbol.entries) {
      if (entry.value > bestValue) {
        bestValue = entry.value;
        bestSymbol = entry.key;
      }
    }

    final trades = rows.length;
    final winRate = trades == 0 ? 0.0 : (wins / trades) * 100.0;
    final periodLabel = switch (_period) {
      _ReportPeriod.daily => 'יומי',
      _ReportPeriod.weekly => 'שבועי',
      _ReportPeriod.monthly => 'חודשי',
    };
    return _ReportSummary(
      periodLabel: periodLabel,
      from: start,
      to: now,
      trades: trades,
      wins: wins,
      losses: losses,
      winRate: winRate,
      realizedPnl: pnl,
      bestSymbol: bestSymbol,
      note: trades == 0
          ? 'אין עסקאות סגורות בתקופה הזאת עדיין.'
          : 'מבוסס על עסקאות סגורות מהיסטוריית השרת.',
    );
  }

  Future<void> _exportReport(
    BuildContext context,
    _ReportSummary summary,
  ) async {
    await widget.backendProvider.refreshBackendTrades(clearBotError: false);
    await widget.backendProvider.refreshBackendPerformance();
    final freshSummary = _buildReportSummary();
    final safePeriod = freshSummary.periodLabel.toLowerCase();
    final stamp = DateTime.now().toIso8601String().replaceAll(':', '-');
    final file = File(
      '${Directory.systemTemp.path}${Platform.pathSeparator}trading_bot_${safePeriod}_report_$stamp.txt',
    );
    await file.writeAsString(_reportText(freshSummary));
    if (!context.mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('הדוח נשמר: ${file.path}')));
  }

  String _reportText(_ReportSummary s) {
    return [
      'דוח ${s.periodLabel} - בוט מסחר',
      'מתאריך: ${s.from.toIso8601String()}',
      'עד תאריך: ${s.to.toIso8601String()}',
      '',
      'עסקאות: ${s.trades}',
      'עסקאות מרוויחות: ${s.wins}',
      'עסקאות מפסידות: ${s.losses}',
      'אחוז הצלחה: ${s.winRate.toStringAsFixed(1)}%',
      'רווח/הפסד ממומש: ${_fmtUsdSigned(s.realizedPnl)}',
      'הסימבול הטוב ביותר: ${s.bestSymbol}',
      '',
      s.note,
    ].join('\n');
  }

  double _asDouble(dynamic v) {
    if (v is num) return v.toDouble();
    return double.tryParse(v?.toString() ?? '') ?? 0;
  }

  DateTime? _parseDate(dynamic v) {
    if (v is String) return DateTime.tryParse(v);
    return null;
  }

  String _fmtUsdSigned(double v) {
    final sign = v >= 0 ? '+' : '-';
    return '$sign\$${v.abs().toStringAsFixed(2)}';
  }
}

class _ReportSummary {
  const _ReportSummary({
    required this.periodLabel,
    required this.from,
    required this.to,
    required this.trades,
    required this.wins,
    required this.losses,
    required this.winRate,
    required this.realizedPnl,
    required this.bestSymbol,
    required this.note,
  });

  final String periodLabel;
  final DateTime from;
  final DateTime to;
  final int trades;
  final int wins;
  final int losses;
  final double winRate;
  final double realizedPnl;
  final String bestSymbol;
  final String note;
}

class _ReadinessItem {
  const _ReadinessItem({
    required this.label,
    required this.state,
    this.critical = false,
  });

  final String label;
  final _ReadinessState state;
  final bool critical;
}
