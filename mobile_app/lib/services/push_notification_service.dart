import 'dart:math';

import 'package:flutter/foundation.dart' show kIsWeb;

import 'api_service.dart';

/// Push: FCM when Firebase is configured; otherwise in-app delivery via API (web/local).
class PushNotificationService {
  PushNotificationService._();
  static final PushNotificationService instance = PushNotificationService._();

  final ApiService _api = ApiService();
  final _rng = Random();

  String? _token;
  bool _serverFcm = false;
  bool _inAppMode = true;

  String? get token => _token;
  bool get isReady => _token != null;
  bool get serverFcmConfigured => _serverFcm;
  bool get inAppMode => _inAppMode;

  Future<bool> initialize() async {
    try {
      final status = await _api.fetchNotificationStatus();
      _serverFcm = status['fcm_configured'] == true;
      _inAppMode = status['in_app_push_available'] == true || !_serverFcm;
      return true;
    } catch (_) {
      _serverFcm = false;
      _inAppMode = true;
      return false;
    }
  }

  Future<bool> registerForSme(int smeId) async {
    await initialize();
    if (kIsWeb) {
      _token = 'web-sme-$smeId-${100000 + _rng.nextInt(899999)}';
      final res = await _api.registerPushDevice(smeId: smeId, token: _token!);
      if (res['api_v5_required'] == true) return false;
      return res['status'] == 'ok';
    }
    // Native FCM: add firebase_messaging + google-services per docs/FIREBASE_SETUP.md
    _token = 'demo-sme-$smeId-${100000 + _rng.nextInt(899999)}';
    final res = await _api.registerPushDevice(smeId: smeId, token: _token!);
    if (res['api_v5_required'] == true) return false;
    return res['status'] == 'ok';
  }

  Future<Map<String, dynamic>> sendTestPush(int smeId) async {
    try {
      return await _api.sendTestPush(smeId: smeId);
    } on Exception catch (e) {
      return {'ok': false, 'error': e.toString()};
    }
  }

  Future<Map<String, dynamic>> sendNudgesPush(int smeId) async {
    try {
      return await _api.sendNudgesPush(smeId);
    } on Exception catch (e) {
      return {'ok': false, 'error': e.toString()};
    }
  }
}
