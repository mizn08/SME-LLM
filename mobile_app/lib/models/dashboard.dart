class ForecastMonth {
  ForecastMonth({
    required this.monthOffset,
    required this.projectedNetRm,
    required this.cumulativeNetRm,
  });

  final int monthOffset;
  final double projectedNetRm;
  final double cumulativeNetRm;

  factory ForecastMonth.fromJson(Map<String, dynamic> j) => ForecastMonth(
        monthOffset: j['month_offset'] as int,
        projectedNetRm: (j['projected_net_rm'] as num).toDouble(),
        cumulativeNetRm: (j['cumulative_net_rm'] as num).toDouble(),
      );
}

class MonthlyPoint {
  MonthlyPoint({required this.month, required this.revenueRm, required this.expenseRm});
  final String month;
  final double revenueRm;
  final double expenseRm;

  factory MonthlyPoint.fromJson(Map<String, dynamic> j) => MonthlyPoint(
        month: j['month'] as String,
        revenueRm: (j['revenue_rm'] as num).toDouble(),
        expenseRm: (j['expense_rm'] as num).toDouble(),
      );
}

class DashboardData {
  DashboardData({
    required this.smeId,
    required this.businessName,
    required this.industry,
    required this.currentRatio,
    required this.daysCashOnHand,
    required this.burnRateMonthlyRm,
    required this.revenueMtdRm,
    required this.expenseMtdRm,
    required this.netOperatingCashRm,
    required this.monthlySeries,
    this.runwayDaysEst,
    this.alerts = const [],
    this.anomalyCount = 0,
    this.healthScore,
    this.healthGrade,
    this.healthLabel,
    this.forecastMonths = const [],
  });

  final int smeId;
  final String businessName;
  final String industry;
  final double currentRatio;
  final double daysCashOnHand;
  final double burnRateMonthlyRm;
  final double revenueMtdRm;
  final double expenseMtdRm;
  final double netOperatingCashRm;
  final List<MonthlyPoint> monthlySeries;
  final double? runwayDaysEst;
  final List<String> alerts;
  final int anomalyCount;
  final int? healthScore;
  final String? healthGrade;
  final String? healthLabel;
  final List<ForecastMonth> forecastMonths;

  factory DashboardData.fromJson(Map<String, dynamic> j) {
    final kpis = j['kpis'] as Map<String, dynamic>;
    final series = (j['monthly_series'] as List<dynamic>? ?? [])
        .map((e) => MonthlyPoint.fromJson(e as Map<String, dynamic>))
        .toList();
    return DashboardData(
      smeId: j['sme_id'] as int,
      businessName: j['business_name'] as String,
      industry: j['industry'] as String,
      currentRatio: (kpis['current_ratio'] as num).toDouble(),
      daysCashOnHand: (kpis['days_cash_on_hand'] as num).toDouble(),
      burnRateMonthlyRm: (kpis['burn_rate_monthly_rm'] as num).toDouble(),
      revenueMtdRm: (kpis['revenue_mtd_rm'] as num).toDouble(),
      expenseMtdRm: (kpis['expense_mtd_rm'] as num).toDouble(),
      netOperatingCashRm: (kpis['net_operating_cash_rm'] as num).toDouble(),
      monthlySeries: series,
      runwayDaysEst: (j['runway_days_est'] as num?)?.toDouble(),
      alerts: (j['alerts'] as List<dynamic>? ?? []).map((e) => e.toString()).toList(),
      anomalyCount: j['anomaly_count'] as int? ?? 0,
      healthScore: j['health_score'] as int?,
      healthGrade: j['health_grade'] as String?,
      healthLabel: j['health_label'] as String?,
      forecastMonths: (j['forecast_months'] as List<dynamic>? ?? [])
          .map((e) => ForecastMonth.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
