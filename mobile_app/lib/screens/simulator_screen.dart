import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';

import '../providers/recommendation_provider.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../services/pdf_report_service.dart' show PdfReportService, writePdfBytes;
import '../theme/app_theme.dart';
import '../widgets/lead_score_meter.dart';
import '../widgets/recommendation_result.dart';
import 'bnpl_repayment_screen.dart';

class SimulatorScreen extends StatefulWidget {
  const SimulatorScreen({super.key});

  @override
  State<SimulatorScreen> createState() => _SimulatorScreenState();
}

class _SimulatorScreenState extends State<SimulatorScreen> {
  final _amountCtrl = TextEditingController(text: '50000');
  String _category = 'Equipment';
  String _bnplChoice = 'Auto-select';
  bool _busy = false;
  bool _islamicOnly = false;
  String? _err;

  static const _categories = [
    'Equipment',
    'Digital / Software',
    'Supplies',
    'Marketing',
    'Logistics',
    'Utilities',
    'Agri inputs',
  ];

  static const _bnplPlans = <MapEntry<String, String?>>[
    MapEntry('Auto-select', null),
    MapEntry('Atome Pay in 3', 'Atome Pay in 3'),
    MapEntry('Grab PayLater 4-month', 'Grab PayLater 4-month'),
    MapEntry('Shopee SPayLater 12-month', 'Shopee SPayLater 12-month'),
  ];

  @override
  void dispose() {
    _amountCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final amt = double.tryParse(_amountCtrl.text.replaceAll(',', '')) ?? 0;
    if (amt <= 0) {
      setState(() => _err = 'Enter a valid purchase amount.');
      return;
    }
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final sid = context.read<SessionProvider>().smeId;
      String? selectedBnpl;
      for (final e in _bnplPlans) {
        if (e.key == _bnplChoice) {
          selectedBnpl = e.value;
          break;
        }
      }
      final res = await ApiService().predict(
        smeId: sid,
        purchaseAmount: amt,
        purchaseCategory: _category,
        selectedBnplPlan: selectedBnpl,
      );
      if (!mounted) return;
      context.read<RecommendationProvider>().setResult(
            res,
            purchaseAmount: amt,
            purchaseCategory: _category,
          );
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (ctx) => Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: DraggableScrollableSheet(
            expand: false,
            initialChildSize: 0.75,
            maxChildSize: 0.95,
            minChildSize: 0.45,
            builder: (_, scroll) => ListView(
              controller: scroll,
              children: [
                // Handle
                Center(
                  child: Container(
                    margin: const EdgeInsets.only(top: 12, bottom: 4),
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                RecommendationResultCard(result: res),
                if (res.leadScores.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Column(
                      children: [
                        const Text('Product match scores', style: TextStyle(fontWeight: FontWeight.w600)),
                        for (final s in res.leadScores)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 6),
                            child: LeadScoreMeter(item: s),
                          ),
                      ],
                    ),
                  ),
                ShapFactorsList(items: res.shapValues),
                if (res.banditSuggestedArm != null || res.rlSuggestedAction != null)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Text(
                      'Bandit explore: ${res.banditSuggestedArm ?? "—"} · RL: ${res.rlSuggestedAction ?? "—"}',
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                    ),
                  ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () async {
                            final sid = context.read<SessionProvider>().smeId;
                            await ApiService().banditFeedback(
                              smeId: sid,
                              arm: res.recommendationType,
                              accepted: true,
                              predictionId: res.predictionId,
                            );
                            if (ctx.mounted) Navigator.pop(ctx);
                          },
                          icon: const Icon(Icons.thumb_up_outlined, size: 18),
                          label: const Text('Helpful'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () async {
                            final sid = context.read<SessionProvider>().smeId;
                            await ApiService().banditFeedback(
                              smeId: sid,
                              arm: res.recommendationType,
                              accepted: false,
                              predictionId: res.predictionId,
                            );
                            if (ctx.mounted) Navigator.pop(ctx);
                          },
                          icon: const Icon(Icons.thumb_down_outlined, size: 18),
                          label: const Text('Not helpful'),
                        ),
                      ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    children: [
                      TextButton.icon(
                        onPressed: () async {
                          final bytes = await PdfReportService.buildRecommendationPdfBytes(res, 'SME');
                          if (kIsWeb) {
                            await Share.shareXFiles([
                              XFile.fromData(bytes, name: 'sme_advisor_report.pdf', mimeType: 'application/pdf'),
                            ], text: 'SME Advisor report');
                          } else {
                            final file = await writePdfBytes(bytes, 'sme_advisor_report.pdf');
                            await Share.shareXFiles([XFile(file.path)], text: 'SME Advisor report');
                          }
                        },
                        icon: const Icon(Icons.share_rounded, size: 18),
                        label: const Text('Share'),
                      ),
                      TextButton.icon(
                        onPressed: () async {
                          final bytes = await PdfReportService.buildRecommendationPdfBytes(res, 'SME');
                          if (kIsWeb) {
                            await Share.shareXFiles([
                              XFile.fromData(bytes, name: 'sme_advisor_report.pdf', mimeType: 'application/pdf'),
                            ]);
                          } else {
                            await writePdfBytes(bytes, 'sme_advisor_report.pdf');
                          }
                          if (ctx.mounted) {
                            ScaffoldMessenger.of(ctx).showSnackBar(
                              const SnackBar(content: Text('PDF ready')),
                            );
                          }
                        },
                        icon: const Icon(Icons.picture_as_pdf_outlined, size: 18),
                        label: const Text('PDF'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      );
    } catch (e) {
      setState(() => _err = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'BNPL Purchase Simulator',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            'Model the impact of your next major business purchase.',
            style: TextStyle(color: Colors.grey.shade600, height: 1.4),
          ),
          const SizedBox(height: 20),

          // ── Form card ──
          PremiumCard(
            margin: EdgeInsets.zero,
            padding: EdgeInsets.zero,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Accent bar
                Container(
                  height: 4,
                  decoration: const BoxDecoration(
                    gradient: AppTheme.cardAccentGradient,
                    borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextField(
                        controller: _amountCtrl,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: const InputDecoration(
                          labelText: 'Purchase amount',
                          prefixText: 'RM ',
                          helperText: 'Total invoice value before taxes.',
                        ),
                      ),
                      const SizedBox(height: 16),
                      DropdownButtonFormField<String>(
                        value: _category,
                        decoration: const InputDecoration(labelText: 'Expense category'),
                        items: _categories
                            .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                            .toList(),
                        onChanged: (v) => setState(() => _category = v ?? _category),
                      ),
                      const SizedBox(height: 16),
                      DropdownButtonFormField<String>(
                        value: _bnplChoice,
                        decoration: const InputDecoration(
                          labelText: 'Preferred BNPL plan (optional)',
                          helperText: 'Auto-select picks the lowest estimated cost.',
                        ),
                        items: _bnplPlans
                            .map((e) => DropdownMenuItem(value: e.key, child: Text(e.key)))
                            .toList(),
                        onChanged: (v) => setState(() => _bnplChoice = v ?? _bnplChoice),
                      ),
                      const SizedBox(height: 8),
                      SwitchListTile(
                        title: const Text('Islamic finance only'),
                        subtitle: const Text('Prefer Shariah-compliant lenders in comparisons'),
                        value: _islamicOnly,
                        onChanged: (v) => setState(() => _islamicOnly = v),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(builder: (_) => const BnplRepaymentScreen()),
                        ),
                        icon: const Icon(Icons.calendar_month_outlined),
                        label: const Text('BNPL Repayment Simulator'),
                      ),
                      const SizedBox(height: 12),

                      // AI info banner
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [AppTheme.teal.withOpacity(0.06), AppTheme.tealLight.withOpacity(0.04)],
                          ),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppTheme.teal.withOpacity(0.15)),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(6),
                              decoration: BoxDecoration(
                                color: AppTheme.teal.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Icon(Icons.auto_awesome_rounded, color: AppTheme.teal, size: 18),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                'AI engine analyses this purchase against your historical cash flow, limits, and market conditions.',
                                style: TextStyle(color: Colors.grey.shade700, fontSize: 13, height: 1.4),
                              ),
                            ),
                          ],
                        ),
                      ),

                      // Error
                      if (_err != null) ...[
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.red.shade50,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(_err!, style: TextStyle(color: Colors.red.shade700, fontSize: 13)),
                        ),
                      ],

                      const SizedBox(height: 20),
                      FilledButton.icon(
                        onPressed: _busy ? null : _submit,
                        icon: _busy
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              )
                            : const Icon(Icons.lightbulb_rounded),
                        label: Text(_busy ? 'Calculating…' : 'Calculate AI Recommendation'),
                        style: FilledButton.styleFrom(
                          backgroundColor: AppTheme.tealDark,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
