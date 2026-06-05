import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/spending_category.dart';
import '../theme/app_theme.dart';

class SpendingDonutChart extends StatelessWidget {
  const SpendingDonutChart({super.key, required this.categories});

  final List<SpendingCategoryItem> categories;

  static final _colors = AppTheme.chartPalette;

  @override
  Widget build(BuildContext context) {
    if (categories.isEmpty) {
      return const SizedBox(height: 160, child: Center(child: Text('No expense data')));
    }
    return SizedBox(
      height: 200,
      child: Row(
        children: [
          Expanded(
            child: PieChart(
              PieChartData(
                sectionsSpace: 2,
                centerSpaceRadius: 40,
                sections: [
                  for (var i = 0; i < categories.length; i++)
                    PieChartSectionData(
                      value: categories[i].amountRm,
                      color: _colors[i % _colors.length],
                      radius: 36,
                      title: '${categories[i].pct.toStringAsFixed(0)}%',
                      titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.white),
                    ),
                ],
              ),
            ),
          ),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (var i = 0; i < categories.length && i < 5; i++)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Row(
                      children: [
                        Container(width: 8, height: 8, color: _colors[i % _colors.length]),
                        const SizedBox(width: 6),
                        Expanded(child: Text(categories[i].category, style: const TextStyle(fontSize: 11))),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
