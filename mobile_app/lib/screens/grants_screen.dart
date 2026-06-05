import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/gov_aid.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'application_tracker_screen.dart';
import 'grant_checklist_screen.dart';

class GrantsScreen extends StatefulWidget {
  const GrantsScreen({super.key});

  @override
  State<GrantsScreen> createState() => _GrantsScreenState();
}

class _GrantsScreenState extends State<GrantsScreen> {
  List<GovAid> all = [];
  bool grantsOnly = false;
  bool bumiOnly = false;
  bool loading = true;
  String? err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      err = null;
    });
    try {
      final list = await ApiService().fetchGovAid();
      setState(() => all = list);
    } catch (e) {
      setState(() => err = e.toString());
    } finally {
      setState(() => loading = false);
    }
  }

  Iterable<GovAid> get _filtered sync* {
    for (final g in all) {
      if (grantsOnly && g.aidType.toLowerCase() != 'grant') continue;
      if (bumiOnly && !g.requiresBumiputera) continue;
      yield g;
    }
  }

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(symbol: 'RM ', decimalDigits: 0);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Funding options',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textPrimary,
                    ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Step 4 — grants and loans matched to your profile.',
                style: TextStyle(color: AppTheme.textSecondary, height: 1.4, fontSize: 13),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              TextButton.icon(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(builder: (_) => const ApplicationTrackerScreen()),
                ),
                icon: const Icon(Icons.view_kanban_outlined, size: 18),
                label: const Text('Application Tracker'),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Wrap(
            spacing: 8,
            children: [
              FilterChip(
                avatar: Icon(
                  Icons.verified_rounded,
                  size: 16,
                  color: grantsOnly ? AppTheme.teal : Colors.grey.shade400,
                ),
                label: const Text('Grants only'),
                selected: grantsOnly,
                selectedColor: AppTheme.teal.withOpacity(0.12),
                checkmarkColor: AppTheme.teal,
                onSelected: (v) => setState(() => grantsOnly = v),
              ),
              FilterChip(
                avatar: Icon(
                  Icons.flag_rounded,
                  size: 16,
                  color: bumiOnly ? AppTheme.teal : Colors.grey.shade400,
                ),
                label: const Text('Bumiputera'),
                selected: bumiOnly,
                selectedColor: AppTheme.teal.withOpacity(0.12),
                checkmarkColor: AppTheme.teal,
                onSelected: (v) => setState(() => bumiOnly = v),
              ),
            ],
          ),
        ),
        Expanded(
          child: loading
              ? const Center(child: CircularProgressIndicator(color: AppTheme.teal))
              : err != null
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.cloud_off_rounded, size: 40, color: Colors.grey.shade400),
                          const SizedBox(height: 8),
                          Text(err!, style: TextStyle(color: Colors.grey.shade600)),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      color: AppTheme.teal,
                      onRefresh: _load,
                      child: ListView(
                        padding: const EdgeInsets.only(bottom: 24),
                        children: [
                          for (final g in _filtered) _card(context, g, currency),
                        ],
                      ),
                    ),
        ),
      ],
    );
  }

  Widget _card(BuildContext context, GovAid g, NumberFormat currency) {
    final isGrant = g.aidType.toLowerCase() == 'grant';
    return PremiumCard(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      borderColor: isGrant ? AppTheme.teal.withOpacity(0.4) : null,
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Accent bar for grants
          if (isGrant)
            Container(
              height: 3,
              decoration: const BoxDecoration(
                gradient: AppTheme.cardAccentGradient,
                borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            g.schemeName,
                            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                          ),
                          const SizedBox(height: 2),
                          Text(g.agency, style: TextStyle(color: Colors.grey.shade500, fontSize: 13)),
                        ],
                      ),
                    ),
                    if (isGrant)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          gradient: AppTheme.cardAccentGradient,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          'GRANT',
                          style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 14),
                _grid(g, currency),
                if (g.description != null) ...[
                  const SizedBox(height: 10),
                  Text(g.description!, style: TextStyle(fontSize: 13, color: Colors.grey.shade700, height: 1.4)),
                ],
                const SizedBox(height: 14),
                OutlinedButton.icon(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => GrantChecklistScreen(grantId: g.id, schemeName: g.schemeName),
                    ),
                  ),
                  icon: const Icon(Icons.checklist_rounded, size: 16),
                  label: const Text('Checklist'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    side: BorderSide(color: AppTheme.teal.withOpacity(0.3)),
                    foregroundColor: AppTheme.teal,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _grid(GovAid g, NumberFormat currency) {
    final maxAmt = g.maxAmountRm == null ? '—' : currency.format(g.maxAmountRm);
    final rate = g.interestRateLabel ?? '—';
    final tenure = g.tenureMonths == null ? '—' : '${g.tenureMonths} mo';
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Table(
        columnWidths: const {0: FlexColumnWidth(1), 1: FlexColumnWidth(1)},
        children: [
          TableRow(children: [_cell('MAX AMOUNT', maxAmt), _cell('INTEREST', rate)]),
          TableRow(children: [_cell('SPEED', g.approvalSpeedLabel), _cell('TENURE', tenure)]),
        ],
      ),
    );
  }

  Widget _cell(String label, String value) => Padding(
        padding: const EdgeInsets.all(6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: TextStyle(fontSize: 10, color: Colors.grey.shade400, fontWeight: FontWeight.w600, letterSpacing: 0.5),
            ),
            const SizedBox(height: 2),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
          ],
        ),
      );
}
