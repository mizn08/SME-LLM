import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/digest.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class DigestScreen extends StatefulWidget {
  const DigestScreen({super.key});

  @override
  State<DigestScreen> createState() => _DigestScreenState();
}

class _DigestScreenState extends State<DigestScreen> {
  bool loading = true;
  DigestResponse? _digest;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final sid = context.read<SessionProvider>().smeId;
    try {
      _digest = await ApiService().fetchDigest(sid);
    } catch (_) {}
    if (mounted) setState(() => loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final fmt = NumberFormat.currency(symbol: 'RM ', decimalDigits: 0);
    return Scaffold(
      appBar: AppBar(title: const Text('Weekly Digest'), backgroundColor: AppTheme.teal),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : _digest == null
              ? const Center(child: Text('Could not load digest'))
              : Padding(
              padding: const EdgeInsets.all(16),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(_digest!.weekLabel, style: const TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 8),
                      Text(_digest!.summary),
                      const Divider(),
                      for (final e in _digest!.events)
                        ListTile(
                          leading: const Icon(Icons.event, color: AppTheme.teal),
                          title: Text(e.title),
                          subtitle: Text(e.detail),
                          trailing: e.amountRm != null ? Text(fmt.format(e.amountRm)) : null,
                        ),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}
