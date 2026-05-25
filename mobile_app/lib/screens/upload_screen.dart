import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// CSV upload — minimalist layout aligned with Nielsen usability heuristics.
class UploadScreen extends StatefulWidget {
  const UploadScreen({super.key});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  static const _bodyStyle = TextStyle(
    fontSize: 14,
    height: 1.5,
    color: AppTheme.textSecondary,
    fontWeight: FontWeight.w400,
    decoration: TextDecoration.none,
  );

  static const _titleStyle = TextStyle(
    fontSize: 22,
    height: 1.25,
    fontWeight: FontWeight.w600,
    color: AppTheme.textPrimary,
    letterSpacing: -0.2,
    decoration: TextDecoration.none,
  );

  double? progress;
  List<String> report = [];
  String? err;
  bool busy = false;
  bool _showFormatHelp = false;

  Future<void> _pickAndUpload() async {
    setState(() {
      err = null;
      report = [];
      busy = true;
      progress = 0.1;
    });
    try {
      final sid = context.read<SessionProvider>().smeId;
      final res = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv'],
        withData: true,
      );
      if (res == null || res.files.isEmpty) {
        setState(() {
          busy = false;
          progress = null;
        });
        return;
      }
      setState(() => progress = 0.45);
      final file = res.files.single;

      if (file.bytes == null) {
        throw Exception('Could not read the selected file. Try again or use a smaller CSV.');
      }
      final body = await ApiService().uploadCsvBytes(
        smeId: sid,
        bytes: file.bytes!,
        fileName: file.name,
      );

      setState(() {
        progress = 1;
        report = List<String>.from((body['cleaning_report'] as List<dynamic>? ?? []).map((e) => '$e'));
        report.insert(0, 'Imported ${body['transactions_imported']} transactions.');
      });
    } catch (e) {
      setState(() => err = _friendlyError(e));
    } finally {
      setState(() {
        busy = false;
        progress = null;
      });
    }
  }

  Future<void> _uploadBundledSample() async {
    setState(() {
      err = null;
      report = [];
      busy = true;
    });
    try {
      final sid = context.read<SessionProvider>().smeId;
      final data = await rootBundle.loadString('assets/sample_transactions.csv');
      final bytes = Uint8List.fromList(data.codeUnits);
      final body = await ApiService().uploadCsvBytes(
        smeId: sid,
        bytes: bytes,
        fileName: 'sample_transactions.csv',
      );
      setState(() {
        report = List<String>.from((body['cleaning_report'] as List<dynamic>? ?? []).map((e) => '$e'));
        report.insert(0, 'Imported ${body['transactions_imported']} rows from sample data.');
      });
    } catch (e) {
      setState(() => err = _friendlyError(e));
    } finally {
      setState(() => busy = false);
    }
  }

  String _friendlyError(Object e) {
    final msg = e.toString();
    if (msg.contains('SocketException') || msg.contains('Connection')) {
      return 'Cannot reach the server. Check that the API is running and your connection is correct.';
    }
    return msg.replaceFirst('Exception: ', '');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFAFBFC),
      appBar: AppBar(
        backgroundColor: Colors.white,
        foregroundColor: AppTheme.textPrimary,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        title: const Text(
          'Upload',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w600,
            color: AppTheme.textPrimary,
            decoration: TextDecoration.none,
          ),
        ),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: Colors.grey.shade200),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
              children: [
                _buildHeader(),
                const SizedBox(height: 28),
                if (busy) _buildStatusBanner(),
                if (err != null) ...[const SizedBox(height: 16), _buildErrorCard()],
                const SizedBox(height: 24),
                _buildPrimaryAction(),
                const SizedBox(height: 12),
                _buildSecondaryAction(),
                if (report.isNotEmpty) ...[const SizedBox(height: 32), _buildSuccessReport()],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'DATA IMPORT',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
            color: AppTheme.teal,
            decoration: TextDecoration.none,
          ),
        ),
        const SizedBox(height: 10),
        const Text('Upload transactions', style: _titleStyle),
        const SizedBox(height: 10),
        const Text(
          'Import your bookkeeping CSV to refresh KPIs and recommendations.',
          style: _bodyStyle,
        ),
        const SizedBox(height: 20),
        _FormatHelpCard(
          expanded: _showFormatHelp,
          onToggle: () => setState(() => _showFormatHelp = !_showFormatHelp),
        ),
      ],
    );
  }

  Widget _buildStatusBanner() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppTheme.teal,
                  value: progress,
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                'Uploading and validating…',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.textPrimary,
                  decoration: TextDecoration.none,
                ),
              ),
            ],
          ),
          if (progress != null) ...[
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 4,
                backgroundColor: AppTheme.teal.withOpacity(0.08),
                color: AppTheme.teal,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildErrorCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF5F5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFFECACA)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline_rounded, color: Colors.red.shade700, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              err!,
              style: TextStyle(
                fontSize: 13,
                height: 1.45,
                color: Colors.red.shade900,
                decoration: TextDecoration.none,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPrimaryAction() {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: FilledButton.icon(
        onPressed: busy ? null : _pickAndUpload,
        icon: const Icon(Icons.upload_file_rounded, size: 20),
        label: const Text('Choose CSV file'),
        style: FilledButton.styleFrom(
          backgroundColor: AppTheme.teal,
          foregroundColor: Colors.white,
          disabledBackgroundColor: AppTheme.teal.withOpacity(0.4),
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            decoration: TextDecoration.none,
          ),
        ),
      ),
    );
  }

  Widget _buildSecondaryAction() {
    return TextButton.icon(
      onPressed: busy ? null : _uploadBundledSample,
      icon: const Icon(Icons.play_circle_outline_rounded, size: 18),
      label: const Text('Try sample data instead'),
      style: TextButton.styleFrom(
        foregroundColor: AppTheme.teal,
        padding: const EdgeInsets.symmetric(vertical: 12),
        textStyle: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          decoration: TextDecoration.none,
        ),
      ),
    );
  }

  Widget _buildSuccessReport() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.accentGreen.withOpacity(0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.check_circle_rounded, color: AppTheme.accentGreen, size: 22),
              SizedBox(width: 10),
              Text(
                'Import complete',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textPrimary,
                  decoration: TextDecoration.none,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          for (final line in report)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                line,
                style: const TextStyle(
                  fontSize: 13,
                  height: 1.4,
                  color: AppTheme.textSecondary,
                  decoration: TextDecoration.none,
                ),
              ),
            ),
          const SizedBox(height: 8),
          Text(
            'Open Health to view updated KPIs.',
            style: TextStyle(
              fontSize: 13,
              color: AppTheme.teal,
              fontWeight: FontWeight.w500,
              decoration: TextDecoration.none,
            ),
          ),
        ],
      ),
    );
  }
}

class _FormatHelpCard extends StatelessWidget {
  const _FormatHelpCard({required this.expanded, required this.onToggle});

  final bool expanded;
  final VoidCallback onToggle;

  static const _columns = [
    ('date', 'Required'),
    ('amount', 'Required'),
    ('category', 'Required'),
    ('description', 'Optional'),
    ('is_expense', 'Optional'),
  ];

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      child: InkWell(
        onTap: onToggle,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.help_outline_rounded, size: 18, color: Colors.grey.shade600),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'CSV format',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textPrimary,
                        decoration: TextDecoration.none,
                      ),
                    ),
                  ),
                  Icon(
                    expanded ? Icons.expand_less_rounded : Icons.expand_more_rounded,
                    color: Colors.grey.shade600,
                  ),
                ],
              ),
              if (expanded) ...[
                const SizedBox(height: 14),
                const Text(
                  'Use these column headers (case-insensitive):',
                  style: TextStyle(
                    fontSize: 13,
                    color: AppTheme.textSecondary,
                    decoration: TextDecoration.none,
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final (name, tag) in _columns) _ColumnChip(name: name, tag: tag),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _ColumnChip extends StatelessWidget {
  const _ColumnChip({required this.name, required this.tag});

  final String name;
  final String tag;

  @override
  Widget build(BuildContext context) {
    final required = tag == 'Required';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: required ? AppTheme.teal.withOpacity(0.08) : Colors.grey.shade100,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            name,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              fontFamily: 'monospace',
              color: required ? AppTheme.teal : AppTheme.textSecondary,
              decoration: TextDecoration.none,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            tag,
            style: TextStyle(
              fontSize: 10,
              color: required ? AppTheme.teal : Colors.grey.shade600,
              decoration: TextDecoration.none,
            ),
          ),
        ],
      ),
    );
  }
}
