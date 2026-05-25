import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/bnpl_repayment.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/repayment_calendar.dart';

class BnplRepaymentScreen extends StatefulWidget {
  const BnplRepaymentScreen({super.key});

  @override
  State<BnplRepaymentScreen> createState() => _BnplRepaymentScreenState();
}

class _BnplRepaymentScreenState extends State<BnplRepaymentScreen> {
  double _amount = 10000;
  double _rate = 12;
  double _tenure = 12;
  BnplRepaymentResponse? _result;
  bool _loading = false;

  Future<void> _calc() async {
    setState(() => _loading = true);
    try {
      _result = await ApiService().simulateBnplRepayment(
        amountRm: _amount,
        annualRatePct: _rate,
        tenureMonths: _tenure.toInt(),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void initState() {
    super.initState();
    _calc();
  }

  @override
  Widget build(BuildContext context) {
    final fmt = NumberFormat.currency(symbol: 'RM ', decimalDigits: 0);
    return Scaffold(
      appBar: AppBar(title: const Text('BNPL Repayment'), backgroundColor: AppTheme.teal),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Amount: ${fmt.format(_amount)}'),
          Slider(value: _amount, min: 1000, max: 100000, divisions: 99, onChanged: (v) => setState(() => _amount = v), onChangeEnd: (_) => _calc()),
          Text('Rate: ${_rate.toStringAsFixed(1)}% p.a.'),
          Slider(value: _rate, min: 0, max: 24, divisions: 24, onChanged: (v) => setState(() => _rate = v), onChangeEnd: (_) => _calc()),
          Text('Tenure: ${_tenure.toInt()} months'),
          Slider(value: _tenure, min: 3, max: 24, divisions: 21, onChanged: (v) => setState(() => _tenure = v), onChangeEnd: (_) => _calc()),
          if (_loading) const Center(child: CircularProgressIndicator()),
          if (_result != null) ...[
            Text('Monthly: ${fmt.format(_result!.monthlyPaymentRm)}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
            RepaymentCalendar(schedule: _result!.schedule),
          ],
        ],
      ),
    );
  }
}
