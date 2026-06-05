import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../providers/settings_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/active_profile_badge.dart';
import 'shell_screen.dart';

class ProfileQuizScreen extends StatefulWidget {
  const ProfileQuizScreen({super.key});

  @override
  State<ProfileQuizScreen> createState() => _ProfileQuizScreenState();
}

class _ProfileQuizScreenState extends State<ProfileQuizScreen> {
  int _step = 0;
  String _sector = 'F&B retail';
  double _revenue = 500000;
  int _employees = 5;
  bool _sst = false;
  double _reserveMonths = 2;
  bool _bumi = false;
  bool _tech = false;
  bool _busy = false;

  static const _sectors = [
    'F&B retail',
    'Agriculture wholesale',
    'IT services',
    'Manufacturing',
    'E-commerce',
  ];

  Future<void> _finish() async {
    setState(() => _busy = true);
    try {
      final smeId = context.read<SessionProvider>().smeId;
      await ApiService().onboardProfile(
        smeId: smeId,
        sector: _sector,
        revenueRm: _revenue,
        employeeCount: _employees,
        sstRegistered: _sst,
        cashReserveMonths: _reserveMonths,
        bumiputera: _bumi,
        techFocus: _tech,
      );
      await context.read<SettingsProvider>().setOnboarded();
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(builder: (_) => const ShellScreen()),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              LinearProgressIndicator(value: (_step + 1) / 5, color: AppTheme.teal),
              const SizedBox(height: 24),
              Text(
                'Quick SME profile (${_step + 1}/5)',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                'We sync this to your active business profile for dashboard and AI.',
                style: TextStyle(color: Colors.grey.shade600),
              ),
              const SizedBox(height: 12),
              const ActiveProfileBadge(dense: true),
              const SizedBox(height: 12),
              Expanded(child: _stepBody()),
              FilledButton(
                onPressed: _busy
                    ? null
                    : () {
                        if (_step < 4) {
                          setState(() => _step++);
                        } else {
                          _finish();
                        }
                      },
                style: FilledButton.styleFrom(backgroundColor: AppTheme.teal, padding: const EdgeInsets.symmetric(vertical: 14)),
                child: Text(_step < 4 ? 'Next' : (_busy ? 'Saving…' : 'Go to dashboard')),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _stepBody() {
    switch (_step) {
      case 0:
        return DropdownButtonFormField<String>(
          value: _sector,
          decoration: const InputDecoration(labelText: 'Sector'),
          items: _sectors.map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
          onChanged: (v) => setState(() => _sector = v ?? _sector),
        );
      case 1:
        return Column(
          children: [
            Text('Annual revenue: RM ${_revenue.toStringAsFixed(0)}'),
            Slider(
              value: _revenue,
              min: 100000,
              max: 5000000,
              divisions: 20,
              label: 'RM ${_revenue.toStringAsFixed(0)}',
              onChanged: (v) => setState(() => _revenue = v),
            ),
          ],
        );
      case 2:
        return Column(
          children: [
            Text('Employees: $_employees'),
            Slider(
              value: _employees.toDouble(),
              min: 1,
              max: 100,
              divisions: 99,
              onChanged: (v) => setState(() => _employees = v.round()),
            ),
            SwitchListTile(
              title: const Text('SST registered'),
              value: _sst,
              onChanged: (v) => setState(() => _sst = v),
            ),
          ],
        );
      case 3:
        return Column(
          children: [
            Text('Cash reserves: ${_reserveMonths.toStringAsFixed(1)} months'),
            Slider(
              value: _reserveMonths,
              min: 0,
              max: 12,
              divisions: 24,
              onChanged: (v) => setState(() => _reserveMonths = v),
            ),
            const Text(
              'BNM/SME Corp guidance: aim for 3–6 months of obligations covered.',
              style: TextStyle(fontSize: 12),
            ),
          ],
        );
      default:
        return Column(
          children: [
            SwitchListTile(title: const Text('Bumiputera-owned'), value: _bumi, onChanged: (v) => setState(() => _bumi = v)),
            SwitchListTile(title: const Text('Tech / digital focus'), value: _tech, onChanged: (v) => setState(() => _tech = v)),
          ],
        );
    }
  }
}
