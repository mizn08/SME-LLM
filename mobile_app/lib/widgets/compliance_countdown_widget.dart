import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import 'kpi_card.dart';

class _Deadline {
  const _Deadline(this.title, this.date, this.urgency);
  final String title;
  final DateTime date;
  final String urgency; // overdue | urgent | upcoming
}

class ComplianceCountdownWidget extends StatelessWidget {
  const ComplianceCountdownWidget({super.key});

  static final _deadlines = [
    _Deadline('e-Invoice Phase 4 (RM1M–RM5M)', DateTime(2026, 1, 1), 'overdue'),
    _Deadline('Minimum wage RM1,700 enforcement', DateTime(2025, 2, 1), 'overdue'),
    _Deadline('e-Invoice Phase 5 (<RM1M)', DateTime(2026, 7, 1), 'upcoming'),
    _Deadline('SJPP guarantee applications close', DateTime(2026, 12, 31), 'upcoming'),
  ];

  Color _color(String u) {
    switch (u) {
      case 'overdue':
        return AppTheme.criticalFg;
      case 'urgent':
        return AppTheme.warningFg;
      default:
        return AppTheme.successFg;
    }
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    return PremiumCard(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.calendar_month_rounded, color: AppTheme.skyDeep, size: 22),
              const SizedBox(width: 8),
              Text(
                'Compliance countdown',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'Malaysia SME obligations — plan ahead',
            style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
          ),
          const SizedBox(height: 12),
          ..._deadlines.map((d) {
            final days = d.date.difference(now).inDays;
            final label = days < 0 ? '${-days} days ago' : days == 0 ? 'Due today' : '$days days left';
            return Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                children: [
                  Container(
                    width: 4,
                    height: 40,
                    decoration: BoxDecoration(
                      color: _color(d.urgency),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(d.title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                        Text(label, style: TextStyle(fontSize: 12, color: _color(d.urgency))),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
