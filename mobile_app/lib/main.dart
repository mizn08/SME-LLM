import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:local_auth/local_auth.dart';
import 'package:provider/provider.dart';

import 'providers/advisor_nav_provider.dart';
import 'providers/recommendation_provider.dart';
import 'providers/settings_provider.dart';
import 'providers/session_provider.dart';
import 'screens/profile_quiz_screen.dart';
import 'screens/shell_screen.dart';
import 'services/push_notification_service.dart';
import 'theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await PushNotificationService.instance.initialize();
  final session = SessionProvider();
  final settings = SettingsProvider();
  await session.load();
  await settings.load();
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<SessionProvider>.value(value: session),
        ChangeNotifierProvider<SettingsProvider>.value(value: settings),
        ChangeNotifierProvider(create: (_) => RecommendationProvider()),
        ChangeNotifierProvider(create: (_) => AdvisorNavProvider()),
      ],
      child: const BnplAdvisorApp(),
    ),
  );
}

class BnplAdvisorApp extends StatelessWidget {
  const BnplAdvisorApp({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    return MaterialApp(
      title: 'SME Advisor',
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: settings.themeMode,
      locale: settings.locale,
      supportedLocales: const [Locale('en'), Locale('ms')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, child) {
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(settings.textScale)),
          child: child ?? const SizedBox.shrink(),
        );
      },
      home: _RootGate(settings: settings),
      debugShowCheckedModeBanner: false,
    );
  }
}

class _RootGate extends StatefulWidget {
  const _RootGate({required this.settings});
  final SettingsProvider settings;

  @override
  State<_RootGate> createState() => _RootGateState();
}

class _RootGateState extends State<_RootGate> {
  bool? _unlocked;

  @override
  void initState() {
    super.initState();
    _checkBio();
  }

  Future<void> _checkBio() async {
    if (!widget.settings.biometricEnabled || kIsWeb) {
      setState(() => _unlocked = true);
      return;
    }
    final auth = LocalAuthentication();
    final ok = await auth.authenticate(
      localizedReason: 'Unlock SME Advisor',
      options: const AuthenticationOptions(biometricOnly: true),
    );
    setState(() => _unlocked = ok);
  }

  @override
  Widget build(BuildContext context) {
    if (_unlocked != true) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (!widget.settings.onboarded) {
      return const ProfileQuizScreen();
    }
    return const ShellScreen();
  }
}
