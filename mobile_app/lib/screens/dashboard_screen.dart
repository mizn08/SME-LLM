import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';

import '../models/dashboard.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../services/pdf_report_service.dart' show PdfReportService, writePdfBytes;
import '../theme/app_theme.dart';
import '../widgets/compliance_countdown_widget.dart';
import '../widgets/kpi_card.dart';
import '../models/digest.dart';
import '../models/nudge.dart';
import '../models/spending_category.dart';
import '../widgets/monthly_chart.dart';
import '../widgets/nudge_banner.dart';
import '../widgets/spending_donut_chart.dart';
import 'benchmark_screen.dart';
import 'digest_screen.dart';
import 'nudges_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> with SingleTickerProviderStateMixin {
  DashboardData? data;
  String? error;
  bool loading = true;
  NudgeResponse? nudges;
  SpendingCategoryResponse? spending;
  DigestResponse? digest;
  bool _nudgeDismissed = false;
  late AnimationController _animCtrl;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _animCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _fadeAnim = CurvedAnimation(parent: _animCtrl, curve: Curves.easeOutCubic);
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    _animCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final sid = context.read<SessionProvider>().smeId;
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final api = ApiService();
      final d = await api.fetchDashboard(sid);
      NudgeResponse? n;
      SpendingCategoryResponse? sp;
      DigestResponse? dig;
      try {
        n = await api.fetchNudges(sid);
        sp = await api.fetchSpendingCategories(sid);
        dig = await api.fetchDigest(sid);
      } catch (_) {}
      if (mounted) {
        setState(() {
          data = d;
          nudges = n;
          spending = sp;
          digest = dig;
        });
        _animCtrl.forward(from: 0);
      }
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  int _healthScore(DashboardData d) {
    final liquidity = (d.currentRatio / 2).clamp(0.0, 1.0);
    final cash = (d.daysCashOnHand / 90).clamp(0.0, 1.0);
    final burnOk = d.burnRateMonthlyRm > 0 ? (1 - (d.expenseMtdRm / (d.burnRateMonthlyRm + 1)).clamp(0.0, 0.5)) : 0.5;
    final raw = (0.4 * liquidity + 0.45 * cash + 0.15 * burnOk) * 100;
    return raw.round().clamp(0, 100);
  }

  String _healthLabel(int s) {
    if (s >= 75) return 'GOOD';
    if (s >= 55) return 'FAIR';
    return 'WATCH';
  }

  String _letterGrade(int s) {
    if (s >= 90) return 'A';
    if (s >= 80) return 'B';
    if (s >= 70) return 'C';
    if (s >= 60) return 'D';
    if (s >= 50) return 'E';
    return 'F';
  }

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(symbol: 'RM ', decimalDigits: 2);
    return RefreshIndicator(
      color: AppTheme.teal,
      onRefresh: _load,
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Financial Overview',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: AppTheme.textPrimary,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(color: AppTheme.accentGreen, shape: BoxShape.circle),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Live · Data synced as of today',
                        style: TextStyle(color: Colors.grey.shade500, fontSize: 13),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          if (loading)
            const SliverFillRemaining(child: Center(child: CircularProgressIndicator(color: AppTheme.teal)))
          else if (error != null)
            SliverFillRemaining(
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.cloud_off_rounded, size: 48, color: Colors.grey.shade400),
                      const SizedBox(height: 12),
                      Text(
                        'Could not load dashboard',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.grey.shade700),
                      ),
                      const SizedBox(height: 8),
                      Text(error!, textAlign: TextAlign.center, style: TextStyle(color: Colors.grey.shade500)),
                    ],
                  ),
                ),
              ),
            )
          else if (data != null)
            SliverToBoxAdapter(
              child: FadeTransition(
                opacity: _fadeAnim,
                child: _body(context, data!, currency),
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _downloadReport(BuildContext context, DashboardData d) async {
    try {
      final report = await ApiService().fetchReport(d.smeId);
      final bytes = await PdfReportService.buildFullReportBytes(report);
      if (kIsWeb) {
        await Share.shareXFiles([
          XFile.fromData(bytes, name: 'sme_advisor_report.pdf', mimeType: 'application/pdf'),
        ], text: 'SME Advisor — bank / grant pack');
      } else {
        final file = await writePdfBytes(bytes, 'sme_advisor_full_report.pdf');
        await Share.shareXFiles([XFile(file.path)], text: 'SME Advisor — bank / grant pack');
      }
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Report ready to share')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  Widget _body(BuildContext context, DashboardData d, NumberFormat currency) {
    final score = d.healthScore ?? _healthScore(d);
    final label = d.healthLabel ?? _healthLabel(score);
    final grade = d.healthGrade ?? _letterGrade(score);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 8),
        if (!_nudgeDismissed && nudges != null && nudges!.nudges.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: NudgeBanner(
              nudge: nudges!.nudges.first,
              onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const NudgesScreen())),
              onDismiss: () => setState(() => _nudgeDismissed = true),
            ),
          ),
        if (digest != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Card(
              child: ListTile(
                leading: const Icon(Icons.calendar_today, color: AppTheme.teal),
                title: const Text('This week in your business'),
                subtitle: Text(digest!.summary, maxLines: 2, overflow: TextOverflow.ellipsis),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const DigestScreen())),
              ),
            ),
          ),
        if (d.alerts.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Material(
              color: Colors.orange.shade50,
              borderRadius: BorderRadius.circular(12),
              child: ListTile(
                leading: Icon(Icons.warning_amber_rounded, color: Colors.orange.shade800),
                title: Text(d.alerts.first, style: TextStyle(fontSize: 13, color: Colors.orange.shade900)),
                subtitle: d.runwayDaysEst != null
                    ? Text('Runway ~${d.runwayDaysEst!.toStringAsFixed(0)} days · ${d.anomalyCount} anomalies')
                    : null,
              ),
            ),
          ),
        const ComplianceCountdownWidget(),
        PremiumCard(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Column(
            children: [
              Text(
                'SME Readiness Score',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 4),
              Text(
                'Like a credit score for financial readiness',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
              const SizedBox(height: 8),
              HealthScoreGauge(score: score, label: label, letterGrade: grade),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: () => _downloadReport(context, d),
                icon: const Icon(Icons.picture_as_pdf_outlined, size: 18),
                label: const Text('Generate bank / grant PDF'),
                style: FilledButton.styleFrom(backgroundColor: AppTheme.teal),
              ),
            ],
          ),
        ),
        // ── Cash posture ──
        KPICard(
          title: '30-day cash posture',
          value: currency.format(d.netOperatingCashRm),
          subtitle: 'Net operating cash (90d window)',
          leading: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppTheme.teal.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.account_balance_wallet_rounded, color: AppTheme.teal, size: 20),
          ),
          trend: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.green.shade50,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.trending_up_rounded, color: Colors.green.shade600, size: 16),
                const SizedBox(width: 4),
                Text(
                  '${d.revenueMtdRm > d.expenseMtdRm ? '+' : ''}MTD',
                  style: TextStyle(color: Colors.green.shade700, fontSize: 12, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
        ),
        // ── Two-up KPIs ──
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Row(
            children: [
              Expanded(
                child: KPICard(
                  title: 'Liquidity',
                  value: d.currentRatio.toStringAsFixed(2),
                  subtitle: 'Inflow / burn proxy',
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.teal.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.water_drop_rounded, color: AppTheme.teal, size: 20),
                  ),
                ),
              ),
              Expanded(
                child: KPICard(
                  title: 'Days cash on hand',
                  value: d.daysCashOnHand.toStringAsFixed(0),
                  subtitle: 'Estimated runway',
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.teal.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.shield_rounded, color: AppTheme.teal, size: 20),
                  ),
                ),
              ),
            ],
          ),
        ),
        // ── Chart section ──
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 8),
          child: Row(
            children: [
              Text(
                'Revenue vs Expenses',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.teal.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('12M', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.teal)),
              ),
            ],
          ),
        ),
        if (spending != null && spending!.categories.isNotEmpty) ...[
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
            child: Text('Spending by category', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
          ),
          PremiumCard(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            child: SpendingDonutChart(categories: spending!.categories),
          ),
        ],
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const BenchmarkScreen())),
                  icon: const Icon(Icons.leaderboard_outlined, size: 18),
                  label: const Text('Industry benchmark'),
                ),
              ),
            ],
          ),
        ),
        PremiumCard(
          margin: const EdgeInsets.symmetric(horizontal: 16),
          padding: const EdgeInsets.all(12),
          child: MonthlyCashChart(
            points: d.monthlySeries,
            forecastNet: d.forecastMonths.map((f) => f.projectedNetRm).toList(),
          ),
        ),
        const SizedBox(height: 32),
      ],
    );
  }
}
