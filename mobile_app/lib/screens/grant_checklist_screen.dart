import 'package:flutter/material.dart';

import '../models/grant_checklist.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class GrantChecklistScreen extends StatefulWidget {
  const GrantChecklistScreen({super.key, required this.grantId, required this.schemeName});

  final int grantId;
  final String schemeName;

  @override
  State<GrantChecklistScreen> createState() => _GrantChecklistScreenState();
}

class _GrantChecklistScreenState extends State<GrantChecklistScreen> {
  GrantChecklistResponse? data;
  final _checked = <int, bool>{};
  bool loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      data = await ApiService().fetchGrantChecklist(widget.grantId);
    } catch (_) {}
    if (mounted) setState(() => loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.schemeName), backgroundColor: AppTheme.teal),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (data?.deadlineLabel != null)
                  Card(
                    color: Colors.amber.shade50,
                    child: ListTile(
                      leading: const Icon(Icons.schedule, color: Colors.amber),
                      title: Text(data!.deadlineLabel!),
                      subtitle: Text('${data!.agency} · ${data!.contactPhone ?? ''}'),
                    ),
                  ),
                for (var i = 0; i < (data?.checklist.length ?? 0); i++)
                  CheckboxListTile(
                    value: _checked[i] ?? false,
                    onChanged: (v) => setState(() => _checked[i] = v ?? false),
                    title: Text(data!.checklist[i].document),
                    subtitle: data!.checklist[i].tip.isNotEmpty ? Text(data!.checklist[i].tip) : null,
                  ),
              ],
            ),
    );
  }
}
