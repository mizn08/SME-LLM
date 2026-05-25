import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../services/push_notification_service.dart';
import '../theme/app_theme.dart';
import '../utils/constants.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  List<Map<String, dynamic>> _nudges = [];
  bool _loading = true;
  String? _fcmToken;
  bool _registered = false;
  bool _serverFcm = false;
  bool _apiV5Missing = false;
  String? _statusMsg;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final sid = context.read<SessionProvider>().smeId;
    final push = PushNotificationService.instance;
    setState(() {
      _loading = true;
      _statusMsg = null;
      _apiV5Missing = false;
    });
    try {
      final n = await ApiService().fetchNudges(sid);
      _nudges = n.nudges
          .map((e) => {
                'severity': e.severity,
                'title': e.title,
                'body': e.body,
                'action_label': e.actionLabel,
              })
          .toList();
      final reg = await push.registerForSme(sid);
      _registered = reg;
      _fcmToken = push.token;
      _serverFcm = push.serverFcmConfigured;
      final status = await ApiService().fetchNotificationStatus();
      _apiV5Missing = status['api_v5_required'] == true;
      if (_apiV5Missing && _nudges.isEmpty) {
        _statusMsg = 'Showing dashboard alerts (live API is pre-v5).';
      }
    } catch (e) {
      _statusMsg = ApiService.friendlyError(e);
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _testPush() async {
    final sid = context.read<SessionProvider>().smeId;
    setState(() => _statusMsg = 'Sending…');
    try {
      final res = await PushNotificationService.instance.sendTestPush(sid);
      if (!mounted) return;
      if (res['error'] == 'api_v5_required') {
        setState(() => _statusMsg = res['hint'] as String? ?? ApiService.friendlyError(Exception()));
        return;
      }
      setState(() {
        _statusMsg = res['ok'] == true
            ? 'Test push sent (${res['batch']?['success_count'] ?? 0} devices)'
            : 'Send failed: ${res['error'] ?? res['batch']?['error'] ?? 'unknown'}';
      });
    } catch (e) {
      if (mounted) setState(() => _statusMsg = ApiService.friendlyError(e));
    }
  }

  Future<void> _sendNudges() async {
    final sid = context.read<SessionProvider>().smeId;
    setState(() => _statusMsg = 'Sending nudges…');
    try {
      final res = await PushNotificationService.instance.sendNudgesPush(sid);
      if (!mounted) return;
      if (res['error'] == 'api_v5_required') {
        setState(() => _statusMsg = res['hint'] as String? ?? ApiService.friendlyError(Exception()));
        return;
      }
      setState(() {
        _statusMsg = res['ok'] == true
            ? 'Sent ${res['fcm_success_total'] ?? 0} notification(s)'
            : 'Failed: ${res['error'] ?? res['hint'] ?? 'unknown'}';
      });
    } catch (e) {
      if (mounted) setState(() => _statusMsg = ApiService.friendlyError(e));
    }
  }

  Color _color(String severity) {
    switch (severity) {
      case 'critical':
        return Colors.red.shade700;
      case 'warning':
        return Colors.orange.shade800;
      default:
        return AppTheme.teal;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Alerts & Push'),
        backgroundColor: AppTheme.teal,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_apiV5Missing) _apiBanner(),
                  _statusCard(),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: _registered && !_apiV5Missing ? _testPush : null,
                          icon: const Icon(Icons.send_rounded, size: 18),
                          label: const Text('Test push'),
                          style: FilledButton.styleFrom(backgroundColor: AppTheme.teal),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _registered && _serverFcm && !_apiV5Missing ? _sendNudges : null,
                          icon: const Icon(Icons.campaign_outlined, size: 18),
                          label: const Text('Push nudges'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text('In-app alerts', style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 8),
                  if (_nudges.isEmpty)
                    Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        'No alerts right now. Check the Health tab for runway and KPIs.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey.shade600),
                      ),
                    )
                  else
                    ..._nudges.map(
                      (n) => Card(
                        margin: const EdgeInsets.only(bottom: 10),
                        child: ListTile(
                          leading: Icon(Icons.notifications_active, color: _color(n['severity'] as String? ?? 'info')),
                          title: Text(n['title'] as String? ?? ''),
                          subtitle: Text(n['body'] as String? ?? ''),
                        ),
                      ),
                    ),
                ],
              ),
            ),
    );
  }

  Widget _apiBanner() {
    return Card(
      color: Colors.orange.shade50,
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('API update needed for push', style: TextStyle(fontWeight: FontWeight.w700, color: Colors.orange.shade900)),
            const SizedBox(height: 6),
            Text(
              'Connected to: ${resolveApiBase()}\n'
              'That server does not have /notifications yet. Run the local API or redeploy Render.',
              style: TextStyle(fontSize: 12, color: Colors.orange.shade900),
            ),
          ],
        ),
      ),
    );
  }

  Widget _statusCard() {
    final tokenOk = _fcmToken != null;
    return Card(
      color: AppTheme.teal.withOpacity(0.06),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Firebase push', style: TextStyle(fontWeight: FontWeight.w700, color: AppTheme.teal)),
            const SizedBox(height: 8),
            _line('API', resolveApiBase()),
            _line('Device token', tokenOk ? '${_fcmToken!.substring(0, 20)}…' : 'Configure Firebase (see docs/FIREBASE_SETUP.md)'),
            _line('Registered with API', _apiV5Missing ? 'N/A (old API)' : (_registered ? 'Yes' : 'No')),
            _line('Server FCM credentials', _serverFcm ? 'Configured' : 'Not set on server'),
            if (_statusMsg != null) ...[
              const SizedBox(height: 8),
              Text(_statusMsg!, style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _line(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 120, child: Text(k, style: TextStyle(fontSize: 12, color: Colors.grey.shade600))),
            Expanded(child: Text(v, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500))),
          ],
        ),
      );
}
