class BenchmarkMetric {
  BenchmarkMetric({
    required this.label,
    required this.smeValue,
    required this.industryMedian,
    this.unit = '',
  });

  final String label;
  final double smeValue;
  final double industryMedian;
  final String unit;

  factory BenchmarkMetric.fromJson(Map<String, dynamic> j) => BenchmarkMetric(
        label: j['label'] as String,
        smeValue: (j['sme_value'] as num).toDouble(),
        industryMedian: (j['industry_median'] as num).toDouble(),
        unit: j['unit'] as String? ?? '',
      );
}

class BenchmarkResponse {
  BenchmarkResponse({
    required this.smeId,
    required this.industry,
    required this.metrics,
    required this.summary,
  });

  final int smeId;
  final String industry;
  final List<BenchmarkMetric> metrics;
  final String summary;

  factory BenchmarkResponse.fromJson(Map<String, dynamic> j) => BenchmarkResponse(
        smeId: j['sme_id'] as int,
        industry: j['industry'] as String,
        metrics: (j['metrics'] as List<dynamic>? ?? [])
            .map((e) => BenchmarkMetric.fromJson(e as Map<String, dynamic>))
            .toList(),
        summary: j['summary'] as String,
      );
}
