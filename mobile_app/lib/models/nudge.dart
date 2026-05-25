class NudgeItem {
  NudgeItem({
    required this.severity,
    required this.title,
    required this.body,
    this.recommendedProduct,
    this.actionLabel,
  });

  final String severity;
  final String title;
  final String body;
  final String? recommendedProduct;
  final String? actionLabel;

  factory NudgeItem.fromJson(Map<String, dynamic> j) => NudgeItem(
        severity: j['severity'] as String,
        title: j['title'] as String,
        body: j['body'] as String,
        recommendedProduct: j['recommended_product'] as String?,
        actionLabel: j['action_label'] as String?,
      );
}

class NudgeResponse {
  NudgeResponse({required this.smeId, required this.nudges});

  final int smeId;
  final List<NudgeItem> nudges;

  factory NudgeResponse.fromJson(Map<String, dynamic> j) => NudgeResponse(
        smeId: j['sme_id'] as int,
        nudges: (j['nudges'] as List<dynamic>? ?? [])
            .map((e) => NudgeItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
