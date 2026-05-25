import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/bnpl_repayment.dart';

class RepaymentCalendar extends StatelessWidget {
  const RepaymentCalendar({super.key, required this.schedule});

  final List<RepaymentMonth> schedule;

  @override
  Widget build(BuildContext context) {
    final fmt = NumberFormat.currency(symbol: 'RM ', decimalDigits: 0);
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        headingRowHeight: 36,
        dataRowMinHeight: 32,
        columns: const [
          DataColumn(label: Text('Mth')),
          DataColumn(label: Text('Payment')),
          DataColumn(label: Text('Principal')),
          DataColumn(label: Text('Interest')),
          DataColumn(label: Text('Balance')),
        ],
        rows: schedule
            .map(
              (m) => DataRow(
                cells: [
                  DataCell(Text('${m.month}')),
                  DataCell(Text(fmt.format(m.paymentRm))),
                  DataCell(Text(fmt.format(m.principalRm))),
                  DataCell(Text(fmt.format(m.interestRm))),
                  DataCell(Text(fmt.format(m.balanceRm))),
                ],
              ),
            )
            .toList(),
      ),
    );
  }
}
