import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/chat_message.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/kpi_card.dart';

/// Sales Engineer tab — agentic quote + RAG sync (embedded in AI Advisor).
class SalesEngineerTab extends StatefulWidget {
  const SalesEngineerTab({
    super.key,
    required this.api,
    this.onRagSynced,
    this.onOpenRagChat,
  });

  final ApiService api;
  final void Function(String userBrief, String ragAnswer, List<ChatSource> sources)? onRagSynced;
  final VoidCallback? onOpenRagChat;

  @override
  State<SalesEngineerTab> createState() => _SalesEngineerTabState();
}

class _SalesEngineerTabState extends State<SalesEngineerTab> {
  final _briefCtrl = TextEditingController(
    text: 'Minimalist home office for a 10x10ft room under RM5000 in Kuala Lumpur. No drilling.',
  );
  final _locationCtrl = TextEditingController(text: 'Kuala Lumpur');
  bool _busy = false;
  String? _err;
  Map<String, dynamic>? _result;
  Map<String, dynamic>? _metrics;
  String? _ragMode;

  @override
  void dispose() {
    _briefCtrl.dispose();
    _locationCtrl.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadMetrics());
  }

  Future<void> _loadMetrics() async {
    final sid = context.read<SessionProvider>().smeId;
    try {
      final m = await widget.api.fetchBusinessValueMetrics(smeId: sid);
      if (mounted) setState(() => _metrics = m);
    } catch (_) {}
  }

  Future<void> _pickBriefFile() async {
    final res = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'txt', 'docx'],
      withData: true,
    );
    if (res == null || res.files.isEmpty || res.files.single.bytes == null) return;
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final parsed = await widget.api.parseRequirements(
        bytes: res.files.single.bytes!,
        fileName: res.files.single.name,
      );
      final budget = parsed['budget'];
      final style = parsed['style'];
      final room = parsed['room_size'];
      final loc = parsed['location'];
      _briefCtrl.text =
          '${style ?? "Setup"} ${room ?? ""} budget RM ${budget ?? "?"} at $loc. '
          '${(parsed["explicit_constraints"] as List?)?.join(", ") ?? ""}';
      if (loc != null) _locationCtrl.text = '$loc';
    } catch (e) {
      setState(() => _err = ApiService.friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _runAgent() async {
    setState(() {
      _busy = true;
      _err = null;
      _result = null;
      _ragMode = null;
    });
    try {
      final sid = context.read<SessionProvider>().smeId;
      final brief = _briefCtrl.text.trim();
      final out = await widget.api.runSalesAgent(
        smeId: sid,
        briefText: brief,
        location: _locationCtrl.text.trim(),
      );
      await _loadMetrics();
      if (!mounted) return;
      setState(() {
        _result = out;
        _ragMode = out['rag_mode'] as String?;
      });

      final ragAnswer = out['rag_answer'] as String?;
      if (ragAnswer != null && ragAnswer.isNotEmpty && widget.onRagSynced != null) {
        final sources = (out['rag_sources'] as List<dynamic>? ?? [])
            .map((e) => ChatSource.fromJson(e as Map<String, dynamic>))
            .toList();
        widget.onRagSynced!(brief, ragAnswer, sources);
      }
    } catch (e) {
      if (mounted) setState(() => _err = ApiService.friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final quote = _result?['quote'] as Map<String, dynamic>?;
    final breakdown = quote?['breakdown'] as Map<String, dynamic>?;
    final bv = _result?['business_value'] as Map<String, dynamic>? ?? _metrics;
    final trace = (_result?['agent_trace'] as List<dynamic>? ?? []);
    final ragAnswer = _result?['rag_answer'] as String?;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          'Upload a brief or type requirements. The agent builds a quote, then RAG syncs financing advice to the chat tab.',
          style: TextStyle(color: Colors.grey.shade600, fontSize: 13, height: 1.4),
        ),
        const SizedBox(height: 12),
        if (bv != null) ...[
          Row(
            children: [
              Expanded(
                child: KPICard(
                  title: 'Time saved',
                  value: '${bv['time_saved_minutes_per_quote'] ?? 43} min',
                  leading: const Icon(Icons.schedule, size: 20, color: AppTheme.teal),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: KPICard(
                  title: 'Cost saved',
                  value: 'RM ${bv['cost_saved_rm'] ?? 0}',
                  leading: const Icon(Icons.savings_outlined, size: 20, color: AppTheme.teal),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
        ],
        TextField(
          controller: _briefCtrl,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Client brief',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _locationCtrl,
          decoration: const InputDecoration(labelText: 'Location', border: OutlineInputBorder()),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            OutlinedButton.icon(
              onPressed: _busy ? null : _pickBriefFile,
              icon: const Icon(Icons.upload_file),
              label: const Text('Upload brief'),
            ),
            FilledButton.icon(
              onPressed: _busy ? null : _runAgent,
              icon: _busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.smart_toy_outlined),
              label: Text(_busy ? 'Running…' : 'Run quote + RAG sync'),
              style: FilledButton.styleFrom(backgroundColor: AppTheme.teal),
            ),
          ],
        ),
        if (_err != null) ...[
          const SizedBox(height: 12),
          Text(_err!, style: const TextStyle(color: Colors.red, fontSize: 13)),
        ],
        if (ragAnswer != null) ...[
          const SizedBox(height: 16),
          Card(
            color: AppTheme.teal.withOpacity(0.06),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.sync_rounded, color: AppTheme.teal, size: 18),
                      const SizedBox(width: 8),
                      Text(
                        'RAG synced${_ragMode != null ? " ($_ragMode)" : ""}',
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(ragAnswer, style: TextStyle(color: Colors.grey.shade800, height: 1.45, fontSize: 13)),
                  if (widget.onOpenRagChat != null) ...[
                    const SizedBox(height: 10),
                    TextButton.icon(
                      onPressed: widget.onOpenRagChat,
                      icon: const Icon(Icons.chat_bubble_outline),
                      label: const Text('Continue in RAG Chat'),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
        if (_result != null) ...[
          const SizedBox(height: 16),
          Text('Agent trace', style: Theme.of(context).textTheme.titleSmall),
          ...trace.map(
            (t) => ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text('${(t as Map)['tool'] ?? t['step']}', style: const TextStyle(fontSize: 13)),
              subtitle: Text('${t['detail'] ?? ''}', style: const TextStyle(fontSize: 12)),
            ),
          ),
        ],
        if (quote != null && breakdown != null) ...[
          const SizedBox(height: 12),
          Text('Quote #${quote['quote_id']}', style: Theme.of(context).textTheme.titleMedium),
          ...(quote['items'] as List<dynamic>? ?? []).map((item) {
            final m = item as Map<String, dynamic>;
            return ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(m['product_name']?.toString() ?? '', style: const TextStyle(fontSize: 13)),
              trailing: Text('RM ${m['unit_price_rm']}', style: const TextStyle(fontWeight: FontWeight.w600)),
            );
          }),
          _line('Grand total', breakdown['grand_total_rm'], bold: true),
          _line('ETA (days)', breakdown['estimated_delivery_days']),
        ],
      ],
    );
  }

  Widget _line(String label, dynamic value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(fontWeight: bold ? FontWeight.w700 : FontWeight.w400, fontSize: 13)),
          Text(
            value is num && label.contains('ETA') ? '$value' : 'RM $value',
            style: TextStyle(fontWeight: bold ? FontWeight.w700 : FontWeight.w500, fontSize: 13),
          ),
        ],
      ),
    );
  }
}
