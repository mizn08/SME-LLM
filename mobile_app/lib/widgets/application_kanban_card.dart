import 'package:flutter/material.dart';

import '../models/application_tracker.dart';
import '../theme/app_theme.dart';

class ApplicationKanbanCard extends StatelessWidget {
  const ApplicationKanbanCard({super.key, required this.item, this.onTap});

  final ApplicationTrackerItem item;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(item.productName, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              Text(item.productType, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
              if (item.notes != null && item.notes!.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(item.notes!, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 10)),
                ),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(color: AppTheme.teal.withOpacity(0.1), borderRadius: BorderRadius.circular(6)),
                child: Text(item.status, style: const TextStyle(fontSize: 10, color: AppTheme.teal)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
