import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
  final _api = ApiService();
  final _searchCtrl = TextEditingController();
  List<LenderItem> _lenders = [];
  bool _islamicOnly = false;
  bool _loading = true;
  String? _err;
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _searchCtrl.addListener(_onSearchChanged);
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchCtrl.dispose();
    super.dispose();
  }

  void _onSearchChanged() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), _load);
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _err = null;
    });
    try {
      final sid = context.read<SessionProvider>().smeId;
      final q = _searchCtrl.text.trim();
      final list = await _api.fetchMatchedLenders(
        sid,
        islamicOnly: _islamicOnly,
        query: q.isEmpty ? null : q,
      );
      if (!mounted) return;
      setState(() => _lenders = list);
    } catch (e) {
      if (mounted) setState(() => _err = ApiService.friendlyError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _copyApplyLink(String url) {
    Clipboard.setData(ClipboardData(text: url));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Link copied: $url')),
    );
  }

  String _typeLabel(String t) {
    switch (t) {
      case 'bnpl':
        return 'BNPL';
      case 'grant':
        return 'Grant';
      case 'islamic':
        return 'Islamic';
      case 'micro_credit':
        return 'Micro-credit';
      default:
        return t;
    }
  }

  Color _typeColor(String t) {
    switch (t) {
      case 'grant':
        return Colors.green.shade700;
      case 'bnpl':
        return Colors.blue.shade700;
      case 'islamic':
        return Colors.teal.shade800;
      default:
        return Colors.grey.shade700;
    }
  }

  @override
  Widget build(BuildContext context) {
    final q = _searchCtrl.text.trim();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Lender Directory'),
        backgroundColor: AppTheme.teal,
        foregroundColor: Colors.white,
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
            child: TextField(
              controller: _searchCtrl,
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search),
                hintText: 'Search MADANI, grant, BNPL, MARA, MDEC…',
                suffixIcon: q.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchCtrl.clear();
                          _load();
                        },
                      )
                    : null,
                border: const OutlineInputBorder(),
              ),
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
          if (_err != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(_err!, style: TextStyle(color: Colors.red.shade700, fontSize: 12)),
            ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                _loading
                    ? 'Searching…'
                    : '${_lenders.length} lender${_lenders.length == 1 ? '' : 's'}'
                        '${q.isNotEmpty ? ' for "$q"' : ' (matched to your SME)'}',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
            ),
          ),
          Expanded(
            child: _loading && _lenders.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : _lenders.isEmpty
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Text(
                            q.isEmpty
                                ? 'No lenders matched yet. Upload transactions on Health or turn off Islamic-only filter.'
                                : 'No results for "$q". Try: madani, grant, tekun, bnpl, mara, mdec.',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Colors.grey.shade600),
                          ),
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.only(bottom: 16),
                        itemCount: _lenders.length,
                        itemBuilder: (_, i) => _lenderCard(_lenders[i]),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _lenderCard(LenderItem l) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    l.name,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                  ),
                ),
                Chip(
                  label: Text(_typeLabel(l.productType), style: const TextStyle(fontSize: 10)),
                  backgroundColor: _typeColor(l.productType).withOpacity(0.12),
                  side: BorderSide.none,
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(l.typicalRateLabel, style: TextStyle(fontSize: 13, color: Colors.grey.shade800)),
            if (l.maxAmountRm != null)
              Text(
                'Up to RM ${l.maxAmountRm!.toStringAsFixed(0)}',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
              ),
            if (l.notes.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(l.notes, style: TextStyle(fontSize: 12, color: Colors.grey.shade600, height: 1.35)),
            ],
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              children: [
                if (l.islamicCompliant)
                  const Chip(
                    label: Text('Islamic', style: TextStyle(fontSize: 10)),
                    visualDensity: VisualDensity.compact,
                  ),
                if (l.bumiputeraPreferred)
                  const Chip(
                    label: Text('Bumiputera', style: TextStyle(fontSize: 10)),
                    visualDensity: VisualDensity.compact,
                  ),
              ],
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () => _copyApplyLink(l.applyUrl),
                icon: const Icon(Icons.open_in_new, size: 16),
                label: const Text('Copy apply link'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
