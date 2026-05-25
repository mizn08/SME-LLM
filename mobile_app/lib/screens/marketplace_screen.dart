import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class MarketplaceScreen extends StatefulWidget {
  const MarketplaceScreen({super.key});

  @override
  State<MarketplaceScreen> createState() => _MarketplaceScreenState();
}

class _MarketplaceScreenState extends State<MarketplaceScreen> {
  List<Map<String, dynamic>> _providers = [];
  bool _loading = true;
  bool _bnplOnly = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _providers = await ApiService().fetchMarketplace(bnplOnly: _bnplOnly);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('BNPL Marketplace'),
        backgroundColor: AppTheme.teal,
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: true, label: Text('BNPL')),
                ButtonSegment(value: false, label: Text('All')),
              ],
              selected: {_bnplOnly},
              onSelectionChanged: (s) {
                _bnplOnly = s.first;
                _load();
              },
            ),
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: _providers.length,
                      itemBuilder: (_, i) {
                        final p = _providers[i];
                        final tenure = p['max_tenure_months'];
                        return Card(
                          margin: const EdgeInsets.only(bottom: 12),
                          child: Padding(
                            padding: const EdgeInsets.all(14),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        p['plan_label'] as String? ?? p['name'] as String? ?? '',
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w700,
                                          fontSize: 15,
                                        ),
                                      ),
                                    ),
                                    if (tenure != null)
                                      Chip(
                                        label: Text('$tenure mo'),
                                        visualDensity: VisualDensity.compact,
                                      ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  p['description'] as String? ?? '',
                                  style: TextStyle(fontSize: 13, color: Colors.grey.shade700, height: 1.4),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Max RM ${p['max_amount_rm']} · ${p['type']}',
                                  style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
                                ),
                                Align(
                                  alignment: Alignment.centerRight,
                                  child: TextButton.icon(
                                    onPressed: () {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(
                                          content: Text('Apply: ${p['apply_url']}'),
                                          duration: const Duration(seconds: 4),
                                        ),
                                      );
                                    },
                                    icon: const Icon(Icons.open_in_new, size: 16),
                                    label: const Text('Apply'),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}
