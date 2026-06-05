import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class InsightsScreen extends StatefulWidget {
  const InsightsScreen({super.key});

  @override
  State<InsightsScreen> createState() => _InsightsScreenState();
}

class _InsightsScreenState extends State<InsightsScreen> {
  final _api = ApiService();
  Map<String, dynamic>? _insights;
  Map<String, dynamic>? _bandit;
  bool _busy = false;
  String? _err;
  String? _ocrPreview;
  List<Map<String, dynamic>> _ocrRows = const [];
  bool _hasScanned = false;
  String? _ocrHint;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final sid = context.read<SessionProvider>().smeId;
      final ins = await _api.fetchInsights(sid);
      final bandit = await _api.fetchBanditStats();
      if (!mounted) return;
      setState(() {
        _insights = ins;
        _bandit = bandit;
      });
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickInvoice() async {
    final pick = await FilePicker.platform.pickFiles(
      type: FileType.any,
      withData: true,
      allowMultiple: false,
    );
    if (pick == null || pick.files.isEmpty) return;
    final file = pick.files.first;
    final bytes = file.bytes;
    if (bytes == null) return;
    setState(() {
      _busy = true;
      _err = null;
      _ocrPreview = null;
      _ocrRows = const [];
      _hasScanned = true;
      _ocrHint = null;
    });
    try {
      final sid = context.read<SessionProvider>().smeId;
      final res = await _api.uploadInvoice(
        smeId: sid,
        bytes: bytes,
        fileName: file.name.isNotEmpty ? file.name : 'upload',
      );
      if (!mounted) return;
      final hint = res['hint'] as String?;
      final warnings = (res['warnings'] as List<dynamic>? ?? []).join('; ');
      final preview = res['csv_preview'] as String? ?? '';
      final quality = res['quality_score'];
      final parsedRows = ((res['ocr'] as Map<String, dynamic>?)?['parsed_rows'] as List<dynamic>? ?? [])
          .whereType<Map<String, dynamic>>()
          .toList();
      final ocrText = (res['ocr'] as Map<String, dynamic>?)?['text'] as String? ?? '';
      final textPreview = ocrText.trim().length > 1500 ? '${ocrText.trim().substring(0, 1500)}…' : ocrText.trim();
      final hasData = parsedRows.isNotEmpty || preview.trim().isNotEmpty;
      setState(() {
        _ocrPreview = preview.trim().isNotEmpty ? preview : null;
        _ocrRows = parsedRows;
        _ocrHint = hint;
        _err = hasData
            ? null
            : [
                if (hint != null) hint,
                if (warnings.isNotEmpty) warnings,
                if (quality != null) 'Quality score: $quality (need clearer file if low)',
                if (!hasData && preview.isEmpty && textPreview.isNotEmpty)
                  'Raw OCR text was unreadable — not shown to avoid garbage output.',
                if (hint == null && warnings.isEmpty && textPreview.isEmpty)
                  'No usable data extracted from this file. Try clear JPG/PNG or CSV.',
              ].where((s) => s.isNotEmpty).join('\n\n');
      });
      if (hasData) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(hint ?? 'Extracted ${preview.split('\n').length - 1} row(s) — review CSV below.')),
        );
      }
    } catch (e) {
      if (mounted) setState(() => _err = ApiService.friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Insights (v3)'),
        backgroundColor: AppTheme.teal,
        foregroundColor: Colors.white,
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      body: _busy && _insights == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_err != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      _err!,
                      style: TextStyle(color: Colors.orange.shade900, fontSize: 12, height: 1.35),
                    ),
                  ),
                _section(
                  'Unsupervised cluster',
                  _insights?['cluster'] != null
                      ? '${_insights!['cluster']['cluster_label']}\n(cluster ${_insights!['cluster']['cluster_id']})'
                      : 'Run after SME data is loaded',
                ),
                _section(
                  'Anomaly detection',
                  _formatAnomalies(_insights?['anomalies']),
                ),
                _section(
                  'Multi-armed bandit (UCB)',
                  _formatBandit(_bandit),
                ),
                const SizedBox(height: 8),
                FilledButton.icon(
                  onPressed: _pickInvoice,
                  icon: const Icon(Icons.document_scanner_outlined),
                  label: const Text('Scan invoice (OCR)'),
                  style: FilledButton.styleFrom(backgroundColor: AppTheme.teal),
                ),
                if (_hasScanned) ...[
                  const SizedBox(height: 12),
                  _ocrTableSection(),
                ],
              ],
            ),
    );
  }

  String _formatAnomalies(dynamic block) {
    if (block == null) return '—';
    final list = block['anomalies'] as List<dynamic>? ?? [];
    if (list.isEmpty) return block['message'] as String? ?? 'No anomalies flagged';
    return list
        .take(5)
        .map((a) => '${a['txn_date']} ${a['category']} RM ${a['amount_rm']}')
        .join('\n');
  }

  String _formatBandit(Map<String, dynamic>? b) {
    if (b == null) return '—';
    final sug = b['suggestion'] as Map<String, dynamic>?;
    final arms = b['arms'] as List<dynamic>? ?? [];
    final lines = <String>[
      if (sug != null) 'Explore arm: ${sug['suggested_arm']}',
      ...arms.map((a) => '${a['arm']}: ${a['pulls']} pulls, avg ${(a['avg_reward'] as num).toStringAsFixed(2)}'),
    ];
    return lines.join('\n');
  }

  Widget _section(String title, String body) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Text(body, style: TextStyle(color: Colors.grey.shade800, height: 1.4, fontSize: 13)),
          ],
        ),
      ),
    );
  }

  Widget _ocrTableSection() {
    final currency = NumberFormat.currency(symbol: 'RM ', decimalDigits: 2);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('OCR extracted rows', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            if (_ocrRows.isEmpty)
              Text(_ocrHint ?? 'No usable rows extracted.')
            else
              ..._ocrRows.take(10).map(
                (r) => Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade50,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.grey.shade200),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              (r['description']?.toString().trim().isNotEmpty == true)
                                  ? r['description'].toString()
                                  : 'Invoice item',
                              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              r['txn_date']?.toString() ?? 'No date',
                              style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        currency.format((r['amount_rm'] as num?)?.toDouble() ?? 0),
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                      ),
                    ],
                  ),
                ),
              ),
            if (_ocrPreview != null && _ocrPreview!.isNotEmpty) ...[
              const SizedBox(height: 8),
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text('Show raw CSV preview', style: TextStyle(fontSize: 12)),
                children: [
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade50,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      _ocrPreview!,
                      style: TextStyle(color: Colors.grey.shade700, height: 1.35, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
