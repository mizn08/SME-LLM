import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/dashboard.dart';
import '../theme/app_theme.dart';

class MonthlyCashChart extends StatelessWidget {
  const MonthlyCashChart({super.key, required this.points, this.forecastNet});

  final List<MonthlyPoint> points;
  final List<double>? forecastNet;

  @override
  Widget build(BuildContext context) {
    if (points.isEmpty) {
      return SizedBox(
        height: 220,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.bar_chart_rounded, size: 40, color: Colors.grey.shade300),
              const SizedBox(height: 8),
              Text(
                'Upload transactions to see monthly trends.',
                style: TextStyle(color: Colors.grey.shade500),
              ),
            ],
          ),
        ),
      );
    }
    final last = points.length > 12 ? points.sublist(points.length - 12) : points;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Legend
        Row(
          children: [
            _legendDot(AppTheme.sage, 'Revenue'),
            const SizedBox(width: 16),
            _legendDot(AppTheme.peachDeep, 'Expenses'),
            if (forecastNet != null && forecastNet!.isNotEmpty) ...[
              const SizedBox(width: 16),
              _legendDot(AppTheme.lavenderDeep, 'Forecast net'),
            ],
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 220,
          child: Padding(
            padding: const EdgeInsets.only(right: 8, top: 8),
            child: LineChart(
              LineChartData(
                minX: 0,
                maxX: last.length > 1 ? (last.length - 1).toDouble() : 1,
                lineTouchData: LineTouchData(
                  touchTooltipData: LineTouchTooltipData(
                    getTooltipColor: (_) => AppTheme.sageDark,
                    tooltipRoundedRadius: 12,
                    tooltipPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    getTooltipItems: (spots) => spots.map((s) {
                      final color = s.barIndex == 0 ? AppTheme.sageLight : AppTheme.peach;
                      final label = s.barIndex == 0 ? 'Rev' : 'Exp';
                      return LineTooltipItem(
                        '$label: RM ${(s.y * 1000).toStringAsFixed(0)}',
                        TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 12),
                      );
                    }).toList(),
                  ),
                ),
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: null,
                  getDrawingHorizontalLine: (value) => FlLine(
                    color: Colors.grey.shade200,
                    strokeWidth: 1,
                    dashArray: [4, 4],
                  ),
                ),
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 28,
                      getTitlesWidget: (v, m) {
                        final i = v.toInt();
                        if (i < 0 || i >= last.length) return const SizedBox.shrink();
                        final short = last[i].month.split(' ').first;
                        return Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            short,
                            style: TextStyle(fontSize: 9, color: Colors.grey.shade500, fontWeight: FontWeight.w500),
                          ),
                        );
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 40,
                      getTitlesWidget: (v, _) => Text(
                        '${v.toInt()}k',
                        style: TextStyle(fontSize: 10, color: Colors.grey.shade500),
                      ),
                    ),
                  ),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  LineChartBarData(
                    spots: [
                      for (var i = 0; i < last.length; i++)
                        FlSpot(i.toDouble(), last[i].revenueRm / 1000),
                    ],
                    gradient: const LinearGradient(colors: [AppTheme.sage, AppTheme.sageLight]),
                    barWidth: 3,
                    dotData: FlDotData(
                      show: true,
                      getDotPainter: (_, __, ___, ____) => FlDotCirclePainter(
                        radius: 4,
                        color: AppTheme.sage,
                        strokeWidth: 2,
                        strokeColor: Colors.white,
                      ),
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [AppTheme.sage.withOpacity(0.2), AppTheme.sage.withOpacity(0.0)],
                      ),
                    ),
                  ),
                  LineChartBarData(
                    spots: [
                      for (var i = 0; i < last.length; i++)
                        FlSpot(i.toDouble(), last[i].expenseRm / 1000),
                    ],
                    color: AppTheme.peachDeep,
                    barWidth: 3,
                    dotData: FlDotData(
                      show: true,
                      getDotPainter: (_, __, ___, ____) => FlDotCirclePainter(
                        radius: 3,
                        color: AppTheme.peachDeep,
                        strokeWidth: 2,
                        strokeColor: Colors.white,
                      ),
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [AppTheme.peach.withOpacity(0.35), AppTheme.peach.withOpacity(0.0)],
                      ),
                    ),
                  ),
                  if (forecastNet != null && forecastNet!.isNotEmpty)
                    LineChartBarData(
                      spots: [
                        for (var i = 0; i < forecastNet!.length; i++)
                          FlSpot((last.length + i).toDouble(), forecastNet![i] / 1000),
                      ],
                      color: AppTheme.lavenderDeep,
                      barWidth: 2,
                      dashArray: [6, 4],
                      dotData: const FlDotData(show: false),
                    ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _legendDot(Color color, String label) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(3)),
          ),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontWeight: FontWeight.w500)),
        ],
      );
}
