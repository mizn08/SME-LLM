class RepaymentMonth {
  RepaymentMonth({
    required this.month,
    required this.paymentRm,
    required this.principalRm,
    required this.interestRm,
    required this.balanceRm,
  });

  final int month;
  final double paymentRm;
  final double principalRm;
  final double interestRm;
  final double balanceRm;

  factory RepaymentMonth.fromJson(Map<String, dynamic> j) => RepaymentMonth(
        month: j['month'] as int,
        paymentRm: (j['payment_rm'] as num).toDouble(),
        principalRm: (j['principal_rm'] as num).toDouble(),
        interestRm: (j['interest_rm'] as num).toDouble(),
        balanceRm: (j['balance_rm'] as num).toDouble(),
      );
}

class BnplRepaymentResponse {
  BnplRepaymentResponse({
    required this.amountRm,
    required this.annualRatePct,
    required this.tenureMonths,
    required this.monthlyPaymentRm,
    required this.totalInterestRm,
    required this.totalCostRm,
    required this.schedule,
  });

  final double amountRm;
  final double annualRatePct;
  final int tenureMonths;
  final double monthlyPaymentRm;
  final double totalInterestRm;
  final double totalCostRm;
  final List<RepaymentMonth> schedule;

  factory BnplRepaymentResponse.fromJson(Map<String, dynamic> j) => BnplRepaymentResponse(
        amountRm: (j['amount_rm'] as num).toDouble(),
        annualRatePct: (j['annual_rate_pct'] as num).toDouble(),
        tenureMonths: j['tenure_months'] as int,
        monthlyPaymentRm: (j['monthly_payment_rm'] as num).toDouble(),
        totalInterestRm: (j['total_interest_rm'] as num).toDouble(),
        totalCostRm: (j['total_cost_rm'] as num).toDouble(),
        schedule: (j['schedule'] as List<dynamic>? ?? [])
            .map((e) => RepaymentMonth.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
