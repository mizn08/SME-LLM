class LeadScoreItem {
  LeadScoreItem({
    required this.productType,
    required this.productName,
    required this.score,
    required this.reasons,
  });

  final String productType;
  final String productName;
  final int score;
  final List<String> reasons;

  factory LeadScoreItem.fromJson(Map<String, dynamic> j) => LeadScoreItem(
        productType: j['product_type'] as String,
        productName: j['product_name'] as String,
        score: (j['score'] as num).toInt(),
        reasons: (j['reasons'] as List<dynamic>? ?? []).map((e) => e.toString()).toList(),
      );
}

class LeadScoreResponse {
  LeadScoreResponse({required this.smeId, required this.scores});

  final int smeId;
  final List<LeadScoreItem> scores;

  factory LeadScoreResponse.fromJson(Map<String, dynamic> j) => LeadScoreResponse(
        smeId: j['sme_id'] as int,
        scores: (j['scores'] as List<dynamic>? ?? [])
            .map((e) => LeadScoreItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
