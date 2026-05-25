import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/lead_score.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/lead_score_meter.dart';

class LeadScoreScreen extends StatefulWidget {
  const LeadScoreScreen({super.key});

  @override
  State<LeadScoreScreen> createState() => _LeadScoreScreenState();
}

class _LeadScoreScreenState extends State<LeadScoreScreen> {
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
      final res = await ApiService().fetchLeadScores(sid);
      if (mounted) {
        setState(() {
          _scores = res.scores;
          loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => loading = false);
    }
  }

  List<LeadScoreItem> _scores = [];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Lead Scores'), backgroundColor: AppTheme.teal),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : PremiumCard(
              margin: const EdgeInsets.all(16),
              child: Column(
                children: [
                  for (final s in _scores)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: LeadScoreMeter(item: s),
                    ),
                ],
              ),
            ),
    );
  }
}
