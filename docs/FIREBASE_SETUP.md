# Firebase Cloud Messaging (real push)

## 1. Create Firebase project

1. Open [Firebase Console](https://console.firebase.google.com/) → **Add project** (e.g. `sme-advisor-apc`).
2. Enable **Google Analytics** (optional).

## 2. Android app

1. **Add app** → Android → package name: `com.example.bnpl_advisor_mobile` (must match `android/app/build.gradle.kts`).
2. Download **`google-services.json`** → place at:
   ```
   mobile_app/android/app/google-services.json
   ```
3. Note **API key**, **App ID**, **Sender ID**, **Project ID** from the file or console.

## 3. Web app (optional)

1. **Add app** → Web → register app.
2. Copy config into `mobile_app/web/firebase-messaging-sw.js` (replace `YOUR_*`).
3. **Cloud Messaging** → **Web configuration** → generate **Key pair (VAPID)**.
4. Run with:
   ```bash
   flutter run -d chrome --dart-define=FIREBASE_WEB_API_KEY=... --dart-define=FIREBASE_WEB_APP_ID=... --dart-define=FIREBASE_MESSAGING_SENDER_ID=... --dart-define=FIREBASE_PROJECT_ID=... --dart-define=FIREBASE_WEB_VAPID_KEY=...
   ```

## 4. Backend service account (required to send push)

1. Firebase Console → **Project settings** → **Service accounts** → **Generate new private key** → JSON file.
2. On your API server, set **one** of:

```env
# Path to the JSON file (recommended locally)
FIREBASE_CREDENTIALS_PATH=./firebase-service-account.json

# Or inline JSON (Render/Heroku — paste minified JSON as one line)
FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
```

3. Restart the API. Check: `GET /notifications/status` → `"fcm_configured": true`.

**Render:** add env var `FIREBASE_CREDENTIALS_JSON` with the full JSON (escape quotes or use Render secret file).

## 5. Run Flutter with Firebase config

### Option A — FlutterFire CLI (recommended)

```bash
cd mobile_app
dart pub global activate flutterfire_cli
flutterfire configure
```

This generates `lib/firebase_options.dart` with real values.

### Option B — dart-define (no committed secrets)

```bash
flutter run --dart-define=FIREBASE_ANDROID_API_KEY=AIza... \
  --dart-define=FIREBASE_ANDROID_APP_ID=1:123:android:abc \
  --dart-define=FIREBASE_MESSAGING_SENDER_ID=123456789 \
  --dart-define=FIREBASE_PROJECT_ID=sme-advisor-apc
```

## 6. Test end-to-end

1. Start API with `FIREBASE_CREDENTIALS_PATH` set.
2. Run app on **physical Android device** (emulator FCM can be flaky).
3. Open **Alerts & Push** (bell icon) → status should show device token + **Registered: Yes**.
4. Tap **Test push** → notification should appear.
5. Tap **Push nudges** → sends runway/grant alerts via FCM.

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/notifications/register` | Save FCM token for SME |
| POST | `/notifications/test` | Send test message |
| POST | `/notifications/send?sme_id=1` | Push current nudges |
| GET | `/notifications/status` | Server FCM configured? |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `firebase_not_configured` | Set service account env on backend |
| No device token | Add `google-services.json`, rebuild app |
| Token but no notification | Enable Cloud Messaging API in Google Cloud Console |
| Web only | Set VAPID key + update `firebase-messaging-sw.js` |

Do **not** commit `google-services.json` or service account JSON to public repos — add to `.gitignore`.
