import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/kpi_card.dart';

/// Autonomous Sales Engineer — unstructured brief, agentic quote, business value metrics.
class SalesEngineerScreen extends StatefulWidget {
  const SalesEngineerScreen({super.key});

  @override
  State<SalesEngineerScreen> createState() => _SalesEngineerScreenState();
}

class _SalesEngineerScreenState extends State<SalesEngineerScreen> {
  final _briefCtrl = TextEditingController(
    text:
        'Minimalist home office for a 10x10ft room under RM5000 in Kuala Lumpur. No drilling.',
  );
  final _locationCtrl = TextEditingController(text: 'Kuala Lumpur');
  bool _busy = false;
  String? _err;
  Map<String, dynamic>? _result;
  Map<String, dynamic>? _metrics;

  @override
  void dispose() {
    _briefCtrl.dispose();
    _locationCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadMetrics() async {
    final sid = context.read<SessionProvider>().smeId;
    final m = await ApiService().fetchBusinessValueMetrics(smeId: sid);
    if (mounted) setState(() => _metrics = m);
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
      final parsed = await ApiService().parseRequirements(
        bytes: res.files.single.bytes!,
        fileName: res.files.single.name,
      );
      final budget = parsed['budget'];
      final style = parsed['style'];
      final room = parsed['room_size'];
      final loc = parsed['location'];
      _briefCtrl.text =
          '${style ?? "Setup"} ${room ?? ""} budget RM ${budget ?? "?"} at $loc. ${(parsed["explicit_constraints"] as List?)?.join(", ") ?? ""}';
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
    });
    try {
      final sid = context.read<SessionProvider>().smeId;
      final out = await ApiService().runSalesAgent(
        smeId: sid,
        briefText: _briefCtrl.text.trim(),
        location: _locationCtrl.text.trim(),
      );
      await _loadMetrics();
      if (mounted) setState(() => _result = out);
    } catch (e) {
      if (mounted) setState(() => _err = ApiService.friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadMetrics());
  }

  @override
  Widget build(BuildContext context) {
    final quote = _result?['quote'] as Map<String, dynamic>?;
    final breakdown = quote?['breakdown'] as Map<String, dynamic>?;
    final bv = _result?['business_value'] as Map<String, dynamic>? ?? _metrics;
    final trace = (_result?['agent_trace'] as List<dynamic>? ?? []);

    return Scaffold(
      appBar: AppBar(title: const Text('Autonomous Sales Engineer')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (bv != null) ...[
            Text('Business value', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: KPICard(
                    title: 'Time saved / quote',
                    value: '${bv['time_saved_minutes_per_quote'] ?? 43} min',
                    leading: const Icon(Icons.schedule, size: 20, color: AppTheme.teal),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: KPICard(
                    title: 'Cost saved (total)',
                    value: 'RM ${bv['cost_saved_rm'] ?? 0}',
                    leading: const Icon(Icons.savings_outlined, size: 20, color: AppTheme.teal),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: KPICard(
                    title: 'Success rate',
                    value: '${((bv['success_rate'] as num? ?? 0) * 100).toStringAsFixed(0)}%',
                    leading: const Icon(Icons.verified_outlined, size: 20, color: AppTheme.teal),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: KPICard(
                    title: 'Quotes generated',
                    value: '${bv['quotes_generated'] ?? 0}',
                    leading: const Icon(Icons.receipt_long, size: 20, color: AppTheme.teal),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
          ],
          TextField(
            controller: _briefCtrl,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Client brief (free text)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _locationCtrl,
            decoration: const InputDecoration(
              labelText: 'Location',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton.icon(
                onPressed: _busy ? null : _pickBriefFile,
                icon: const Icon(Icons.upload_file),
                label: const Text('Upload PDF / TXT / DOCX'),
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
                label: Text(_busy ? 'Agent running…' : 'Run agentic quote'),
              ),
            ],
          ),
          if (_err != null) ...[
            const SizedBox(height: 12),
            Text(_err!, style: const TextStyle(color: Colors.red)),
          ],
          if (_result != null) ...[
            const SizedBox(height: 20),
            Text('Agent trace', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 6),
            ...trace.map(
              (t) => ListTile(
                dense: true,
                title: Text('${(t as Map)['tool'] ?? (t)['step']}'),
                subtitle: Text('${t['detail'] ?? ''}'),
              ),
            ),
            const SizedBox(height: 12),
            Text('Reasoning summary', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 6),
            Text(_result!['reasoning_summary']?.toString() ?? ''),
          ],
          if (quote != null && breakdown != null) ...[
            const SizedBox(height: 20),
            Text('Final quote #${quote['quote_id']}', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            ...(quote['items'] as List<dynamic>? ?? []).map((item) {
              final m = item as Map<String, dynamic>;
              return ListTile(
                title: Text(m['product_name']?.toString() ?? ''),
                subtitle: Text(m['compatibility_note']?.toString() ?? ''),
                trailing: Text('RM ${m['unit_price_rm']}'),
              );
            }),
            const Divider(),
            _line('Subtotal', breakdown['subtotal_rm']),
            _line('Shipping', breakdown['shipping_rm']),
            _line('Tax', breakdown['tax_rm']),
            _line('Discount', breakdown['discount_rm']),
            _line('Grand total', breakdown['grand_total_rm'], bold: true),
            _line('ETA (days)', breakdown['estimated_delivery_days']),
          ],
        ],
      ),
    );
  }

  Widget _line(String label, dynamic value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(fontWeight: bold ? FontWeight.w700 : FontWeight.w400)),
          Text(
            value is num && label.contains('ETA') ? '$value' : 'RM $value',
            style: TextStyle(fontWeight: bold ? FontWeight.w700 : FontWeight.w500),
          ),
        ],
      ),
    );
  }
}
