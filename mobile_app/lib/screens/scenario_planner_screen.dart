import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class ScenarioPlannerScreen extends StatefulWidget {
  const ScenarioPlannerScreen({super.key});

  @override
  State<ScenarioPlannerScreen> createState() => _ScenarioPlannerScreenState();
}

class _ScenarioPlannerScreenState extends State<ScenarioPlannerScreen> {
  double _extraPayroll = 0;
  double _loanRm = 0;
  double _purchaseRm = 50000;
  double? _runwayBefore;
  double? _runwayAfter;
  int? _healthBefore;
  int? _healthAfter;
  bool _busy = false;

  Future<void> _simulate() async {
    setState(() => _busy = true);
    try {
      final sid = context.read<SessionProvider>().smeId;
      final dash = await ApiService().fetchDashboard(sid, useCacheOnFail: false);
      final beforeRunway = dash.runwayDaysEst ?? dash.daysCashOnHand;
      final beforeHealth = dash.healthScore;
      if (beforeHealth == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Load Health tab first — readiness score comes from the server.')),
          );
        }
        return;
      }

      final dailyBurn = (dash.burnRateMonthlyRm / 30).clamp(1.0, 999999.0);
      final impact = _extraPayroll * 3 + _loanRm * 0.02 * 12;
      final afterRunway = (beforeRunway - impact / dailyBurn).clamp(0.0, 9999.0);
      final runwayFactor = beforeRunway > 0 ? (afterRunway / beforeRunway).clamp(0.0, 1.0) : 0.0;
      final afterHealth = (beforeHealth * runwayFactor).round().clamp(0, 100);

      if (_purchaseRm > 0) {
        await ApiService().predict(
          smeId: sid,
          purchaseAmount: _purchaseRm,
          purchaseCategory: 'Equipment',
        );
      }

      setState(() {
        _runwayBefore = beforeRunway;
        _runwayAfter = afterRunway;
        _healthBefore = beforeHealth;
        _healthAfter = afterHealth;
      });
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('What-if planner')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Illustrative what-if: runway and score scale from your live Health tab KPIs.',
            style: TextStyle(height: 1.4),
          ),
          const SizedBox(height: 16),
          Text('Hire / payroll increase (monthly): RM ${_extraPayroll.toStringAsFixed(0)}'),
          Slider(value: _extraPayroll, max: 20000, divisions: 40, onChanged: (v) => setState(() => _extraPayroll = v)),
          Text('New loan principal: RM ${_loanRm.toStringAsFixed(0)}'),
          Slider(value: _loanRm, max: 200000, divisions: 40, onChanged: (v) => setState(() => _loanRm = v)),
          Text('BNPL / equipment purchase: RM ${_purchaseRm.toStringAsFixed(0)}'),
          Slider(value: _purchaseRm, max: 150000, divisions: 30, onChanged: (v) => setState(() => _purchaseRm = v)),
          FilledButton(
            onPressed: _busy ? null : _simulate,
            style: FilledButton.styleFrom(backgroundColor: AppTheme.teal),
            child: Text(_busy ? 'Calculating…' : 'Run scenario'),
          ),
          if (_runwayBefore != null) ...[
            const SizedBox(height: 24),
            _compareTile('Runway (days)', _runwayBefore!, _runwayAfter!),
            _compareTile('Readiness score', _healthBefore!.toDouble(), _healthAfter!.toDouble()),
          ],
        ],
      ),
    );
  }

  Widget _compareTile(String label, double before, double after) {
    final delta = after - before;
    return Card(
      child: ListTile(
        title: Text(label),
        subtitle: Text('Before: ${before.toStringAsFixed(0)} → After: ${after.toStringAsFixed(0)} (${delta >= 0 ? '+' : ''}${delta.toStringAsFixed(0)})'),
        trailing: Icon(delta >= 0 ? Icons.trending_up : Icons.trending_down, color: delta >= 0 ? Colors.green : Colors.red),
      ),
    );
  }
}
