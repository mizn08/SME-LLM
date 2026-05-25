import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/guided_advisory.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class GuidedAdvisoryScreen extends StatefulWidget {
  const GuidedAdvisoryScreen({super.key});

  @override
  State<GuidedAdvisoryScreen> createState() => _GuidedAdvisoryScreenState();
}

class _GuidedAdvisoryScreenState extends State<GuidedAdvisoryScreen> {
  int _step = 0;
  String _businessType = 'Retail';
  String _goal = 'expand';
  double _amount = 50000;
  int _timeline = 6;
  String _constraint = 'cash';
  GuidedAdvisoryResponse? _result;
  bool _loading = false;

  Future<void> _submit() async {
    setState(() => _loading = true);
    try {
      final sid = context.read<SessionProvider>().smeId;
      _result = await ApiService().guidedAdvisory(
        smeId: sid,
        businessType: _businessType,
        goal: _goal,
        amountRm: _amount,
        timelineMonths: _timeline,
        mainConstraint: _constraint,
      );
      if (mounted) setState(() => _step = 5);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_step == 5 && _result != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Recommendation'), backgroundColor: AppTheme.teal),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(_result!.recommendation, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 12),
            Text('Top product: ${_result!.topProduct}'),
            for (final r in _result!.reasoning) ListTile(dense: true, leading: const Icon(Icons.check, size: 16), title: Text(r, style: const TextStyle(fontSize: 13))),
            const Divider(),
            const Text('Next steps', style: TextStyle(fontWeight: FontWeight.w600)),
            for (final s in _result!.nextSteps) ListTile(dense: true, title: Text(s, style: const TextStyle(fontSize: 13))),
          ],
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text('Guided Advisory (${_step + 1}/5)'), backgroundColor: AppTheme.teal),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            LinearProgressIndicator(value: (_step + 1) / 5),
            const SizedBox(height: 24),
            if (_step == 0)
              DropdownButtonFormField<String>(
                value: _businessType,
                items: ['Retail', 'F&B', 'Agriculture', 'Technology']
                    .map((e) => DropdownMenuItem(value: e, child: Text(e)))
                    .toList(),
                onChanged: (v) => setState(() => _businessType = v!),
                decoration: const InputDecoration(labelText: 'Business type'),
              ),
            if (_step == 1)
              DropdownButtonFormField<String>(
                value: _goal,
                items: const [
                  DropdownMenuItem(value: 'expand', child: Text('Expand')),
                  DropdownMenuItem(value: 'survive', child: Text('Survive cash crunch')),
                  DropdownMenuItem(value: 'digitalise', child: Text('Digitalise')),
                  DropdownMenuItem(value: 'export', child: Text('Export')),
                ],
                onChanged: (v) => setState(() => _goal = v!),
                decoration: const InputDecoration(labelText: 'Primary goal'),
              ),
            if (_step == 2) ...[
              Text('Amount: RM ${_amount.toStringAsFixed(0)}'),
              Slider(value: _amount, min: 5000, max: 200000, divisions: 39, onChanged: (v) => setState(() => _amount = v)),
            ],
            if (_step == 3) ...[
              Text('Timeline: $_timeline months'),
              Slider(value: _timeline.toDouble(), min: 1, max: 24, divisions: 23, onChanged: (v) => setState(() => _timeline = v.toInt())),
            ],
            if (_step == 4)
              DropdownButtonFormField<String>(
                value: _constraint,
                items: const [
                  DropdownMenuItem(value: 'cash', child: Text('Cash flow')),
                  DropdownMenuItem(value: 'collateral', child: Text('Collateral')),
                  DropdownMenuItem(value: 'time', child: Text('Time')),
                  DropdownMenuItem(value: 'eligibility', child: Text('Eligibility')),
                ],
                onChanged: (v) => setState(() => _constraint = v!),
                decoration: const InputDecoration(labelText: 'Main constraint'),
              ),
            const Spacer(),
            FilledButton(
              onPressed: _loading
                  ? null
                  : () {
                      if (_step < 4) {
                        setState(() => _step++);
                      } else {
                        _submit();
                      }
                    },
              child: Text(_step < 4 ? 'Next' : (_loading ? '...' : 'Get recommendation')),
            ),
          ],
        ),
      ),
    );
  }
}
