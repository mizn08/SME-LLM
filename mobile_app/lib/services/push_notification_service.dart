import 'api_service.dart';

/// Push notifications (FCM) are optional — enable via docs/FIREBASE_SETUP.md on mobile builds.
/// Web and default builds use API nudges only so Render `flutter build web` stays reliable.
class PushNotificationService {
  PushNotificationService._();
  static final PushNotificationService instance = PushNotificationService._();

  final ApiService _api = ApiService();

  String? get token => null;
  bool get isReady => false;
  bool get serverFcmConfigured => false;

  Future<bool> initialize() async {
    try {
      final status = await _api.fetchNotificationStatus();
      return status['fcm_configured'] == true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> registerForSme(int smeId) async => false;

  Future<Map<String, dynamic>> sendTestPush(int smeId) async => {
        'status': 'skipped',
        'reason': 'fcm_not_enabled_in_this_build',
      };

  Future<Map<String, dynamic>> sendNudgesPush(int smeId) async {
    try {
      return await _api.sendNudgesPush(smeId);
    } catch (e) {
      return {'status': 'error', 'detail': e.toString()};
    }
  }
}
