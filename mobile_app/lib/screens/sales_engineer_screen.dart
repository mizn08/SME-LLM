import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../widgets/sales_engineer_tab.dart';

/// Standalone route — redirects user to AI Advisor tab in practice.
class SalesEngineerScreen extends StatelessWidget {
  const SalesEngineerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Autonomous Sales Engineer')),
      body: SalesEngineerTab(
        api: ApiService(),
        onRagSynced: (_, __, ___) {},
      ),
    );
  }
}

/// Opens AI Advisor bottom tab + Sales Engineer sub-tab.
void openSalesEngineerInAdvisor(BuildContext context, void Function(int) setShellIndex) {
  context.read<AdvisorNavProvider>().openSubTab(4);
  setShellIndex(2);
}
