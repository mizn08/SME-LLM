// Firebase options — replace via FlutterFire CLI or --dart-define (see docs/FIREBASE_SETUP.md).
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static bool get isConfigured {
    const key = String.fromEnvironment('FIREBASE_ANDROID_API_KEY', defaultValue: '');
    if (key.isNotEmpty && !key.startsWith('YOUR_')) return true;
    if (kIsWeb) {
      const wk = String.fromEnvironment('FIREBASE_WEB_API_KEY', defaultValue: '');
      return wk.isNotEmpty && !wk.startsWith('YOUR_');
    }
    return false;
  }

  static FirebaseOptions get currentPlatform {
    if (kIsWeb) return web;
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      case TargetPlatform.macOS:
        return macos;
      default:
        return android;
    }
  }

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: String.fromEnvironment('FIREBASE_WEB_API_KEY', defaultValue: 'YOUR_WEB_API_KEY'),
    appId: String.fromEnvironment('FIREBASE_WEB_APP_ID', defaultValue: 'YOUR_WEB_APP_ID'),
    messagingSenderId: String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID', defaultValue: 'YOUR_SENDER_ID'),
    projectId: String.fromEnvironment('FIREBASE_PROJECT_ID', defaultValue: 'YOUR_PROJECT_ID'),
    authDomain: String.fromEnvironment('FIREBASE_AUTH_DOMAIN', defaultValue: 'YOUR_PROJECT_ID.firebaseapp.com'),
    storageBucket: String.fromEnvironment('FIREBASE_STORAGE_BUCKET', defaultValue: 'YOUR_PROJECT_ID.appspot.com'),
  );

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: String.fromEnvironment('FIREBASE_ANDROID_API_KEY', defaultValue: 'YOUR_ANDROID_API_KEY'),
    appId: String.fromEnvironment('FIREBASE_ANDROID_APP_ID', defaultValue: 'YOUR_ANDROID_APP_ID'),
    messagingSenderId: String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID', defaultValue: 'YOUR_SENDER_ID'),
    projectId: String.fromEnvironment('FIREBASE_PROJECT_ID', defaultValue: 'YOUR_PROJECT_ID'),
    storageBucket: String.fromEnvironment('FIREBASE_STORAGE_BUCKET', defaultValue: 'YOUR_PROJECT_ID.appspot.com'),
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: String.fromEnvironment('FIREBASE_IOS_API_KEY', defaultValue: 'YOUR_IOS_API_KEY'),
    appId: String.fromEnvironment('FIREBASE_IOS_APP_ID', defaultValue: 'YOUR_IOS_APP_ID'),
    messagingSenderId: String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID', defaultValue: 'YOUR_SENDER_ID'),
    projectId: String.fromEnvironment('FIREBASE_PROJECT_ID', defaultValue: 'YOUR_PROJECT_ID'),
    storageBucket: String.fromEnvironment('FIREBASE_STORAGE_BUCKET', defaultValue: 'YOUR_PROJECT_ID.appspot.com'),
    iosBundleId: 'com.example.bnplAdvisorMobile',
  );

  static const FirebaseOptions macos = ios;
}
