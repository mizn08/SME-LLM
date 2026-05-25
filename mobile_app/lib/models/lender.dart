class LenderItem {
  LenderItem({
    required this.id,
    required this.name,
    required this.productType,
    this.maxAmountRm,
    required this.typicalRateLabel,
    this.minRevenueRm,
    this.bumiputeraPreferred = false,
    this.islamicCompliant = false,
    required this.applyUrl,
    this.notes = '',
  });

  final String id;
  final String name;
  final String productType;
  final double? maxAmountRm;
  final String typicalRateLabel;
  final double? minRevenueRm;
  final bool bumiputeraPreferred;
  final bool islamicCompliant;
  final String applyUrl;
  final String notes;

  factory LenderItem.fromJson(Map<String, dynamic> j) => LenderItem(
        id: j['id'] as String,
        name: j['name'] as String,
        productType: j['product_type'] as String,
        maxAmountRm: (j['max_amount_rm'] as num?)?.toDouble(),
        typicalRateLabel: j['typical_rate_label'] as String,
        minRevenueRm: (j['min_revenue_rm'] as num?)?.toDouble(),
        bumiputeraPreferred: j['bumiputera_preferred'] as bool? ?? false,
        islamicCompliant: j['islamic_compliant'] as bool? ?? false,
        applyUrl: j['apply_url'] as String,
        notes: j['notes'] as String? ?? '',
      );
}

class LenderDirectoryResponse {
  LenderDirectoryResponse({required this.lenders, required this.total});

  final List<LenderItem> lenders;
  final int total;

  factory LenderDirectoryResponse.fromJson(Map<String, dynamic> j) =>
      LenderDirectoryResponse(
        lenders: (j['lenders'] as List<dynamic>? ?? [])
            .map((e) => LenderItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        total: j['total'] as int,
      );
}
