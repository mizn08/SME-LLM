import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../l10n/app_strings.dart';
import '../providers/settings_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/app_logo.dart';
import 'shell_screen.dart';

class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final s = AppStrings(Localizations.localeOf(context));
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),
              const AppLogo(size: 120, borderRadius: 24),
              const SizedBox(height: 24),
              Text(s.onboardingTitle, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              Text(s.onboardingBody, style: TextStyle(color: Colors.grey.shade600, height: 1.5)),
              const Spacer(),
              FilledButton(
                onPressed: () async {
                  await context.read<SettingsProvider>().setOnboarded();
                  if (!context.mounted) return;
                  Navigator.of(context).pushReplacement(
                    MaterialPageRoute<void>(builder: (_) => const ShellScreen()),
                  );
                },
                style: FilledButton.styleFrom(backgroundColor: AppTheme.teal, padding: const EdgeInsets.symmetric(vertical: 14)),
                child: Text(s.t('Get started', 'Mula')),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
