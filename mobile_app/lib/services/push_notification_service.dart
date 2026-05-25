import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../firebase_options.dart';
import 'api_service.dart';

/// Background FCM handler (must be top-level).
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
}

class PushNotificationService {
  PushNotificationService._();
  static final PushNotificationService instance = PushNotificationService._();

  final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _local = FlutterLocalNotificationsPlugin();
  final ApiService _api = ApiService();

  bool _initialized = false;
  String? _token;
  bool _fcmConfiguredOnServer = false;

  String? get token => _token;
  bool get isReady => _initialized && _token != null;
  bool get serverFcmConfigured => _fcmConfiguredOnServer;

  Future<bool> initialize() async {
    if (_initialized) return _token != null;
    if (!DefaultFirebaseOptions.isConfigured) {
      if (kDebugMode) {
        debugPrint('Firebase: not configured — use docs/FIREBASE_SETUP.md');
      }
      return false;
    }
    try {
      await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
      FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

      if (!kIsWeb) {
        await _messaging.requestPermission(alert: true, badge: true, sound: true);
      }

      await _setupLocalNotifications();
      _token = await _messaging.getToken();
      if (kIsWeb) {
        // Web may need VAPID key — set in Firebase console → Cloud Messaging → Web configuration
        _token ??= await _messaging.getToken(
          vapidKey: const String.fromEnvironment('FIREBASE_WEB_VAPID_KEY', defaultValue: ''),
        );
      }

      FirebaseMessaging.onMessage.listen(_onForegroundMessage);
      FirebaseMessaging.onMessageOpenedApp.listen(_onOpenedApp);
      _messaging.onTokenRefresh.listen((t) {
        _token = t;
      });

      try {
        final status = await _api.fetchNotificationStatus();
        _fcmConfiguredOnServer = status['fcm_configured'] == true;
      } catch (_) {}

      _initialized = true;
      return _token != null;
    } catch (e, st) {
      if (kDebugMode) debugPrint('Firebase init error: $e\n$st');
      return false;
    }
  }

  Future<void> _setupLocalNotifications() async {
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const init = InitializationSettings(android: android);
    await _local.initialize(init);
    const channel = AndroidNotificationChannel(
      'sme_advisor_alerts',
      'SME Advisor Alerts',
      description: 'Cash runway, grants, and financing nudges',
      importance: Importance.high,
    );
    await _local
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);
  }

  Future<void> _onForegroundMessage(RemoteMessage message) async {
    final n = message.notification;
    if (n == null) return;
    await _local.show(
      message.hashCode,
      n.title,
      n.body,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'sme_advisor_alerts',
          'SME Advisor Alerts',
          importance: Importance.high,
          priority: Priority.high,
        ),
      ),
    );
  }

  void _onOpenedApp(RemoteMessage message) {
    if (kDebugMode) debugPrint('Notification opened: ${message.data}');
  }

  Future<bool> registerForSme(int smeId) async {
    if (_token == null) {
      final ok = await initialize();
      if (!ok || _token == null) return false;
    }
    try {
      final res = await _api.registerPushDevice(smeId: smeId, token: _token!);
      if (res['api_v5_required'] == true) return false;
      _fcmConfiguredOnServer = res['fcm_configured'] == true;
      return res['status'] == 'ok';
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> sendTestPush(int smeId) async {
    return _api.sendTestPush(smeId: smeId);
  }

  Future<Map<String, dynamic>> sendNudgesPush(int smeId) async {
    return _api.sendNudgesPush(smeId);
  }
}
