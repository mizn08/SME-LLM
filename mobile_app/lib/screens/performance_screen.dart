import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/dashboard.dart';
import '../models/prediction.dart';
import '../models/spending_category.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/recommendation_result.dart';

class PerformanceScreen extends StatefulWidget {
  const PerformanceScreen({super.key});

  @override
  State<PerformanceScreen> createState() => _PerformanceScreenState();
}

class _PerformanceScreenState extends State<PerformanceScreen> {
  DashboardData? dashboard;
  SpendingCategoryResponse? spending;
  List<PredictionHistoryItem> history = [];
  Map<String, dynamic>? trainingMetrics;
  String? err;
  bool loading = true;
  bool _showTrainingBenchmark = false;

  final _currency = NumberFormat.currency(symbol: 'RM ', decimalDigits: 0);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    if (!mounted) return;
    final sid = context.read<SessionProvider>().smeId;
    setState(() {
      loading = true;
      err = null;
    });
    try {
      final api = ApiService();
      final results = await Future.wait([
        api.fetchDashboard(sid, useCacheOnFail: false),
        api.fetchSpendingCategories(sid),
        api.fetchHistory(sid),
        api.fetchModelMetrics(),
      ]);
      setState(() {
        dashboard = results[0] as DashboardData;
        spending = results[1] as SpendingCategoryResponse;
        history = results[2] as List<PredictionHistoryItem>;
        trainingMetrics = results[3] as Map<String, dynamic>;
      });
    } catch (e) {
      setState(() => err = e.toString());
    } finally {
      setState(() => loading = false);
    }
  }

  Future<void> _openDetail(int id) async {
    try {
      final raw = await ApiService().fetchPredictionDetail(id);
      if (!mounted) return;
      final shap = (raw['shap_values'] as List<dynamic>? ?? [])
          .map((e) => ShapItem.fromJson(e as Map<String, dynamic>))
          .toList();
      await showDialog<void>(
        context: context,
        builder: (ctx) => Dialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 500),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      raw['product_name'] as String? ?? 'Prediction',
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
                    ),
                    const SizedBox(height: 12),
                    Text(raw['explanation'] as String? ?? '', style: const TextStyle(height: 1.5)),
                    const SizedBox(height: 16),
                    ShapFactorsList(items: shap),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.brandBlue));
    }
    if (err != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(err!, textAlign: TextAlign.center),
        ),
      );
    }

    final d = dashboard!;
    final spend = spending;
    final txnCount = d.transactionCount;
    final hasData = txnCount > 0;

    return RefreshIndicator(
      color: AppTheme.brandBlue,
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Decision history',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Live numbers from your uploaded transactions — updates when you import or refresh.',
            style: TextStyle(color: AppTheme.textSecondary, height: 1.4),
          ),
          const SizedBox(height: 16),

          if (!hasData)
            PremiumCard(
              child: Row(
                children: [
                  Icon(Icons.upload_file_rounded, color: AppTheme.goldAccent, size: 22),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'No transactions loaded yet. Upload files on Home → Upload, then pull to refresh here.',
                      style: TextStyle(color: AppTheme.textSecondary, height: 1.4),
                    ),
                  ),
                ],
              ),
            )
          else ...[
            PremiumCard(
              gradient: AppTheme.primaryGradient,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'YOUR READINESS SCORE',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1,
                      color: Colors.white.withOpacity(0.8),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        '${d.healthScore ?? 0}',
                        style: const TextStyle(
                          fontSize: 44,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          height: 1,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text(
                          '/ 100 · Grade ${d.healthGrade ?? '—'}',
                          style: TextStyle(color: Colors.white.withOpacity(0.85), fontSize: 14),
                        ),
                      ),
                    ],
                  ),
                  Text(
                    d.healthLabel ?? '',
                    style: TextStyle(color: AppTheme.premiumGold, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _StatCard(
                    label: 'Transactions loaded',
                    value: '$txnCount',
                    hint: 'From your imports',
                    icon: Icons.receipt_long_rounded,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _StatCard(
                    label: '90-day net cash',
                    value: _currency.format(d.netOperatingCashRm),
                    hint: 'Operating window',
                    icon: Icons.account_balance_wallet_rounded,
                  ),
                ),
              ],
            ),
            Row(
              children: [
                Expanded(
                  child: _StatCard(
                    label: 'Monthly burn',
                    value: _currency.format(d.burnRateMonthlyRm),
                    hint: 'Avg expenses',
                    icon: Icons.trending_down_rounded,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _StatCard(
                    label: 'Runway',
                    value: '${(d.runwayDaysEst ?? d.daysCashOnHand).toStringAsFixed(0)} days',
                    hint: 'Estimated',
                    icon: Icons.schedule_rounded,
                  ),
                ),
              ],
            ),
            if (spend != null && spend.categories.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(
                'Top spending (your data)',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              PremiumCard(
                child: Column(
                  children: [
                    for (final c in spend.categories.take(6))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Expanded(
                                  child: Text(c.category, style: const TextStyle(fontWeight: FontWeight.w500)),
                                ),
                                Text(
                                  '${c.pct.toStringAsFixed(0)}%',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                    color: AppTheme.brandBlue,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: (c.pct / 100).clamp(0.0, 1.0),
                                minHeight: 8,
                                color: AppTheme.brandBlue,
                                backgroundColor: AppTheme.accentWash,
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ],

          const SizedBox(height: 16),
          Text(
            'Simulator decisions',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          if (history.isEmpty)
            PremiumCard(
              child: Text(
                'No simulator runs yet. Use Plan → Simulate to add entries here.',
                style: TextStyle(color: AppTheme.mutedForeground),
              ),
            )
          else
            ...history.map(
              (h) => PremiumCard(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                child: InkWell(
                  onTap: () => _openDetail(h.id),
                  child: Row(
                    children: [
                      const Icon(Icons.insights_rounded, color: AppTheme.brandBlue, size: 20),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(h.productName, style: const TextStyle(fontWeight: FontWeight.w600)),
                            Text(
                              DateFormat.yMMMd().format(h.createdAt),
                              style: const TextStyle(fontSize: 12, color: AppTheme.mutedForeground),
                            ),
                          ],
                        ),
                      ),
                      Text(
                        h.recommendationType,
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.brandBlue,
                        ),
                      ),
                      const Icon(Icons.chevron_right_rounded, color: AppTheme.mutedForeground),
                    ],
                  ),
                ),
              ),
            ),

          const SizedBox(height: 12),
          _TrainingBenchmarkPanel(
            expanded: _showTrainingBenchmark,
            metrics: trainingMetrics,
            onToggle: () => setState(() => _showTrainingBenchmark = !_showTrainingBenchmark),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.label,
    required this.value,
    required this.hint,
    required this.icon,
  });

  final String label;
  final String value;
  final String hint;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return PremiumCard(
      margin: const EdgeInsets.only(top: 4, bottom: 4),
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppTheme.brandBlue, size: 20),
          const SizedBox(height: 8),
          Text(label, style: const TextStyle(fontSize: 11, color: AppTheme.mutedForeground)),
          const SizedBox(height: 4),
          Text(
            value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          ),
          Text(hint, style: const TextStyle(fontSize: 10, color: AppTheme.mutedForeground)),
        ],
      ),
    );
  }
}

class _TrainingBenchmarkPanel extends StatelessWidget {
  const _TrainingBenchmarkPanel({
    required this.expanded,
    required this.metrics,
    required this.onToggle,
  });

  final bool expanded;
  final Map<String, dynamic>? metrics;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final acc = ((metrics?['overall_accuracy'] as num?)?.toDouble() ?? 0) * 100;
    final f1 = (metrics?['f1_score'] as num?)?.toDouble() ?? 0;
    final fi = (metrics?['feature_importance'] as List<dynamic>? ?? []);

    return Material(
      color: AppTheme.surfaceCard,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppTheme.borderColor),
      ),
      child: Column(
        children: [
          InkWell(
            onTap: onToggle,
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Icon(Icons.science_outlined, color: AppTheme.mutedForeground, size: 20),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'ML training benchmark (reference)',
                          style: TextStyle(fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                        ),
                        Text(
                          'Static 94% figures — not your upload',
                          style: TextStyle(fontSize: 12, color: AppTheme.mutedForeground),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    expanded ? Icons.expand_less : Icons.expand_more,
                    color: AppTheme.mutedForeground,
                  ),
                ],
              ),
            ),
          ),
          if (expanded)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    metrics?['disclaimer'] as String? ?? '',
                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, height: 1.4),
                  ),
                  const SizedBox(height: 12),
                  Text('Accuracy ${acc.toStringAsFixed(1)}% · F1 ${f1.toStringAsFixed(2)}'),
                  const SizedBox(height: 8),
                  for (final raw in fi)
                    Text(
                      '• ${(raw as Map)['name']}: ${((raw)['weight_pct'] as num?)?.toStringAsFixed(0)}%',
                      style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
