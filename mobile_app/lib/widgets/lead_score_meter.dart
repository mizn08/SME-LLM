import 'package:flutter/material.dart';

import '../models/lead_score.dart';
import '../theme/app_theme.dart';

class LeadScoreMeter extends StatelessWidget {
  const LeadScoreMeter({super.key, required this.item});

  final LeadScoreItem item;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text(item.productName, style: const TextStyle(fontWeight: FontWeight.w600))),
            Text('${item.score}%', style: const TextStyle(fontWeight: FontWeight.w700, color: AppTheme.teal)),
          ],
        ),
        const SizedBox(height: 6),
        TweenAnimationBuilder<double>(
          tween: Tween(begin: 0, end: item.score / 100),
          duration: const Duration(milliseconds: 800),
          builder: (_, v, __) => LinearProgressIndicator(
            value: v,
            minHeight: 8,
            borderRadius: BorderRadius.circular(4),
            backgroundColor: Colors.grey.shade200,
            color: AppTheme.teal,
          ),
        ),
        if (item.reasons.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(item.reasons.first, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
        ],
      ],
    );
  }
}
