import 'package:flutter_test/flutter_test.dart';
import 'package:bnpl_advisor_mobile/models/dashboard.dart';

/// App shell requires API/session; model tests cover client parsing consistency.
void main() {
  test('health fields are optional until dashboard loads', () {
    final json = {
      'sme_id': 1,
      'business_name': 'Test',
      'industry': 'Retail',
      'kpis': {
        'current_ratio': 1.0,
        'days_cash_on_hand': 30.0,
        'burn_rate_monthly_rm': 1000.0,
        'revenue_mtd_rm': 500.0,
        'expense_mtd_rm': 400.0,
        'net_operating_cash_rm': 100.0,
      },
      'monthly_series': [],
    };
    final d = DashboardData.fromJson(json);
    expect(d.healthScore, isNull);
    expect(d.netOperatingCashRm, 100.0);
  });
}
