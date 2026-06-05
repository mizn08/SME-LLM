import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// Shows the active SME profile from the API (synced with drawer + Quick Profile).
class ActiveProfileBadge extends StatefulWidget {
  const ActiveProfileBadge({super.key, this.compact = false, this.dense = false});

  final bool compact;
  final bool dense;

  @override
  State<ActiveProfileBadge> createState() => _ActiveProfileBadgeState();
}

class _ActiveProfileBadgeState extends State<ActiveProfileBadge> {
  int? _loadedSmeId;
  String? _businessName;
  String? _industry;
  bool _loading = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final sid = context.read<SessionProvider>().smeId;
    if (sid != _loadedSmeId && !_loading) {
      _load(sid);
    }
  }

  Future<void> _load(int smeId) async {
    setState(() => _loading = true);
    try {
      final profile = await ApiService().fetchSmeProfile(smeId);
      if (!mounted || context.read<SessionProvider>().smeId != smeId) return;
      setState(() {
        _loadedSmeId = smeId;
        _businessName = profile['business_name'] as String? ?? 'SME #$smeId';
        _industry = profile['industry'] as String? ?? '';
      });
    } catch (_) {
      if (!mounted || context.read<SessionProvider>().smeId != smeId) return;
      setState(() {
        _loadedSmeId = smeId;
        _businessName = 'SME #$smeId';
        _industry = '';
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    context.watch<SessionProvider>();
    final sid = context.read<SessionProvider>().smeId;
    if (sid != _loadedSmeId && !_loading) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && context.read<SessionProvider>().smeId == sid) {
          _load(sid);
        }
      });
    }

    final name = _businessName ?? 'Loading…';
    final industry = _industry ?? '';

    if (widget.compact) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: AppTheme.accentWash,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppTheme.borderColor),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.storefront_rounded, size: 14, color: AppTheme.brandBlue),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                name,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.brandBlueDark),
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      width: double.infinity,
      margin: widget.dense ? EdgeInsets.zero : const EdgeInsets.fromLTRB(12, 8, 12, 0),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.accentWash,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.borderColor),
            ),
            child: const Icon(Icons.storefront_rounded, size: 18, color: AppTheme.brandBlue),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Active profile',
                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: AppTheme.mutedForeground, letterSpacing: 0.4),
                ),
                const SizedBox(height: 2),
                Text(
                  name,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppTheme.textPrimary),
                  overflow: TextOverflow.ellipsis,
                ),
                if (industry.isNotEmpty)
                  Text(
                    industry,
                    style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
          ),
          if (_loading)
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.brandBlue),
            )
          else
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: AppTheme.successBg,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'ID $sid',
                style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTheme.successFg),
              ),
            ),
        ],
      ),
    );
  }
}
