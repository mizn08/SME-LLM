import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../l10n/app_strings.dart';
import '../providers/session_provider.dart';
import '../providers/settings_provider.dart';
import '../providers/shell_nav_provider.dart';
import '../services/push_notification_service.dart';
import '../theme/app_theme.dart';
import '../widgets/app_logo.dart';
import 'ai_advisor_screen.dart';
import 'application_tracker_screen.dart';
import 'benchmark_screen.dart';
import 'bnpl_repayment_screen.dart';
import 'compare_screen.dart';
import 'dashboard_screen.dart';
import 'grant_eligibility_screen.dart';
import 'grants_screen.dart';
import 'insights_screen.dart';
import 'lender_directory_screen.dart';
import 'notifications_screen.dart';
import 'nudges_screen.dart';
import 'performance_screen.dart';
import 'sales_engineer_screen.dart';
import 'scenario_planner_screen.dart';
import 'settings_screen.dart';
import 'simulator_screen.dart';
import 'upload_screen.dart';

class ShellScreen extends StatefulWidget {
  const ShellScreen({super.key});

  @override
  State<ShellScreen> createState() => _ShellScreenState();
}

class _ShellScreenState extends State<ShellScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  /// HCI workflow: 0 Home → 1 Plan → 2 Ask AI → 3 Funding → 4 History
  static const _icons = [
    Icons.home_rounded,
    Icons.edit_note_rounded,
    Icons.psychology_alt_rounded,
    Icons.assured_workload_rounded,
    Icons.history_rounded,
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _registerPush());
  }

  Future<void> _registerPush() async {
    final sid = context.read<SessionProvider>().smeId;
    await PushNotificationService.instance.registerForSme(sid);
  }

  void _goTab(int i) => context.read<ShellNavProvider>().goToTab(i);

  @override
  Widget build(BuildContext context) {
    final index = context.watch<ShellNavProvider>().tabIndex;
    final sid = context.watch<SessionProvider>().smeId;
    final s = AppStrings(context.watch<SettingsProvider>().locale);
    final labels = [s.home, s.plan, s.askAi, s.funding, s.history];

    final pages = <Widget>[
      DashboardScreen(key: ValueKey('dash_$sid'), onNavigateTab: _goTab),
      const SimulatorScreen(),
      const AiAdvisorScreen(),
      const GrantsScreen(),
      PerformanceScreen(key: ValueKey('perf_$sid')),
    ];

    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: AppTheme.voidBg,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(kToolbarHeight + 6),
        child: Container(
          decoration: AppTheme.brandAppBarDecoration,
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.menu_rounded, color: AppTheme.brandBlue),
                    onPressed: () => _scaffoldKey.currentState?.openDrawer(),
                  ),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const AppLogo(size: 32, borderRadius: 8),
                            const SizedBox(width: 10),
                            Text(
                              s.appTitle,
                              style: const TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.2,
                                color: AppTheme.brandBlue,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 2),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppTheme.accentWash,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: AppTheme.borderColor),
                          ),
                          child: Text(
                            labels[index],
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.brandBlueDark,
                              letterSpacing: 0.2,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: Stack(
                      clipBehavior: Clip.none,
                      children: [
                        const Icon(Icons.notifications_outlined, color: AppTheme.brandBlueDark),
                        Positioned(
                          right: 2,
                          top: 2,
                          child: Container(
                            width: 7,
                            height: 7,
                            decoration: BoxDecoration(
                              color: AppTheme.coral,
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 1.5),
                            ),
                          ),
                        ),
                      ],
                    ),
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(builder: (_) => const NotificationsScreen()),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
      drawer: _buildDrawer(context, sid, s),
      body: IndexedStack(index: index, children: pages),
      bottomNavigationBar: NavigationBar(
        backgroundColor: AppTheme.surfaceCard,
        indicatorColor: AppTheme.accentWash,
        elevation: 0,
        height: 72,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        selectedIndex: index,
        onDestinationSelected: _goTab,
        destinations: [
          for (var i = 0; i < labels.length; i++)
            NavigationDestination(
              icon: Icon(_icons[i], size: 22),
              selectedIcon: Icon(
                _icons[i],
                size: 22,
                color: i == 3 ? AppTheme.goldAccent : AppTheme.brandBlue,
              ),
              label: labels[i],
            ),
        ],
      ),
    );
  }

  Widget _sectionLabel(String text) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 8),
      child: Text(
        text,
        style: const TextStyle(
          fontWeight: FontWeight.w700,
          fontSize: 11,
          letterSpacing: 1.1,
          color: AppTheme.mutedForeground,
        ),
      ),
    );
  }

  Widget _buildDrawer(BuildContext context, int sid, AppStrings s) {
    return Drawer(
      backgroundColor: AppTheme.surfaceDeep,
      child: SafeArea(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            Container(
              padding: const EdgeInsets.fromLTRB(24, 28, 24, 20),
              decoration: const BoxDecoration(gradient: AppTheme.headerGradient),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const AppLogo(size: 56, borderRadius: 14),
                  const SizedBox(height: 14),
                  Text(s.appTitle, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: AppTheme.textPrimary)),
                  const SizedBox(height: 4),
                  Text(s.appSubtitle, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
                  const SizedBox(height: 4),
                  Text(s.appTagline, style: const TextStyle(fontSize: 11, color: AppTheme.mutedForeground)),
                ],
              ),
            ),
            _sectionLabel('YOUR BUSINESS'),
            _smeOption(context, 1, 'Kopi Maju', 'Food & Beverage', Icons.coffee_rounded, sid),
            _smeOption(context, 2, 'Harapan Agro', 'Agriculture', Icons.grass_rounded, sid),
            _smeOption(context, 3, 'Urban Digital', 'Technology', Icons.computer_rounded, sid),
            _sectionLabel(s.drawerUnderstand),
            _drawerTile(context, Icons.upload_file_rounded, 'Upload transactions', AppTheme.surfaceElevated, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const UploadScreen()));
            }),
            _drawerTile(context, Icons.insights_rounded, 'AI insights & anomalies', AppTheme.sky, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const InsightsScreen()));
            }),
            _drawerTile(context, Icons.notifications_active_rounded, 'Alerts & nudges', AppTheme.blush, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const NudgesScreen()));
            }),
            _sectionLabel(s.drawerPlan),
            _drawerTile(context, Icons.calculate_rounded, 'Financing simulator', AppTheme.peach, () {
              Navigator.pop(context);
              _goTab(1);
            }),
            _drawerTile(context, Icons.compare_arrows_rounded, 'Compare financing', AppTheme.surfaceElevated, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const CompareScreen()));
            }),
            _drawerTile(context, Icons.tune_rounded, 'What-if planner', AppTheme.surfaceElevated, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const ScenarioPlannerScreen()));
            }),
            _sectionLabel(s.drawerGuidance),
            _drawerTile(context, Icons.psychology_alt_rounded, 'BNPL Advisor (RAG + LLM)', AppTheme.midnight, () {
              Navigator.pop(context);
              _goTab(2);
            }, emphasized: true),
            _drawerTile(context, Icons.engineering_rounded, 'Autonomous Sales Engineer', AppTheme.peach, () {
              Navigator.pop(context);
              openSalesEngineerInAdvisor(context, _goTab);
            }),
            _drawerTile(context, Icons.verified_rounded, 'Grant eligibility', AppTheme.sky, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const GrantEligibilityScreen()));
            }),
            _sectionLabel(s.drawerApply),
            _drawerTile(context, Icons.assured_workload_rounded, 'Funding catalog', AppTheme.ember, () {
              Navigator.pop(context);
              _goTab(3);
            }),
            _drawerTile(context, Icons.view_kanban_rounded, 'Application tracker', AppTheme.surfaceElevated, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const ApplicationTrackerScreen()));
            }),
            _drawerTile(context, Icons.account_balance_rounded, 'Lender directory', AppTheme.surfaceElevated, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const LenderDirectoryScreen()));
            }),
            _drawerTile(context, Icons.calendar_month_rounded, 'BNPL repayment', AppTheme.peach, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const BnplRepaymentScreen()));
            }),
            _drawerTile(context, Icons.leaderboard_rounded, 'Industry benchmark', AppTheme.surfaceElevated, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const BenchmarkScreen()));
            }),
            const Divider(height: 24, indent: 24, endIndent: 24),
            _drawerTile(context, Icons.settings_rounded, s.settings, AppTheme.borderColor, () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute<void>(builder: (_) => const SettingsScreen()));
            }),
          ],
        ),
      ),
    );
  }

  Widget _drawerTile(
    BuildContext context,
    IconData icon,
    String title,
    Color bg,
    VoidCallback onTap, {
    bool emphasized = false,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: bg.withOpacity(0.5),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: AppTheme.textPrimary, size: 20),
        ),
        title: Text(
          title,
          style: TextStyle(
            fontWeight: emphasized ? FontWeight.w700 : FontWeight.w500,
            color: emphasized ? AppTheme.ember : AppTheme.textPrimary,
          ),
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        onTap: onTap,
      ),
    );
  }

  Widget _smeOption(BuildContext context, int id, String name, String industry, IconData icon, int current) {
    final selected = id == current;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: selected ? const Color(0xFFE8EDF5) : Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: selected ? AppTheme.midnight : AppTheme.borderColor),
          ),
          child: Icon(icon, color: selected ? AppTheme.midnight : AppTheme.mutedForeground, size: 20),
        ),
        title: Text(name, style: TextStyle(fontWeight: selected ? FontWeight.w700 : FontWeight.w500)),
        subtitle: Text(industry, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
        trailing: selected
            ? Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(color: AppTheme.successBg, borderRadius: BorderRadius.circular(8)),
                child: const Text('Active', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTheme.successFg)),
              )
            : null,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        onTap: () async {
          await context.read<SessionProvider>().setSmeId(id);
          if (context.mounted) Navigator.pop(context);
        },
      ),
    );
  }
}
