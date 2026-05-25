import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../theme/app_theme.dart';
import 'ai_advisor_screen.dart';
import 'dashboard_screen.dart';
import 'grants_screen.dart';
import 'performance_screen.dart';
import 'simulator_screen.dart';
import 'compare_screen.dart';
import 'grant_eligibility_screen.dart';
import 'insights_screen.dart';
import 'scenario_planner_screen.dart';
import 'settings_screen.dart';
import 'upload_screen.dart';
import 'notifications_screen.dart';
import '../services/push_notification_service.dart';
import 'lender_directory_screen.dart';
import 'application_tracker_screen.dart';
import 'bnpl_repayment_screen.dart';
import 'pitch_screen.dart';
import 'financing_timeline_screen.dart';
import '../providers/settings_provider.dart';
import '../l10n/app_strings.dart';

class ShellScreen extends StatefulWidget {
  const ShellScreen({super.key});

  @override
  State<ShellScreen> createState() => _ShellScreenState();
}

class _ShellScreenState extends State<ShellScreen> {
  int _index = 0;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _registerPush());
  }

  Future<void> _registerPush() async {
    final sid = context.read<SessionProvider>().smeId;
    await PushNotificationService.instance.registerForSme(sid);
  }

  List<String> _labels(BuildContext context) {
    final s = AppStrings(context.watch<SettingsProvider>().locale);
    return [s.health, s.simulate, s.aiAdvisor, s.grants, s.performance];
  }
  static const _icons = [
    Icons.grid_view_rounded,
    Icons.calculate_rounded,
    Icons.psychology_rounded,
    Icons.account_balance_rounded,
    Icons.show_chart_rounded,
  ];

  @override
  Widget build(BuildContext context) {
    final sid = context.watch<SessionProvider>().smeId;
    final pages = <Widget>[
      DashboardScreen(key: ValueKey('dash_$sid')),
      const SimulatorScreen(),
      const AiAdvisorScreen(),
      const GrantsScreen(),
      PerformanceScreen(key: ValueKey('perf_$sid')),
    ];

    return Scaffold(
      key: _scaffoldKey,
      extendBodyBehindAppBar: false,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(kToolbarHeight),
        child: Container(
          decoration: const BoxDecoration(
            gradient: AppTheme.headerGradient,
            boxShadow: [
              BoxShadow(
                color: Color(0x33004D40),
                blurRadius: 12,
                offset: Offset(0, 2),
              ),
            ],
          ),
          child: AppBar(
            backgroundColor: Colors.transparent,
            elevation: 0,
            leading: IconButton(
              icon: const Icon(Icons.menu_rounded, color: Colors.white),
              onPressed: () => _scaffoldKey.currentState?.openDrawer(),
            ),
            title: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.trending_up_rounded, color: AppTheme.tealAccent, size: 20),
                ),
                const SizedBox(width: 10),
                const Text(
                  'SME Advisor',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                    color: Colors.white,
                  ),
                ),
              ],
            ),
            actions: [
              Container(
                margin: const EdgeInsets.only(right: 8),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: IconButton(
                  icon: const Icon(Icons.notifications_none_rounded, color: Colors.white70),
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(builder: (_) => const NotificationsScreen()),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
      drawer: _buildDrawer(context, sid),
      body: Container(
        decoration: const BoxDecoration(gradient: AppTheme.backgroundGradient),
        child: IndexedStack(index: _index, children: pages),
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius: 16,
              offset: const Offset(0, -4),
            ),
          ],
        ),
        child: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (i) => setState(() => _index = i),
          destinations: [
            for (var i = 0; i < _labels(context).length; i++)
              NavigationDestination(
                icon: Icon(_icons[i]),
                selectedIcon: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.teal.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(_icons[i], color: AppTheme.teal),
                ),
                label: _labels(context)[i],
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildDrawer(BuildContext context, int sid) {
    return Drawer(
      child: Container(
        decoration: const BoxDecoration(color: Colors.white),
        child: SafeArea(
          child: ListView(
            padding: EdgeInsets.zero,
            children: [
              Container(
                padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
                decoration: const BoxDecoration(
                  gradient: AppTheme.headerGradient,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: const Icon(Icons.trending_up_rounded, color: AppTheme.tealAccent, size: 32),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'SME Advisor',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'AI-powered BNPL Intelligence',
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.white.withOpacity(0.7),
                        letterSpacing: 0.3,
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 24, 24, 8),
                child: Row(
                  children: [
                    Icon(Icons.business_rounded, size: 18, color: Colors.grey.shade500),
                    const SizedBox(width: 8),
                    Text(
                      'SELECT BUSINESS',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 11,
                        letterSpacing: 1.2,
                        color: Colors.grey.shade500,
                      ),
                    ),
                  ],
                ),
              ),
              _smeOption(context, 1, 'Kopi Maju', 'Food & Beverage', Icons.coffee_rounded, sid),
              _smeOption(context, 2, 'Harapan Agro', 'Agriculture', Icons.grass_rounded, sid),
              _smeOption(context, 3, 'Urban Digital', 'Technology', Icons.computer_rounded, sid),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                child: Divider(color: Colors.grey.shade200),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.teal.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.upload_file_rounded, color: AppTheme.teal, size: 20),
                  ),
                  title: const Text('Upload CSV', style: TextStyle(fontWeight: FontWeight.w500)),
                  subtitle: Text('Import transaction data', style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  onTap: () {
                    Navigator.pop(context);
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(builder: (_) => const UploadScreen()),
                    );
                  },
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.teal.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.insights_rounded, color: AppTheme.teal, size: 20),
                  ),
                  title: const Text('AI Insights', style: TextStyle(fontWeight: FontWeight.w500)),
                  subtitle: Text('Clusters, anomalies, bandit, OCR', style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  onTap: () {
                    Navigator.pop(context);
                    Navigator.of(context).push(
                      MaterialPageRoute<void>(builder: (_) => const InsightsScreen()),
                    );
                  },
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: AppTheme.teal.withOpacity(0.08), borderRadius: BorderRadius.circular(10)),
                    child: const Icon(Icons.compare_arrows_rounded, color: AppTheme.teal, size: 20),
                  ),
                  title: const Text('Compare financing'),
                  onTap: () {
                    Navigator.pop(context);
                    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const CompareScreen()));
                  },
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: AppTheme.teal.withOpacity(0.08), borderRadius: BorderRadius.circular(10)),
                    child: const Icon(Icons.verified_rounded, color: AppTheme.teal, size: 20),
                  ),
                  title: const Text('Grant eligibility'),
                  subtitle: Text('Budget 2026 rules engine', style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
                  onTap: () {
                    Navigator.pop(context);
                    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const GrantEligibilityScreen()));
                  },
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: AppTheme.teal.withOpacity(0.08), borderRadius: BorderRadius.circular(10)),
                    child: const Icon(Icons.tune_rounded, color: AppTheme.teal, size: 20),
                  ),
                  title: const Text('What-if planner'),
                  onTap: () {
                    Navigator.pop(context);
                    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const ScenarioPlannerScreen()));
                  },
                ),
              ),
              _drawerNav(context, Icons.notifications_active_rounded, 'AI Nudges', const NudgesScreen()),
              _drawerNav(context, Icons.account_balance_rounded, 'Lender Directory', const LenderDirectoryScreen()),
              _drawerNav(context, Icons.view_kanban_rounded, 'Application Tracker', const ApplicationTrackerScreen()),
              _drawerNav(context, Icons.calendar_month_rounded, 'BNPL Repayment', const BnplRepaymentScreen()),
              _drawerNav(context, Icons.description_rounded, 'Pitch Generator', const PitchScreen()),
              _drawerNav(context, Icons.timeline_rounded, 'Financing Timeline', const FinancingTimelineScreen()),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: AppTheme.teal.withOpacity(0.08), borderRadius: BorderRadius.circular(10)),
                    child: const Icon(Icons.settings_rounded, color: AppTheme.teal, size: 20),
                  ),
                  title: const Text('Settings'),
                  onTap: () {
                    Navigator.pop(context);
                    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen()));
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _drawerNav(BuildContext context, IconData icon, String title, Widget screen) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: AppTheme.teal.withOpacity(0.08), borderRadius: BorderRadius.circular(10)),
          child: Icon(icon, color: AppTheme.teal, size: 20),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w500)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        onTap: () {
          Navigator.pop(context);
          Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => screen));
        },
      ),
    );
  }

  Widget _smeOption(BuildContext context, int id, String name, String industry, IconData icon, int current) {
    final selected = id == current;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: selected ? AppTheme.teal.withOpacity(0.12) : Colors.grey.shade100,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: selected ? AppTheme.teal : Colors.grey.shade400, size: 20),
        ),
        title: Text(name, style: TextStyle(fontWeight: selected ? FontWeight.w600 : FontWeight.w400)),
        subtitle: Text(industry, style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
        trailing: selected
            ? Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.teal.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text('ACTIVE', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: AppTheme.teal)),
              )
            : null,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        selected: selected,
        selectedTileColor: AppTheme.teal.withOpacity(0.04),
        onTap: () async {
          await context.read<SessionProvider>().setSmeId(id);
          if (context.mounted) Navigator.pop(context);
        },
      ),
    );
  }
}
