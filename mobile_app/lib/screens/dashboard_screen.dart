import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';

import '../models/dashboard.dart';
import '../providers/advisor_nav_provider.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../services/pdf_report_service.dart' show PdfReportService, writePdfBytes;
import '../theme/app_theme.dart';
import '../utils/constants.dart';
import '../widgets/compliance_countdown_widget.dart';
import '../widgets/kpi_card.dart';
import '../models/digest.dart';
import '../models/nudge.dart';
import '../models/spending_category.dart';
import '../widgets/monthly_chart.dart';
import '../widgets/nudge_banner.dart';
import '../widgets/spending_donut_chart.dart';
import '../widgets/workflow_guide.dart';
import 'benchmark_screen.dart';
import 'digest_screen.dart';
import 'nudges_screen.dart';
import 'upload_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, this.onNavigateTab});

  /// Switch shell bottom nav (0=Home … 4=History).
  final void Function(int tabIndex)? onNavigateTab;

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

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(symbol: 'RM ', decimalDigits: 2);
    return RefreshIndicator(
      color: AppTheme.sage,
      onRefresh: _load,
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: Container(
              decoration: const BoxDecoration(gradient: AppTheme.backgroundGradient),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          data != null ? 'Hi, ${data!.businessName}' : 'Hi there',
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                fontWeight: FontWeight.w700,
                                color: AppTheme.textPrimary,
                              ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'SME LLM BNPL Advisor — cashflow pulse synced for quotes and financing.',
                          style: TextStyle(color: AppTheme.textSecondary, fontSize: 13, height: 1.4),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(color: AppTheme.successFg, shape: BoxShape.circle),
                      ),
                            const SizedBox(width: 6),
                            const Text(
                              'Live data · synced with BNPL Advisor',
                              style: TextStyle(color: AppTheme.mutedForeground, fontSize: 12),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  WorkflowGuide(
                    currentStep: 0,
                    onStepTap: widget.onNavigateTab == null
                        ? null
                        : (step) {
                            switch (step) {
                              case 1:
                                context.read<AdvisorNavProvider>().openSubTab(4);
                                widget.onNavigateTab!(2);
                                break;
                              case 2:
                                context.read<AdvisorNavProvider>().openSubTab(0);
                                widget.onNavigateTab!(2);
                                break;
                              case 3:
                                widget.onNavigateTab!(3);
                                break;
                              default:
                                widget.onNavigateTab!(0);
                            }
                          },
                  ),
                  if (widget.onNavigateTab != null)
                    QuickActionGrid(
                      onAskAi: () => widget.onNavigateTab!(2),
                      onSimulate: () => widget.onNavigateTab!(1),
                      onGrants: () => widget.onNavigateTab!(3),
                      onUpload: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(builder: (_) => const UploadScreen()),
                      ),
                    ),
                ],
              ),
            ),
          ),
          if (loading)
            const SliverFillRemaining(child: Center(child: CircularProgressIndicator(color: AppTheme.sage)))
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
                      const SizedBox(height: 8),
                      Text(
                        'API: ${resolveApiBase()}',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 11, color: Colors.grey.shade400),
                      ),
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
      final xFile = await writePdfBytes(bytes, 'sme_advisor_full_report.pdf');
      await Share.shareXFiles([xFile], text: 'SME Advisor — bank / grant pack');
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
    final score = d.healthScore ?? 0;
    final label = d.healthLabel ?? '—';
    final grade = d.healthGrade ?? '—';
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
              color: AppTheme.infoBg,
              elevation: 0,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: AppTheme.borderColor)),
              child: ListTile(
                leading: const Icon(Icons.calendar_today_rounded, color: AppTheme.infoFg),
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
              color: AppTheme.warningBg,
              borderRadius: BorderRadius.circular(16),
              child: ListTile(
                leading: const Icon(Icons.warning_amber_rounded, color: AppTheme.warningFg),
                title: Text(d.alerts.first, style: const TextStyle(fontSize: 13, color: AppTheme.warningFg, fontWeight: FontWeight.w600)),
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
              const Text(
                'Like a credit score for financial readiness',
                style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
              ),
              const SizedBox(height: 8),
              HealthScoreGauge(score: score, label: label, letterGrade: grade),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: () => _downloadReport(context, d),
                icon: const Icon(Icons.picture_as_pdf_outlined, size: 18),
                label: const Text('Generate bank / grant PDF'),
              ),
            ],
          ),
        ),
        // ── Cash posture ──
        KPICard(
          title: '90-day cash posture',
          value: currency.format(d.netOperatingCashRm),
          subtitle: 'Net operating cash (same as AI Advisor)',
          leading: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppTheme.mint,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.account_balance_wallet_rounded, color: AppTheme.midnight, size: 20),
          ),
          trend: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: d.netOperatingCashRm >= 0 ? AppTheme.successBg : AppTheme.criticalBg,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              d.netOperatingCashRm >= 0 ? 'Positive' : 'Negative',
              style: TextStyle(
                color: d.netOperatingCashRm >= 0 ? AppTheme.successFg : AppTheme.criticalFg,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
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
                      color: AppTheme.sky,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.water_drop_rounded, color: AppTheme.midnightLight, size: 20),
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
                      color: AppTheme.peach,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.shield_rounded, color: AppTheme.ember, size: 20),
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
                  color: AppTheme.mint,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('12M', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.midnight)),
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
