import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// Data import — accepts any file; server stores and preprocesses later.
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
  bool _canReprocess = false;

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
        type: FileType.any,
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
        throw Exception('Could not read the selected file. Try again or use a smaller file.');
      }
      final body = await ApiService().uploadFileBytes(
        smeId: sid,
        bytes: file.bytes!,
        fileName: file.name,
      );

      setState(() {
        progress = 1;
        report = _reportLines(body);
        _canReprocess = (body['transactions_imported'] as int? ?? 0) == 0;
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

  Future<void> _reprocessSaved() async {
    setState(() {
      err = null;
      report = [];
      busy = true;
    });
    try {
      final sid = context.read<SessionProvider>().smeId;
      final body = await ApiService().reprocessUploads(sid);
      setState(() {
        report = _reportLines(body);
        _canReprocess = (body['transactions_imported'] as int? ?? 0) == 0;
      });
    } catch (e) {
      setState(() => err = _friendlyError(e));
    } finally {
      setState(() => busy = false);
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
      final body = await ApiService().uploadFileBytes(
        smeId: sid,
        bytes: bytes,
        fileName: 'sample_transactions.csv',
      );
      setState(() {
        report = _reportLines(body);
        _canReprocess = false;
      });
    } catch (e) {
      setState(() => err = _friendlyError(e));
    } finally {
      setState(() => busy = false);
    }
  }

  List<String> _reportLines(Map<String, dynamic> body) {
    final status = body['status'] as String? ?? 'stored';
    final imported = body['transactions_imported'] as int? ?? 0;
    final lines = List<String>.from(
      (body['cleaning_report'] as List<dynamic>? ?? []).map((e) => '$e'),
    );
    if (status == 'imported' && imported > 0) {
      lines.insert(0, 'Imported $imported transactions.');
    } else {
      lines.insert(0, 'File received — preprocessing will run on the server.');
    }
    return lines;
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
                if (_canReprocess) ...[const SizedBox(height: 12), _buildReprocessAction()],
                if (report.isNotEmpty) ...[const SizedBox(height: 32), _buildSuccessReport()],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return const Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'DATA IMPORT',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
            color: AppTheme.teal,
            decoration: TextDecoration.none,
          ),
        ),
        SizedBox(height: 10),
        Text('Upload transactions', style: _titleStyle),
        SizedBox(height: 10),
        Text(
          'Upload any bookkeeping export (CSV, Excel, PDF, etc.). '
          'We save it on the server and preprocess it to refresh your KPIs.',
          style: _bodyStyle,
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
                'Uploading…',
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
        label: const Text('Choose file'),
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

  Widget _buildReprocessAction() {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: busy ? null : _reprocessSaved,
        icon: const Icon(Icons.sync_rounded, size: 18),
        label: const Text('Import saved files'),
        style: OutlinedButton.styleFrom(
          foregroundColor: AppTheme.teal,
          side: const BorderSide(color: AppTheme.teal),
          padding: const EdgeInsets.symmetric(vertical: 14),
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
                'Upload complete',
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
            'Open Health and pull down to refresh — KPIs update after import.',
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
