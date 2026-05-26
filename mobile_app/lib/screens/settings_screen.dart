import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';
import 'package:provider/provider.dart';

import '../l10n/app_strings.dart';
import '../providers/settings_provider.dart';
import '../theme/app_theme.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    final s = AppStrings(settings.locale);
    return Scaffold(
      appBar: AppBar(title: Text(s.settings), backgroundColor: AppTheme.teal, foregroundColor: Colors.white),
      body: ListView(
        children: [
          SwitchListTile(
            title: Text(s.t('Dark mode', 'Mod gelap')),
            value: settings.themeMode == ThemeMode.dark,
            onChanged: (v) => settings.setDark(v),
          ),
          ListTile(
            title: Text(s.t('Language', 'Bahasa')),
            subtitle: Text(settings.locale.languageCode == 'ms' ? 'Bahasa Melayu' : 'English'),
            trailing: DropdownButton<String>(
              value: settings.locale.languageCode,
              items: const [
                DropdownMenuItem(value: 'en', child: Text('English')),
                DropdownMenuItem(value: 'ms', child: Text('Melayu')),
              ],
              onChanged: (v) {
                if (v != null) settings.setLocale(v);
              },
            ),
          ),
          ListTile(
            title: Text(s.t('Text size', 'Saiz teks')),
            subtitle: Slider(
              value: settings.textScale,
              min: 0.9,
              max: 1.3,
              divisions: 4,
              label: settings.textScale.toStringAsFixed(1),
              onChanged: settings.setTextScale,
            ),
          ),
          SwitchListTile(
            title: Text(s.t('Biometric lock', 'Kunci biometrik')),
            value: settings.biometricEnabled,
            onChanged: kIsWeb
                ? null
                : (v) async {
              if (v) {
                final auth = LocalAuthentication();
                final ok = await auth.authenticate(
                  localizedReason: 'Unlock SME Advisor',
                  options: const AuthenticationOptions(biometricOnly: true),
                );
                if (!ok) return;
              }
              await settings.setBiometric(v);
            },
          ),
        ],
      ),
    );
  }
}
