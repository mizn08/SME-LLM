import 'package:flutter_test/flutter_test.dart';
import 'package:bnpl_advisor_mobile/models/dashboard.dart';

void main() {
  test('DashboardData parses API KPIs and health from server', () {
    final json = {
      'sme_id': 1,
      'business_name': 'Kopi Maju Enterprise',
      'industry': 'F&B',
      'kpis': {
        'current_ratio': 0.42,
        'days_cash_on_hand': 0.0,
        'burn_rate_monthly_rm': 83854.33,
        'revenue_mtd_rm': 12000.0,
        'expense_mtd_rm': 45000.0,
        'net_operating_cash_rm': -249536.48,
      },
      'monthly_series': [],
      'runway_days_est': 0.0,
      'alerts': [],
      'anomaly_count': 2,
      'health_score': 0,
      'health_grade': 'F',
      'health_label': 'WATCH',
      'forecast_months': [],
    };

    final d = DashboardData.fromJson(json);
    expect(d.netOperatingCashRm, -249536.48);
    expect(d.healthScore, 0);
    expect(d.healthGrade, 'F');
    expect(d.healthLabel, 'WATCH');
    expect(d.runwayDaysEst, 0.0);
  });
}
