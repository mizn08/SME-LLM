import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class FinancingTimelineScreen extends StatefulWidget {
  const FinancingTimelineScreen({super.key});

  @override
  State<FinancingTimelineScreen> createState() => _FinancingTimelineScreenState();
}

class _FinancingTimelineScreenState extends State<FinancingTimelineScreen> {
  List<dynamic> _items = [];
  bool loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final sid = context.read<SessionProvider>().smeId;
    try {
      final res = await ApiService().fetchFinancingTimeline(sid);
      _items = res['items'] as List<dynamic>? ?? [];
    } catch (_) {}
    if (mounted) setState(() => loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Financing Timeline'), backgroundColor: AppTheme.teal),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _items.length,
              itemBuilder: (_, i) {
                final item = _items[i] as Map<String, dynamic>;
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Column(
                      children: [
                        const Icon(Icons.circle, size: 12, color: AppTheme.teal),
                        if (i < _items.length - 1) Container(width: 2, height: 48, color: Colors.grey.shade300),
                      ],
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Card(
                        child: ListTile(
                          title: Text(item['title'] as String? ?? ''),
                          subtitle: Text('${item['subtitle']} · ${item['status'] ?? ''}'),
                          trailing: Text((item['created_at'] as String? ?? '').substring(0, 10)),
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
    );
  }
}
