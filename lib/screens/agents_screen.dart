import 'dart:convert';

import 'package:flutter/material.dart';

import '../models/bot_settings_model.dart';
import '../providers/backend_provider.dart';
import '../providers/bot_provider.dart';
import '../widgets/status_badge.dart';

enum _AgentTarget {
  all('ALL', 'All Agents', Icons.groups_2_outlined),
  risk('RISK', 'Risk', Icons.shield_outlined),
  macro('MACRO', 'Macro/News', Icons.public),
  technical('TECHNICAL', 'Technical', Icons.analytics_outlined),
  assetScout('ASSET_SCOUT', 'Asset Scout', Icons.explore_outlined),
  chief('CHIEF', 'Chief AI', Icons.psychology_alt_outlined);

  const _AgentTarget(this.key, this.label, this.icon);

  final String key;
  final String label;
  final IconData icon;
}

class AgentsScreen extends StatefulWidget {
  const AgentsScreen({
    super.key,
    required this.botProvider,
    required this.backendProvider,
  });

  final BotProvider botProvider;
  final BackendProvider backendProvider;

  @override
  State<AgentsScreen> createState() => _AgentsScreenState();
}

class _AgentsScreenState extends State<AgentsScreen> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  _AgentTarget _selectedTarget = _AgentTarget.all;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.backendProvider.refreshAiTeamPreview(showLoading: false);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([widget.botProvider, widget.backendProvider]),
      builder: (context, _) {
        final backend = widget.backendProvider;
        final simple =
            widget.botProvider.settings.displayMode == DisplayMode.simple;
        return Column(
          children: [
            _agentBar(context, backend),
            Expanded(
              child: RefreshIndicator(
                onRefresh: () => backend.refreshAiTeamPreview(),
                child: _chatList(context, backend, simple: simple),
              ),
            ),
            _inputBar(context, backend),
          ],
        );
      },
    );
  }

  Widget _agentBar(BuildContext context, BackendProvider backend) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 8),
      decoration: BoxDecoration(
        color: scheme.surface,
        border: Border(bottom: BorderSide(color: scheme.outlineVariant)),
      ),
      child: SizedBox(
        height: 88,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: _AgentTarget.values.length,
          separatorBuilder: (_, _) => const SizedBox(width: 12),
          itemBuilder: (context, index) {
            final target = _AgentTarget.values[index];
            return _agentAvatar(context, backend, target);
          },
        ),
      ),
    );
  }

  Widget _agentAvatar(
    BuildContext context,
    BackendProvider backend,
    _AgentTarget target,
  ) {
    final scheme = Theme.of(context).colorScheme;
    final selected = _selectedTarget == target;
    final color = _targetStatusColor(context, backend, target);
    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: () => setState(() => _selectedTarget = target),
      child: SizedBox(
        width: 76,
        child: Column(
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: selected
                    ? scheme.primaryContainer
                    : scheme.surfaceContainerHighest,
                border: Border.all(color: color, width: selected ? 3 : 2),
                boxShadow: [
                  if (selected)
                    BoxShadow(
                      color: color.withValues(alpha: 0.28),
                      blurRadius: 14,
                      spreadRadius: 1,
                    ),
                ],
              ),
              child: Icon(
                target.icon,
                color: selected ? scheme.primary : scheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              target.label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 11,
                fontWeight: selected ? FontWeight.w900 : FontWeight.w700,
                color: selected ? scheme.primary : scheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _chatList(
    BuildContext context,
    BackendProvider backend, {
    required bool simple,
  }) {
    final messages = backend.aiTeamChatMessages;
    final scheme = Theme.of(context).colorScheme;
    return ListView(
      controller: _scrollController,
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 16),
      children: [
        if (backend.aiTeamError != null) _errorBubble(context, backend),
        if (backend.isAiTeamLoading && messages.isEmpty) ...[
          const SizedBox(height: 8),
          const LinearProgressIndicator(),
        ],
        if (messages.isEmpty) _welcomeBubble(context, backend),
        for (final message in messages)
          _chatBubble(context, message, simple: simple),
        if (backend.isAiTeamChatLoading)
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: scheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(18),
              ),
              child: const Text('Agents are thinking...'),
            ),
          ),
      ],
    );
  }

  Widget _welcomeBubble(BuildContext context, BackendProvider backend) {
    final chief = _mapOf(backend.aiTeamPreview?['chief_decision']);
    final action = chief['final_action']?.toString();
    final confidence = chief['final_confidence']?.toString();
    final text = chief.isEmpty
        ? 'Ask the AI trading team about risk, news, technical entries, assets to watch, or the Chief AI decision.'
        : 'Chief AI is ready. Latest advisory view: ${_friendlyAction(action)} at ${confidence ?? '—'}% confidence.';
    return _systemBubble(context, text);
  }

  Widget _errorBubble(BuildContext context, BackendProvider backend) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.errorContainer.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: scheme.error),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              backend.userVisibleAiTeamError ?? 'AI Team unavailable',
              style: TextStyle(color: scheme.onErrorContainer),
            ),
          ),
          TextButton(
            onPressed: () => backend.refreshAiTeamPreview(),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _systemBubble(BuildContext context, String text) {
    final scheme = Theme.of(context).colorScheme;
    return Align(
      alignment: Alignment.center,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(
          color: scheme.surfaceContainerHighest.withValues(alpha: 0.65),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(
          text,
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
        ),
      ),
    );
  }

  Widget _chatBubble(
    BuildContext context,
    Map<String, dynamic> message, {
    required bool simple,
  }) {
    final scheme = Theme.of(context).colorScheme;
    final type = message['type']?.toString() ?? 'agent';
    final isUser = type == 'user';
    final isChief = type == 'chief' || message['agent_key'] == 'CHIEF';
    final align = isUser ? Alignment.centerRight : Alignment.centerLeft;
    final bg = isUser
        ? scheme.primaryContainer
        : isChief
        ? scheme.tertiaryContainer.withValues(alpha: 0.65)
        : scheme.surfaceContainerHighest.withValues(alpha: 0.75);
    final text =
        (simple
                ? message['short_text'] ?? message['text'] ?? message['message']
                : message['text'] ??
                      message['short_text'] ??
                      message['message'])
            ?.toString() ??
        '';
    return Align(
      alignment: align,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width * 0.82,
        ),
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(20).copyWith(
            bottomRight: isUser ? const Radius.circular(6) : null,
            bottomLeft: isUser ? null : const Radius.circular(6),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!isUser) _bubbleHeader(context, message, isChief: isChief),
            Text(
              text,
              style: TextStyle(
                height: 1.35,
                fontWeight: isChief ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
            if (!simple && !isUser) _advancedDetails(context, message),
          ],
        ),
      ),
    );
  }

  Widget _bubbleHeader(
    BuildContext context,
    Map<String, dynamic> message, {
    required bool isChief,
  }) {
    final scheme = Theme.of(context).colorScheme;
    final action = message['action']?.toString();
    final agentKey = message['agent_key']?.toString();
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Icon(
            _iconForAgent(agentKey),
            size: 17,
            color: isChief ? scheme.tertiary : scheme.primary,
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              message['sender']?.toString() ??
                  (isChief ? 'Chief AI Manager' : 'Agent'),
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900),
            ),
          ),
          if (action != null)
            StatusBadge(
              label: _friendlyAction(action),
              type: _actionBadgeType(action),
            ),
        ],
      ),
    );
  }

  Widget _advancedDetails(BuildContext context, Map<String, dynamic> message) {
    final confidence = message['confidence']?.toString() ?? '—';
    final risk = message['risk_level']?.toString();
    return Theme(
      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        tilePadding: EdgeInsets.zero,
        childrenPadding: EdgeInsets.zero,
        title: const Text(
          'Details',
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900),
        ),
        children: [
          _detailLine('Confidence', confidence),
          if (risk != null) _detailLine('Risk', risk),
          _detailLine('Agent', message['agent_key']?.toString() ?? '—'),
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(top: 6),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              const JsonEncoder.withIndent('  ').convert(message),
              textDirection: TextDirection.ltr,
              style: const TextStyle(fontSize: 10, fontFamily: 'monospace'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _detailLine(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 12))),
          Text(
            value,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }

  Widget _inputBar(BuildContext context, BackendProvider backend) {
    final scheme = Theme.of(context).colorScheme;
    return SafeArea(
      top: false,
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 10),
        decoration: BoxDecoration(
          color: scheme.surface,
          border: Border(top: BorderSide(color: scheme.outlineVariant)),
        ),
        child: Row(
          children: [
            IconButton(
              tooltip: 'Voice input',
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Voice input coming soon')),
                );
              },
              icon: const Icon(Icons.mic_none_outlined),
            ),
            Expanded(
              child: TextField(
                controller: _controller,
                minLines: 1,
                maxLines: 4,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _send(backend),
                decoration: InputDecoration(
                  hintText: 'Ask the agents...',
                  filled: true,
                  fillColor: scheme.surfaceContainerHighest.withValues(
                    alpha: 0.55,
                  ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(22),
                    borderSide: BorderSide.none,
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 10,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: backend.isAiTeamChatLoading
                  ? null
                  : () => _send(backend),
              style: FilledButton.styleFrom(
                shape: const CircleBorder(),
                padding: const EdgeInsets.all(13),
              ),
              child: const Icon(Icons.send),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _send(BackendProvider backend) async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();
    final ok = await backend.sendAiTeamChatMessage(
      message: text,
      targetAgent: _selectedTarget.key,
    );
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(backend.userVisibleAiTeamError ?? 'Send failed'),
        ),
      );
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Color _targetStatusColor(
    BuildContext context,
    BackendProvider backend,
    _AgentTarget target,
  ) {
    if (target == _AgentTarget.all) {
      return Theme.of(context).colorScheme.primary;
    }
    final raw = _agentByKey(backend, target.key);
    if (target == _AgentTarget.chief) {
      final chief = _mapOf(backend.aiTeamPreview?['chief_decision']);
      return chief.isEmpty ? Colors.grey : Colors.green;
    }
    if (raw?['veto'] == true) return Colors.red;
    final status = raw?['current_status']?.toString();
    return switch (status) {
      'REAL_DATA' => Colors.green,
      'AI_CONNECTED' => Colors.blue,
      'MOCK' => Colors.grey,
      _ => Colors.grey,
    };
  }

  Map<String, dynamic>? _agentByKey(BackendProvider backend, String key) {
    final agents = backend.aiTeamPreview?['agents'];
    if (agents is! List) return null;
    for (final raw in agents) {
      if (raw is! Map) continue;
      final map = _mapOf(raw);
      final name = map['agent_name']?.toString() ?? '';
      if (_keyForAgentName(name) == key) return map;
    }
    return null;
  }

  String _keyForAgentName(String name) {
    if (name.contains('Risk')) return 'RISK';
    if (name.contains('Macro')) return 'MACRO';
    if (name.contains('Technical')) return 'TECHNICAL';
    if (name.contains('Asset')) return 'ASSET_SCOUT';
    return 'CHIEF';
  }

  IconData _iconForAgent(String? key) {
    return switch (key) {
      'RISK' => Icons.shield_outlined,
      'MACRO' => Icons.public,
      'TECHNICAL' => Icons.analytics_outlined,
      'ASSET_SCOUT' => Icons.explore_outlined,
      'CHIEF' => Icons.psychology_alt_outlined,
      _ => Icons.memory_outlined,
    };
  }

  Map<String, dynamic> _mapOf(dynamic raw) {
    if (raw is Map) {
      return Map<String, dynamic>.from(
        raw.map((key, value) => MapEntry(key.toString(), value)),
      );
    }
    return <String, dynamic>{};
  }

  String _friendlyAction(dynamic raw) {
    return switch (raw?.toString().toUpperCase()) {
      'HOLD' => 'Waiting',
      'BUY' => 'Buy Signal',
      'SELL' => 'Sell Signal',
      _ => raw?.toString() ?? '—',
    };
  }

  StatusBadgeType _actionBadgeType(String action) {
    return switch (action.toUpperCase()) {
      'BUY' => StatusBadgeType.positive,
      'SELL' => StatusBadgeType.negative,
      'HOLD' => StatusBadgeType.warning,
      _ => StatusBadgeType.neutral,
    };
  }
}
