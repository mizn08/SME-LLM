/// Web/desktop stub — FCM is mobile-only; API nudges still work in-app.
class PushNotificationService {
  PushNotificationService._();
  static final PushNotificationService instance = PushNotificationService._();

  String? get token => null;
  bool get isReady => false;
  bool get serverFcmConfigured => false;

  Future<bool> initialize() async => false;

  Future<bool> registerForSme(int smeId) async => false;

  Future<Map<String, dynamic>> sendTestPush(int smeId) async => {
        'status': 'skipped',
        'reason': 'push_not_supported_on_web',
      };

  Future<Map<String, dynamic>> sendNudgesPush(int smeId) async => {
        'status': 'skipped',
        'reason': 'push_not_supported_on_web',
      };
}
