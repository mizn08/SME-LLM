import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/nudge.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class NudgesScreen extends StatefulWidget {
  const NudgesScreen({super.key});

  @override
  State<NudgesScreen> createState() => _NudgesScreenState();
}

class _NudgesScreenState extends State<NudgesScreen> {
  NudgeResponse? data;
  bool loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final sid = context.read<SessionProvider>().smeId;
    setState(() => loading = true);
    try {
      data = await ApiService().fetchNudges(sid);
    } catch (_) {}
    if (mounted) setState(() => loading = false);
  }

  Color _severityColor(String s) {
    if (s == 'critical') return Colors.red;
    if (s == 'warning') return Colors.orange;
    return AppTheme.teal;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI Nudges'), backgroundColor: AppTheme.teal),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  for (final n in data?.nudges ?? [])
                    Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      child: ListTile(
                        leading: Icon(Icons.lightbulb, color: _severityColor(n.severity)),
                        title: Text(n.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                        subtitle: Text(n.body),
                        trailing: n.actionLabel != null
                            ? TextButton(onPressed: () {}, child: Text(n.actionLabel!))
                            : null,
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}
