import 'package:flutter/material.dart';

import '../models/nudge.dart';
import '../theme/app_theme.dart';

class NudgeBanner extends StatelessWidget {
  const NudgeBanner({super.key, required this.nudge, this.onTap, this.onDismiss});

  final NudgeItem nudge;
  final VoidCallback? onTap;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final bg = AppTheme.severityBackground(nudge.severity);
    final fg = AppTheme.severityForeground(nudge.severity);

    return Material(
      color: bg,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: fg.withOpacity(0.25)),
          ),
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.6),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(Icons.notifications_active_rounded, color: fg, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(nudge.title, style: TextStyle(fontWeight: FontWeight.w700, color: fg, fontSize: 14)),
                    const SizedBox(height: 4),
                    Text(nudge.body, style: const TextStyle(fontSize: 12, height: 1.4, color: AppTheme.textPrimary)),
                  ],
                ),
              ),
              if (onDismiss != null)
                IconButton(
                  icon: Icon(Icons.close_rounded, size: 20, color: fg.withOpacity(0.7)),
                  onPressed: onDismiss,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
