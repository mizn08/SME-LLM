import 'package:flutter/material.dart';

/// Brand logo — chat bubble + growth arrow + neural network.
class AppLogo extends StatelessWidget {
  const AppLogo({
    super.key,
    this.size = 36,
    this.borderRadius = 10,
  });

  final double size;
  final double borderRadius;

  static const assetPath = 'assets/images/app_logo.png';

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: Image.asset(
        assetPath,
        width: size,
        height: size,
        fit: BoxFit.contain,
        errorBuilder: (_, __, ___) => Icon(Icons.psychology_alt_rounded, size: size * 0.7),
      ),
    );
  }
}
