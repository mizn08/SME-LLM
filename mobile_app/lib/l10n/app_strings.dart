import 'package:flutter/material.dart';

/// Lightweight EN / MS strings — aligned with AI Marathon "Autonomous Sales Engineer".
class AppStrings {
  AppStrings(this.locale);

  final Locale locale;
  bool get isMs => locale.languageCode == 'ms';

  String t(String en, String ms) => isMs ? ms : en;

  String get appTitle => t('SME LLM BNPL Advisor', 'Penasihat BNPL LLM PKS');
  String get appSubtitle => t(
        'Autonomous Sales Engineer + BNPL intelligence',
        'Jurutera Jualan Autonomi + kecerdasan BNPL',
      );
  String get appTagline => t(
        'Brief → design → quote → BNPL / grant / credit advice',
        'Ringkasan → reka → sebut harga → nasihat BNPL / geran / kredit',
      );

  // Bottom nav — user journey order
  String get home => t('Home', 'Utama');
  String get plan => t('Design & Finance', 'Reka & Biaya');
  String get askAi => t('BNPL Advisor', 'Penasihat BNPL');
  String get funding => t('Funding', 'Pembiayaan');
  String get history => t('History', 'Sejarah');

  // Legacy aliases
  String get health => home;
  String get simulate => plan;
  String get aiAdvisor => askAi;
  String get grants => funding;
  String get performance => history;

  String get compare => t('Compare', 'Banding');
  String get settings => t('Settings', 'Tetapan');
  String get onboardingTitle => t('Welcome to SME LLM BNPL Advisor', 'Selamat datang ke Penasihat BNPL LLM PKS');
  String get onboardingBody => t(
        'Upload transactions, design solutions from a brief, finance purchases with BNPL, '
        'and get LLM guidance — all synced to your SME profile.',
        'Muat naik transaksi, reka penyelesaian daripada ringkasan, biayai pembelian dengan BNPL, '
        'dan dapatkan nasihat LLM — disegerakkan dengan profil PKS anda.',
      );
  String get includeSst => t('Include SST (6%) estimate', 'Termasuk anggaran SST (6%)');
  String get islamicOnly => t('Islamic financing only', 'Pembiayaan Islam sahaja');
  String get shareReport => t('Share report', 'Kongsi laporan');
  String get exportPdf => t('Export PDF', 'Eksport PDF');

  String get drawerUnderstand => t('1 · Understand', '1 · Fahami');
  String get drawerPlan => t('2 · Design & finance', '2 · Reka & biaya');
  String get drawerGuidance => t('3 · BNPL guidance', '3 · Nasihat BNPL');
  String get drawerApply => t('4 · Apply & track', '4 · Mohon');

  // AI Advisor sub-tabs
  String get tabRagChat => t('BNPL Chat', 'Sembang BNPL');
  String get tabAgents => t('Agents', 'Ejen');
  String get tabMlInsight => t('ML Insight', 'Wawasan ML');
  String get tabGuided => t('Guided', 'Berpandu');
  String get tabSalesEngineer => t('Sales Engineer', 'Jurutera Jualan');

  String get salesEngineerFlow => t('Design → Validate → Quote → Finance', 'Reka → Sahkan → Sebut Harga → Biaya');
}
