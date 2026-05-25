import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';

import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class PitchScreen extends StatefulWidget {
  const PitchScreen({super.key});

  @override
  State<PitchScreen> createState() => _PitchScreenState();
}

class _PitchScreenState extends State<PitchScreen> {
  String _lang = 'en';
  String _tone = 'formal';
  String? _letter;
  bool _loading = false;

  Future<void> _generate() async {
    setState(() => _loading = true);
    try {
      final sid = context.read<SessionProvider>().smeId;
      final letter = await ApiService().generatePitch(smeId: sid, lang: _lang, tone: _tone);
      if (mounted) setState(() => _letter = letter);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pitch Generator'), backgroundColor: AppTheme.teal),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'en', label: Text('English')),
              ButtonSegment(value: 'ms', label: Text('Bahasa')),
            ],
            selected: {_lang},
            onSelectionChanged: (s) => setState(() => _lang = s.first),
          ),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'formal', label: Text('Formal')),
              ButtonSegment(value: 'friendly', label: Text('Friendly')),
            ],
            selected: {_tone},
            onSelectionChanged: (s) => setState(() => _tone = s.first),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _loading ? null : _generate,
            child: _loading ? const CircularProgressIndicator() : const Text('Generate pitch letter'),
          ),
          if (_letter != null) ...[
            const SizedBox(height: 16),
            PremiumCard(
              child: SelectableText(_letter!),
            ),
            Row(
              children: [
                TextButton.icon(
                  icon: const Icon(Icons.copy),
                  label: const Text('Copy'),
                  onPressed: () => Clipboard.setData(ClipboardData(text: _letter!)),
                ),
                TextButton.icon(
                  icon: const Icon(Icons.share),
                  label: const Text('Share'),
                  onPressed: () => Share.share(_letter!),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
