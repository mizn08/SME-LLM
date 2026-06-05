import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/chat_message.dart';
import '../l10n/app_strings.dart';
import '../providers/recommendation_provider.dart';
import '../providers/session_provider.dart';
import '../providers/settings_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../utils/constants.dart';
import '../widgets/formatted_chat_text.dart';
import '../widgets/kpi_card.dart';

/// Autonomous Sales Engineer tab — requirements brief → catalog quote → BNPL RAG sync.
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
    text:
        'Kopi Maju (SME 1) needs RM3,500 digital POS upgrade in Kuala Lumpur. '
        'Compare BNPL vs grant vs micro-credit and keep monthly payments low.',
  );
  final _locationCtrl = TextEditingController(text: 'Kuala Lumpur');
  bool _busy = false;
  String? _err;
  Map<String, dynamic>? _result;
  Map<String, dynamic>? _metrics;
  String? _ragMode;
  String? _apiHint;
  Map<String, dynamic>? _transcriptSummary;
  final List<String> _demoLog = [];

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
    } catch (e) {
      if (mounted) {
        setState(() {
          _err = ApiService.friendlyError(e);
          _apiHint = resolveApiBase();
        });
      }
    }
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
      final loc = parsed['location'];
      final category = parsed['purchase_category'];
      _briefCtrl.text =
          'SME purchase${category != null ? " ($category)" : ""}: budget RM ${budget ?? "?"} at $loc. '
          '${(parsed["explicit_constraints"] as List?)?.join(", ") ?? ""}';
      if (loc != null) _locationCtrl.text = '$loc';
    } catch (e) {
      if (mounted) setState(() => _err = ApiService.friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickTranscriptFile() async {
    final res = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'txt', 'docx', 'md', 'json', 'csv'],
      withData: true,
    );
    if (res == null || res.files.isEmpty || res.files.single.bytes == null) return;
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final parsed = await widget.api.parseClientTranscript(
        bytes: res.files.single.bytes!,
        fileName: res.files.single.name,
      );
      final budget = parsed['budget'];
      final loc = parsed['location'];
      final category = parsed['purchase_category'];
      final constraints = (parsed['explicit_constraints'] as List<dynamic>? ?? []).join(', ');
      _briefCtrl.text =
          'Client transcript requirements${category != null ? " ($category)" : ""}: '
          'budget RM ${budget ?? "?"}, location ${loc ?? "Kuala Lumpur"}. '
          '${constraints.isNotEmpty ? "Constraints: $constraints." : ""}';
      if (loc != null) _locationCtrl.text = '$loc';
      if (!mounted) return;
      setState(() => _transcriptSummary = parsed);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Transcript parsed • confidence ${(100 * ((parsed['confidence'] as num?)?.toDouble() ?? 0)).toStringAsFixed(0)}%',
          ),
        ),
      );
    } catch (e) {
      if (mounted) setState(() => _err = ApiService.friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _runAgent() async {
    setState(() {
      _busy = true;
      _err = null;
      _apiHint = null;
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
      final agentErr = out['error'] as String?;
      final complete = out['task_complete'] == true;
      _syncQuoteToFinancing(out);
      if (!mounted) return;
      setState(() {
        _result = out;
        _ragMode = out['rag_mode'] as String?;
        _err = (!complete && agentErr != null && agentErr.isNotEmpty)
            ? agentErr
            : (!complete ? 'Quote not generated — see agent trace below.' : null);
        _apiHint = null;
      });

      final ragAnswer = out['rag_answer'] as String?;
      if (ragAnswer != null && ragAnswer.isNotEmpty && widget.onRagSynced != null) {
        final sources = (out['rag_sources'] as List<dynamic>? ?? [])
            .map((e) => ChatSource.fromJson(e as Map<String, dynamic>))
            .toList();
        widget.onRagSynced!(brief, ragAnswer, sources);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _err = ApiService.friendlyError(e);
          _apiHint = resolveApiBase();
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _runDemoScript() async {
    const demoTranscript = '''
Client: We run Kopi Maju and need a complete POS + inventory + website package.
Client: Budget around RM 12000 and we prefer low monthly payment.
Client: Delivery and setup should be in Kuala Lumpur this month.
Agent: Noted, please compare BNPL vs grant vs micro-credit.
''';

    setState(() {
      _busy = true;
      _err = null;
      _apiHint = null;
      _result = null;
      _ragMode = null;
      _demoLog
        ..clear()
        ..add('1/4 Parsing unstructured transcript...');
    });
    try {
      final parsed = await widget.api.parseClientTranscript(
        bytes: utf8.encode(demoTranscript),
        fileName: 'demo_transcript.txt',
      );
      final budget = parsed['budget'];
      final loc = parsed['location'];
      final category = parsed['purchase_category'];
      final constraints = (parsed['explicit_constraints'] as List<dynamic>? ?? []).join(', ');
      _briefCtrl.text =
          'Client transcript requirements${category != null ? " ($category)" : ""}: '
          'budget RM ${budget ?? "?"}, location ${loc ?? "Kuala Lumpur"}. '
          '${constraints.isNotEmpty ? "Constraints: $constraints." : ""}';
      if (loc != null) _locationCtrl.text = '$loc';
      _transcriptSummary = parsed;
      _demoLog.add('2/4 Transcript parsed. Running Autonomous Sales Engineer...');

      final sid = context.read<SessionProvider>().smeId;
      final brief = _briefCtrl.text.trim();
      final out = await widget.api.runSalesAgent(
        smeId: sid,
        briefText: brief,
        location: _locationCtrl.text.trim(),
      );
      await _loadMetrics();
      if (!mounted) return;
      final agentErr = out['error'] as String?;
      final complete = out['task_complete'] == true;
      _syncQuoteToFinancing(out);
      _demoLog.add('3/4 Quote built and synced to Financing Simulator.');
      setState(() {
        _result = out;
        _ragMode = out['rag_mode'] as String?;
        _err = (!complete && agentErr != null && agentErr.isNotEmpty)
            ? agentErr
            : (!complete ? 'Quote not generated — see agent trace below.' : null);
      });

      final ragAnswer = out['rag_answer'] as String?;
      if (ragAnswer != null && ragAnswer.isNotEmpty && widget.onRagSynced != null) {
        final sources = (out['rag_sources'] as List<dynamic>? ?? [])
            .map((e) => ChatSource.fromJson(e as Map<String, dynamic>))
            .toList();
        widget.onRagSynced!(brief, ragAnswer, sources);
      }
      _demoLog.add('4/4 RAG financing advice synced. Demo flow complete.');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Demo script completed: transcript → quote → finance sync')),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _err = ApiService.friendlyError(e);
          _apiHint = resolveApiBase();
          _demoLog.add('Demo failed: ${ApiService.friendlyError(e)}');
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _useCustomTranscriptText() async {
    final ctrl = TextEditingController();
    final text = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Use custom transcript text'),
        content: SizedBox(
          width: 560,
          child: TextField(
            controller: ctrl,
            maxLines: 10,
            minLines: 6,
            decoration: const InputDecoration(
              hintText: 'Paste client call transcript here...\n\nClient: We need POS and inventory sync...\nAgent: Noted...',
              border: OutlineInputBorder(),
            ),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
            child: const Text('Parse transcript'),
          ),
        ],
      ),
    );
    ctrl.dispose();
    if (text == null || text.isEmpty) return;

    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final parsed = await widget.api.parseClientTranscript(
        bytes: utf8.encode(text),
        fileName: 'custom_transcript.txt',
      );
      final budget = parsed['budget'];
      final loc = parsed['location'];
      final category = parsed['purchase_category'];
      final constraints = (parsed['explicit_constraints'] as List<dynamic>? ?? []).join(', ');
      _briefCtrl.text =
          'Client transcript requirements${category != null ? " ($category)" : ""}: '
          'budget RM ${budget ?? "?"}, location ${loc ?? "Kuala Lumpur"}. '
          '${constraints.isNotEmpty ? "Constraints: $constraints." : ""}';
      if (loc != null) _locationCtrl.text = '$loc';
      if (!mounted) return;
      setState(() => _transcriptSummary = parsed);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Custom transcript parsed • confidence ${(100 * ((parsed['confidence'] as num?)?.toDouble() ?? 0)).toStringAsFixed(0)}%',
          ),
        ),
      );
    } catch (e) {
      if (mounted) setState(() => _err = ApiService.friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _syncQuoteToFinancing(Map<String, dynamic> out) {
    final quote = out['quote'] as Map<String, dynamic>?;
    final breakdown = quote?['breakdown'] as Map<String, dynamic>?;
    final grand = (breakdown?['grand_total_rm'] as num?)?.toDouble();
    if (grand == null || grand <= 0) return;
    final req = out['requirements'] as Map<String, dynamic>? ?? {};
    final category = (req['purchase_category'] as String?)?.toLowerCase() ?? 'equipment';
    context.read<RecommendationProvider>().setResult(
          context.read<RecommendationProvider>().lastResult,
          purchaseAmount: grand,
          purchaseCategory: category,
        );
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Quote RM ${grand.toStringAsFixed(0)} synced to Financing Simulator')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = AppStrings(context.watch<SettingsProvider>().locale);
    final quote = _result?['quote'] as Map<String, dynamic>?;
    final breakdown = quote?['breakdown'] as Map<String, dynamic>?;
    final bv = _result?['business_value'] as Map<String, dynamic>? ?? _metrics;
    final trace = (_result?['agent_trace'] as List<dynamic>? ?? []);
    final agentMode = _result?['agent_mode'] as String?;
    final ragAnswer = _result?['rag_answer'] as String?;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: AppTheme.accentWash,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppTheme.borderColor),
          ),
          child: Text(
            s.salesEngineerFlow,
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.brandBlueDark),
          ),
        ),
        const SizedBox(height: 10),
        Text(
          'Autonomous Sales Engineer — take a client requirements brief, navigate the product catalog, '
          'validate compatibility and budget, then quote and sync BNPL / grant / credit advice to BNPL Chat.',
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
                  leading: const Icon(Icons.account_balance_wallet_outlined, size: 20, color: AppTheme.teal),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          _quantBusinessValue(bv),
          const SizedBox(height: 8),
        ],
        TextField(
          controller: _briefCtrl,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Requirements brief (system design)',
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
            FilledButton.icon(
              onPressed: _busy ? null : _runDemoScript,
              icon: const Icon(Icons.play_circle_fill_rounded),
              label: const Text('Run demo script mode'),
              style: FilledButton.styleFrom(backgroundColor: AppTheme.midnight),
            ),
            OutlinedButton.icon(
              onPressed: _busy ? null : _useCustomTranscriptText,
              icon: const Icon(Icons.edit_note_rounded),
              label: const Text('Use custom transcript text'),
            ),
            OutlinedButton.icon(
              onPressed: _busy ? null : _pickBriefFile,
              icon: const Icon(Icons.upload_file),
              label: const Text('Upload brief (PDF/TXT/DOCX)'),
            ),
            OutlinedButton.icon(
              onPressed: _busy ? null : _pickTranscriptFile,
              icon: const Icon(Icons.chat_outlined),
              label: const Text('Parse client transcript'),
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
              label: Text(_busy ? 'Running…' : 'Design solution & quote'),
              style: FilledButton.styleFrom(backgroundColor: AppTheme.teal),
            ),
          ],
        ),
        if (_err != null) ...[
          const SizedBox(height: 12),
          Text(_err!, style: const TextStyle(color: Colors.red, fontSize: 13)),
          if (_apiHint != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('API: $_apiHint', style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
            ),
        ],
        if (_demoLog.isNotEmpty) ...[
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Demo run status', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  ..._demoLog.map((e) => Text('• $e', style: TextStyle(color: Colors.grey.shade700, fontSize: 12))),
                ],
              ),
            ),
          ),
        ],
        if (_transcriptSummary != null) ...[
          const SizedBox(height: 12),
          _transcriptCard(_transcriptSummary!),
        ],
        if (quote != null && breakdown != null) ...[
          const SizedBox(height: 16),
          _quotedSolutionCard(quote, breakdown),
        ],
        if (trace.isNotEmpty) ...[
          const SizedBox(height: 12),
          _workflowTimeline(trace, agentMode: agentMode),
        ],
        if (ragAnswer != null) ...[
          const SizedBox(height: 12),
          _ragSyncCard(ragAnswer),
        ],
      ],
    );
  }

  static const _stepMeta = <String, ({String label, IconData icon})>{
    'llm_plan': (label: 'LLM workflow plan', icon: Icons.route_outlined),
    'search_products': (label: 'Search product catalog', icon: Icons.inventory_2_outlined),
    'check_compatibility': (label: 'Validate compatibility', icon: Icons.verified_outlined),
    'calculate_shipping': (label: 'Calculate shipping', icon: Icons.local_shipping_outlined),
    'apply_tax': (label: 'Apply SST / tax', icon: Icons.receipt_long_outlined),
    'generate_quote': (label: 'Generate final quote', icon: Icons.request_quote_outlined),
    'done': (label: 'Quote completed', icon: Icons.check_circle_outline),
    'rag_sync': (label: 'Sync BNPL financing advice', icon: Icons.sync_rounded),
  };

  String _friendlyStepLabel(Map<String, dynamic> step) {
    final tool = step['tool'] as String?;
    final raw = step['step'] as String? ?? tool ?? 'step';
    if (tool != null && _stepMeta.containsKey(tool)) return _stepMeta[tool]!.label;
    if (_stepMeta.containsKey(raw)) return _stepMeta[raw]!.label;
    if (raw.startsWith('iter_')) return 'Agent reasoning pass';
    return raw.replaceAll('_', ' ');
  }

  IconData _stepIcon(Map<String, dynamic> step) {
    final tool = step['tool'] as String?;
    final raw = step['step'] as String? ?? '';
    if (tool != null && _stepMeta.containsKey(tool)) return _stepMeta[tool]!.icon;
    if (_stepMeta.containsKey(raw)) return _stepMeta[raw]!.icon;
    if (raw == 'done') return Icons.check_circle_outline;
    if (raw == 'rag_sync') return Icons.sync_rounded;
    return Icons.smart_toy_outlined;
  }

  String _friendlyStepDetail(Map<String, dynamic> step) {
    final detail = (step['detail'] as String?)?.trim() ?? '';
    final source = step['source'] as String?;
    String routing = '';
    if (source == 'llm') {
      routing = 'LLM chose this step';
    } else if (source == 'guardrail_corrected') {
      routing = 'Guardrail corrected routing';
    } else if (source == 'rule_fallback' || source == 'rule_unstick') {
      routing = 'Rule fallback';
    }
    if (detail.isEmpty) return routing.isEmpty ? 'Completed' : routing;
    if (detail.startsWith('quote_id=')) return 'Quote #${detail.split('=').last} saved';
    if (detail.contains('+llm') || detail.contains('bm25')) {
      return 'Financing advice pushed to BNPL Chat';
    }
    if (routing.isNotEmpty && detail != routing) return '$routing · $detail';
    return detail;
  }

  Widget _workflowTimeline(List<dynamic> trace, {String? agentMode}) {
    final steps = trace.whereType<Map<String, dynamic>>().toList();
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppTheme.borderColor),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.accentWash,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.account_tree_outlined, size: 18, color: AppTheme.brandBlue),
                ),
                const SizedBox(width: 10),
                const Text(
                  'Agent workflow',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              agentMode == 'llm_supervised'
                  ? 'LLM-supervised tool routing · Design → validate → quote → finance'
                  : 'Design → validate → quote → finance handoff',
              style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
            ),
            const SizedBox(height: 12),
            ...List.generate(steps.length, (i) {
              final step = steps[i];
              final isLast = i == steps.length - 1;
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Column(
                    children: [
                      Container(
                        width: 30,
                        height: 30,
                        decoration: BoxDecoration(
                          color: AppTheme.successBg,
                          shape: BoxShape.circle,
                          border: Border.all(color: AppTheme.successFg.withOpacity(0.35)),
                        ),
                        child: Icon(_stepIcon(step), size: 16, color: AppTheme.successFg),
                      ),
                      if (!isLast)
                        Container(
                          width: 2,
                          height: 28,
                          color: AppTheme.borderColor,
                        ),
                    ],
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Padding(
                      padding: EdgeInsets.only(bottom: isLast ? 0 : 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _friendlyStepLabel(step),
                            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            _friendlyStepDetail(step),
                            style: TextStyle(color: Colors.grey.shade600, fontSize: 12, height: 1.3),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _quotedSolutionCard(Map<String, dynamic> quote, Map<String, dynamic> breakdown) {
    final currency = NumberFormat.currency(symbol: 'RM ', decimalDigits: 2);
    final items = (quote['items'] as List<dynamic>? ?? []).whereType<Map<String, dynamic>>().toList();
    final grand = (breakdown['grand_total_rm'] as num?)?.toDouble() ?? 0;
    final subtotal = (breakdown['subtotal_rm'] as num?)?.toDouble();
    final shipping = (breakdown['shipping_rm'] as num?)?.toDouble();
    final tax = (breakdown['tax_rm'] as num?)?.toDouble();
    final eta = breakdown['estimated_delivery_days'];
    final location = quote['location']?.toString() ?? _locationCtrl.text;

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: AppTheme.teal.withOpacity(0.35)),
      ),
      color: AppTheme.teal.withOpacity(0.04),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Quoted solution',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.successBg,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '#${quote['quote_id']}',
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.successFg),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Deliver to $location · ETA $eta days',
              style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
            ),
            const SizedBox(height: 14),
            ...items.map((m) {
              final price = (m['unit_price_rm'] as num?)?.toDouble() ?? 0;
              final qty = (m['quantity'] as num?)?.toInt() ?? 1;
              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.borderColor),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            m['product_name']?.toString() ?? 'Product',
                            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                          ),
                          if (qty > 1)
                            Text('Qty $qty', style: TextStyle(color: Colors.grey.shade600, fontSize: 11)),
                        ],
                      ),
                    ),
                    Text(currency.format(price), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                  ],
                ),
              );
            }),
            const Divider(height: 20),
            if (subtotal != null) _moneyRow('Subtotal', currency.format(subtotal)),
            if (shipping != null && shipping > 0) _moneyRow('Shipping', currency.format(shipping)),
            if (tax != null && tax > 0) _moneyRow('SST / tax', currency.format(tax)),
            const SizedBox(height: 6),
            _moneyRow('Grand total', currency.format(grand), bold: true),
          ],
        ),
      ),
    );
  }

  Widget _moneyRow(String label, String value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              fontWeight: bold ? FontWeight.w700 : FontWeight.w500,
              fontSize: bold ? 14 : 13,
              color: bold ? AppTheme.textPrimary : AppTheme.textSecondary,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontWeight: bold ? FontWeight.w800 : FontWeight.w600,
              fontSize: bold ? 16 : 13,
              color: bold ? AppTheme.teal : AppTheme.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _ragSyncCard(String ragAnswer) {
    return Card(
      elevation: 0,
      color: AppTheme.teal.withOpacity(0.06),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: AppTheme.teal.withOpacity(0.2)),
      ),
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
                  'BNPL financing advice${_ragMode != null ? " · $_ragMode" : ""}',
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                ),
              ],
            ),
            const SizedBox(height: 8),
            FormattedChatText(
              text: ragAnswer,
              style: TextStyle(color: Colors.grey.shade800, height: 1.45, fontSize: 13),
            ),
            if (widget.onOpenRagChat != null) ...[
              const SizedBox(height: 10),
              TextButton.icon(
                onPressed: widget.onOpenRagChat,
                icon: const Icon(Icons.chat_bubble_outline),
                label: const Text('Continue in BNPL Chat'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _quantBusinessValue(Map<String, dynamic> bv) {
    final cycle = (bv['quote_cycle_time_reduction_pct'] as num?)?.toDouble() ?? 0;
    final annualHours = (bv['annual_time_saved_hours'] as num?)?.toDouble() ?? 0;
    final annualRm = (bv['annual_cost_saved_rm'] as num?)?.toDouble() ?? 0;
    final monthlyQuotes = (bv['assumed_quotes_per_month'] as num?)?.toInt() ?? 0;
    final success = ((bv['success_rate'] as num?)?.toDouble() ?? 0) * 100.0;
    final budget = ((bv['within_budget_rate'] as num?)?.toDouble() ?? 0) * 100.0;
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.surfaceElevated,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Text(
        'Quantified value • ${cycle.toStringAsFixed(0)}% faster quote cycle · '
        '${success.toStringAsFixed(0)}% compatibility success · '
        '${budget.toStringAsFixed(0)}% within budget · '
        '${annualHours.toStringAsFixed(0)} hrs/year and RM ${annualRm.toStringAsFixed(0)} annual savings '
        '(assumes $monthlyQuotes quotes/month).',
        style: TextStyle(color: Colors.grey.shade700, fontSize: 12, height: 1.35),
      ),
    );
  }

  Widget _transcriptCard(Map<String, dynamic> parsed) {
    final confidence = ((parsed['confidence'] as num?)?.toDouble() ?? 0) * 100.0;
    final turns = (parsed['speaker_turns'] as num?)?.toInt() ?? 0;
    final evidence = (parsed['evidence'] as List<dynamic>? ?? [])
        .map((e) => e is Map ? '${e['field']}: ${e['match']}' : e.toString())
        .take(3)
        .join(' • ');
    return Card(
      color: AppTheme.peach.withOpacity(0.25),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Unstructured transcript parsed (${confidence.toStringAsFixed(0)}% confidence, $turns turns)',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
            ),
            if (evidence.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(evidence, style: TextStyle(color: Colors.grey.shade700, fontSize: 12)),
            ],
          ],
        ),
      ),
    );
  }
}
