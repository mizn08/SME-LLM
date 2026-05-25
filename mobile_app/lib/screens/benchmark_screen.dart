import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/benchmark.dart';
import '../providers/session_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class BenchmarkScreen extends StatefulWidget {
  const BenchmarkScreen({super.key});

  @override
  State<BenchmarkScreen> createState() => _BenchmarkScreenState();
}

class _BenchmarkScreenState extends State<BenchmarkScreen> {
  BenchmarkResponse? data;
  bool loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final sid = context.read<SessionProvider>().smeId;
    try {
      data = await ApiService().fetchBenchmark(sid);
    } catch (_) {}
    if (mounted) setState(() => loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Industry Benchmark'), backgroundColor: AppTheme.teal),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(data?.summary ?? '', style: TextStyle(color: Colors.grey.shade700)),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 220,
                    child: BarChart(
                      BarChartData(
                        alignment: BarChartAlignment.spaceAround,
                        maxY: ((data?.metrics.isNotEmpty ?? false)
                                ? data!.metrics
                                    .map((m) => m.smeValue > m.industryMedian ? m.smeValue : m.industryMedian)
                                    .reduce((a, b) => a > b ? a : b)
                                : 1) *
                            1.2,
                        barGroups: [
                          for (var i = 0; i < (data?.metrics.length ?? 0); i++)
                            BarChartGroupData(
                              x: i,
                              barRods: [
                                BarChartRodData(toY: data!.metrics[i].smeValue, color: AppTheme.teal, width: 12),
                                BarChartRodData(toY: data!.metrics[i].industryMedian, color: Colors.grey, width: 12),
                              ],
                            ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
