class SpendingCategoryItem {
  SpendingCategoryItem({
    required this.category,
    required this.amountRm,
    required this.pct,
  });

  final String category;
  final double amountRm;
  final double pct;

  factory SpendingCategoryItem.fromJson(Map<String, dynamic> j) => SpendingCategoryItem(
        category: j['category'] as String,
        amountRm: (j['amount_rm'] as num).toDouble(),
        pct: (j['pct'] as num).toDouble(),
      );
}

class SpendingCategoryResponse {
  SpendingCategoryResponse({
    required this.smeId,
    required this.categories,
    required this.totalExpenseRm,
  });

  final int smeId;
  final List<SpendingCategoryItem> categories;
  final double totalExpenseRm;

  factory SpendingCategoryResponse.fromJson(Map<String, dynamic> j) => SpendingCategoryResponse(
        smeId: j['sme_id'] as int,
        categories: (j['categories'] as List<dynamic>? ?? [])
            .map((e) => SpendingCategoryItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        totalExpenseRm: (j['total_expense_rm'] as num).toDouble(),
      );
}
