import 'package:flutter/material.dart';

import '../models/nudge.dart';
import '../theme/app_theme.dart';

class NudgeBanner extends StatelessWidget {
  const NudgeBanner({super.key, required this.nudge, this.onTap, this.onDismiss});

  final NudgeItem nudge;
  final VoidCallback? onTap;
  final VoidCallback? onDismiss;

  Color get _color {
    switch (nudge.severity) {
      case 'critical':
        return Colors.red.shade700;
      case 'warning':
        return Colors.orange.shade800;
      default:
        return AppTheme.teal;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: _color.withOpacity(0.12),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Icon(Icons.notifications_active_rounded, color: _color),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(nudge.title, style: TextStyle(fontWeight: FontWeight.w700, color: _color)),
                    Text(nudge.body, style: const TextStyle(fontSize: 12)),
                  ],
                ),
              ),
              if (onDismiss != null)
                IconButton(icon: const Icon(Icons.close, size: 18), onPressed: onDismiss),
            ],
          ),
        ),
      ),
    );
  }
}
