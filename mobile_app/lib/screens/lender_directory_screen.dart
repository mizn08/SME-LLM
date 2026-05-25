import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/lender.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class LenderDirectoryScreen extends StatefulWidget {
  const LenderDirectoryScreen({super.key});

  @override
  State<LenderDirectoryScreen> createState() => _LenderDirectoryScreenState();
}

class _LenderDirectoryScreenState extends State<LenderDirectoryScreen> {
  List<LenderItem> _lenders = [];
  bool _islamicOnly = false;
  String _query = '';
  bool loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => loading = true);
    try {
      final sid = context.read<SessionProvider>().smeId;
      _lenders = await ApiService().fetchMatchedLenders(sid, islamicOnly: _islamicOnly);
    } catch (_) {}
    if (mounted) setState(() => loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _lenders
        .where((l) => l.name.toLowerCase().contains(_query.toLowerCase()))
        .toList();
    return Scaffold(
      appBar: AppBar(title: const Text('Lender Directory'), backgroundColor: AppTheme.teal),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search lenders'),
              onChanged: (v) => setState(() => _query = v),
            ),
          ),
          SwitchListTile(
            title: const Text('Islamic finance only'),
            value: _islamicOnly,
            onChanged: (v) {
              setState(() => _islamicOnly = v);
              _load();
            },
          ),
          Expanded(
            child: loading
                ? const Center(child: CircularProgressIndicator())
                : ListView.builder(
                    itemCount: filtered.length,
                    itemBuilder: (_, i) {
                      final l = filtered[i];
                      return Card(
                        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                        child: ListTile(
                          title: Text(l.name),
                          subtitle: Text(l.typicalRateLabel),
                          trailing: l.islamicCompliant
                              ? const Chip(label: Text('Islamic', style: TextStyle(fontSize: 10)))
                              : null,
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
