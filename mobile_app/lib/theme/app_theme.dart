import 'package:flutter/material.dart';

/// SME Advisor — professional light theme built on #006BBB · #30A0E0 · #FFC872 · #FFE3B3.
class AppTheme {
  // ── Brand (your palette, unchanged) ──
  static const Color brandBlue = Color(0xFF006BBB);
  static const Color skyBlue = Color(0xFF30A0E0);
  static const Color premiumGold = Color(0xFFFFC872);
  static const Color cream = Color(0xFFFFE3B3);

  // ── Professional surfaces (neutral base + brand accents) ──
  static const Color voidBg = Color(0xFFF4F7FA);
  static const Color surfaceDeep = Color(0xFFEEF4F9);
  static const Color surfaceCard = Color(0xFFFFFFFF);
  static const Color surfaceElevated = Color(0xFFFAFCFE);
  static const Color accentWash = Color(0xFFE8F2FA);
  static const Color creamSubtle = Color(0xFFFFF8EE);
  static const Color borderColor = Color(0xFFE3EBF3);
  static const Color borderGlow = Color(0xFF30A0E0);

  static const Color brandBlueDark = Color(0xFF005A9E);
  static const Color goldAccent = Color(0xFFC9923A);
  static const Color goldDark = Color(0xFFB8842E);
  static const Color coral = Color(0xFFD45C5C);
  static const Color textPrimary = Color(0xFF1A3348);
  static const Color textSecondary = Color(0xFF5C7289);
  static const Color mutedForeground = Color(0xFF8A9DB0);

  // Legacy aliases
  static const Color midnight = brandBlue;
  static const Color midnightLight = skyBlue;
  static const Color ember = goldAccent;
  static const Color emberDark = goldDark;
  static const Color sage = brandBlue;
  static const Color sageDark = brandBlueDark;
  static const Color sageLight = skyBlue;
  static const Color mint = accentWash;
  static const Color lavender = skyBlue;
  static const Color lavenderDeep = brandBlue;
  static const Color peach = creamSubtle;
  static const Color peachDeep = goldAccent;
  static const Color blush = Color(0xFFFFF5F5);
  static const Color rose = coral;
  static const Color sky = accentWash;
  static const Color skyDeep = skyBlue;
  static const Color teal = brandBlue;
  static const Color tealDark = brandBlueDark;
  static const Color tealLight = skyBlue;
  static const Color tealAccent = goldAccent;
  static const Color iceBlue = accentWash;
  static const Color navy = brandBlue;
  static const Color accentGreen = skyBlue;
  static const Color surfaceLight = voidBg;
  static const Color gold = premiumGold;
  static const Color neonCyan = brandBlue;
  static const Color neonCyanDim = brandBlueDark;
  static const Color neonPurple = skyBlue;
  static const Color neonPurpleBright = brandBlue;
  static const Color royalBlue = skyBlue;

  static const Color criticalBg = Color(0xFFFFF5F5);
  static const Color criticalFg = coral;
  static const Color warningBg = Color(0xFFFFF8EE);
  static const Color warningFg = goldDark;
  static const Color successBg = Color(0xFFEEF6FC);
  static const Color successFg = brandBlue;
  static const Color infoBg = Color(0xFFEEF6FC);
  static const Color infoFg = brandBlueDark;

  static const LinearGradient primaryGradient = LinearGradient(
    colors: [Color(0xFF006BBB), Color(0xFF1A7FC4)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient headerGradient = LinearGradient(
    colors: [Color(0xFFFFFFFF), Color(0xFFF4F7FA)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  /// Top app bar — white with a soft brand wash and accent line.
  static BoxDecoration get brandAppBarDecoration => BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFFFFFFF), Color(0xFFF8FBFE), Color(0xFFEEF6FC)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border(
          bottom: BorderSide(color: brandBlue.withOpacity(0.18), width: 1.5),
        ),
        boxShadow: [
          BoxShadow(
            color: brandBlue.withOpacity(0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      );

  static const LinearGradient cardAccentGradient = LinearGradient(
    colors: [Color(0xFF006BBB), Color(0xFF30A0E0)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient backgroundGradient = LinearGradient(
    colors: [Color(0xFFF4F7FA), Color(0xFFFAFCFE)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  static const LinearGradient askAiGradient = LinearGradient(
    colors: [Color(0xFF005A9E), Color(0xFF006BBB)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient fundingGradient = LinearGradient(
    colors: [Color(0xFFC9923A), Color(0xFFB8842E)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const List<Color> chartPalette = [
    Color(0xFF006BBB),
    Color(0xFF30A0E0),
    Color(0xFFC9923A),
    Color(0xFF8A9DB0),
    Color(0xFFD45C5C),
    Color(0xFF005A9E),
    Color(0xFF5C7289),
    Color(0xFFFFC872),
  ];

  static List<BoxShadow> cardShadow = [
    BoxShadow(
      color: const Color(0xFF1A3348).withOpacity(0.06),
      blurRadius: 12,
      offset: const Offset(0, 2),
    ),
  ];

  static List<BoxShadow> glowShadow(Color color) => [
    BoxShadow(color: color.withOpacity(0.14), blurRadius: 8, spreadRadius: 0),
  ];

  static BoxDecoration cardDecoration({
    Color? color,
    Gradient? gradient,
    Color? border,
    double radius = 12,
  }) {
    return BoxDecoration(
      gradient: gradient,
      color: gradient == null ? (color ?? surfaceCard) : null,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: border ?? borderColor, width: 1),
      boxShadow: cardShadow,
    );
  }

  static List<BoxShadow> elevatedShadow = [
    BoxShadow(
      color: const Color(0xFF1A3348).withOpacity(0.08),
      blurRadius: 16,
      offset: const Offset(0, 4),
    ),
  ];

  static Color severityBackground(String severity) {
    switch (severity) {
      case 'critical':
        return criticalBg;
      case 'warning':
        return warningBg;
      default:
        return infoBg;
    }
  }

  static Color severityForeground(String severity) {
    switch (severity) {
      case 'critical':
        return criticalFg;
      case 'warning':
        return warningFg;
      default:
        return infoFg;
    }
  }

  static ThemeData light() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      fontFamily: 'Roboto',
      scaffoldBackgroundColor: voidBg,
      colorScheme: ColorScheme.fromSeed(
        seedColor: brandBlue,
        brightness: Brightness.light,
        primary: brandBlue,
        secondary: goldAccent,
        tertiary: skyBlue,
        surface: surfaceCard,
        onSurface: textPrimary,
        onPrimary: Colors.white,
      ),
      textTheme: const TextTheme(
        headlineSmall: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.4,
          color: textPrimary,
        ),
        titleLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: textPrimary),
        titleMedium: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: textPrimary),
        titleSmall: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: textSecondary),
        bodyLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.w400, height: 1.5, color: textPrimary),
        bodyMedium: TextStyle(fontSize: 14, fontWeight: FontWeight.w400, height: 1.45, color: textPrimary),
        bodySmall: TextStyle(fontSize: 12, height: 1.4, color: mutedForeground),
        labelSmall: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.6,
          color: mutedForeground,
        ),
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: surfaceCard,
        foregroundColor: textPrimary,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: textPrimary),
        iconTheme: IconThemeData(color: textPrimary, size: 22),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surfaceCard,
        indicatorColor: accentWash,
        surfaceTintColor: Colors.transparent,
        elevation: 8,
        shadowColor: const Color(0xFF1A3348).withOpacity(0.08),
        height: 72,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: brandBlue);
          }
          return const TextStyle(fontSize: 10, fontWeight: FontWeight.w500, color: mutedForeground);
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const IconThemeData(color: brandBlue, size: 22);
          }
          return const IconThemeData(color: mutedForeground, size: 22);
        }),
      ),
      cardTheme: CardTheme(
        elevation: 0,
        color: surfaceCard,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: borderColor),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceCard,
        labelStyle: const TextStyle(color: textSecondary, fontSize: 13),
        hintStyle: const TextStyle(color: mutedForeground, fontSize: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: borderColor),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: borderColor),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: brandBlue, width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: brandBlue,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 22),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: 0.2),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: brandBlue,
          side: const BorderSide(color: borderColor),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surfaceElevated,
        selectedColor: accentWash,
        side: const BorderSide(color: borderColor),
        labelStyle: const TextStyle(color: textPrimary, fontSize: 13),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      dividerTheme: const DividerThemeData(color: borderColor, thickness: 1),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        backgroundColor: textPrimary,
      ),
    );
  }

  static ThemeData dark() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: brandBlueDark,
      colorScheme: ColorScheme.fromSeed(seedColor: skyBlue, brightness: Brightness.dark),
    );
  }
}

class PremiumCard extends StatelessWidget {
  const PremiumCard({
    super.key,
    required this.child,
    this.margin,
    this.padding,
    this.gradient,
    this.borderColor,
  });

  final Widget child;
  final EdgeInsetsGeometry? margin;
  final EdgeInsetsGeometry? padding;
  final Gradient? gradient;
  final Color? borderColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin ?? const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      decoration: AppTheme.cardDecoration(
        gradient: gradient,
        border: borderColor,
      ),
      child: Padding(
        padding: padding ?? const EdgeInsets.all(20),
        child: child,
      ),
    );
  }
}

class GradientAppBar extends StatelessWidget implements PreferredSizeWidget {
  const GradientAppBar({
    super.key,
    required this.title,
    this.leading,
    this.actions,
    this.subtitle,
  });

  final String title;
  final String? subtitle;
  final Widget? leading;
  final List<Widget>? actions;

  @override
  Size get preferredSize => Size.fromHeight(subtitle != null ? kToolbarHeight + 20 : kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppTheme.surfaceCard,
        border: Border(bottom: BorderSide(color: AppTheme.borderColor)),
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
          child: Row(
            children: [
              if (leading != null) leading!,
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      title,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    if (subtitle != null)
                      Text(
                        subtitle!,
                        style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                      ),
                  ],
                ),
              ),
              if (actions != null) ...actions! else const SizedBox(width: 48),
            ],
          ),
        ),
      ),
    );
  }
}

class FundingIcon extends StatelessWidget {
  const FundingIcon({super.key, this.size = 24, this.color, this.outlined = false});

  final double size;
  final Color? color;
  final bool outlined;

  @override
  Widget build(BuildContext context) {
    return Icon(
      outlined ? Icons.assured_workload_outlined : Icons.assured_workload_rounded,
      size: size,
      color: color ?? AppTheme.goldAccent,
    );
  }
}
