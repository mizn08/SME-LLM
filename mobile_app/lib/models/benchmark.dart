class BenchmarkMetric {
  BenchmarkMetric({
    required this.label,
    required this.smeValue,
    required this.industryMedian,
    this.industryP25,
    this.industryP75,
    this.percentile,
    this.unit = '',
  });

  final String label;
  final double smeValue;
  final double industryMedian;
  final double? industryP25;
  final double? industryP75;
  final int? percentile;
  final String unit;

  factory BenchmarkMetric.fromJson(Map<String, dynamic> j) => BenchmarkMetric(
        label: j['label'] as String,
        smeValue: (j['sme_value'] as num).toDouble(),
        industryMedian: (j['industry_median'] as num).toDouble(),
        industryP25: (j['industry_p25'] as num?)?.toDouble(),
        industryP75: (j['industry_p75'] as num?)?.toDouble(),
        percentile: j['percentile'] as int?,
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
