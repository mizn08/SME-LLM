import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/application_tracker.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/application_kanban_card.dart';

class ApplicationTrackerScreen extends StatefulWidget {
  const ApplicationTrackerScreen({super.key});

  @override
  State<ApplicationTrackerScreen> createState() => _ApplicationTrackerScreenState();
}

class _ApplicationTrackerScreenState extends State<ApplicationTrackerScreen> {
  List<ApplicationTrackerItem> _apps = [];
  bool loading = true;

  static const _columns = ['draft', 'submitted', 'under_review', 'approved'];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final sid = context.read<SessionProvider>().smeId;
    try {
      final res = await ApiService().fetchApplications(sid);
      _apps = res.applications;
    } catch (_) {}
    if (mounted) setState(() => loading = false);
  }

  Future<void> _create() async {
    final sid = context.read<SessionProvider>().smeId;
    await ApiService().createApplication(
      smeId: sid,
      productName: 'New application',
      productType: 'grant',
    );
    _load();
  }

  Future<void> _updateStatus(ApplicationTrackerItem item) async {
    final idx = _columns.indexOf(item.status);
    final next = idx < 0 || idx >= _columns.length - 1 ? 'submitted' : _columns[idx + 1];
    await ApiService().updateApplication(id: item.id, status: next);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Application Tracker'),
        backgroundColor: AppTheme.teal,
        actions: [IconButton(icon: const Icon(Icons.add), onPressed: _create)],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.all(8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final col in _columns)
                    SizedBox(
                      width: 160,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: const EdgeInsets.all(8),
                            child: Text(col.replaceAll('_', ' ').toUpperCase(),
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 11)),
                          ),
                          ..._apps.where((a) => a.status == col || (col == 'approved' && a.status == 'rejected')).map(
                                (a) => ApplicationKanbanCard(item: a, onTap: () => _updateStatus(a)),
                              ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}
