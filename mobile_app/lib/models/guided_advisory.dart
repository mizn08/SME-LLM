class GuidedAdvisoryResponse {
  GuidedAdvisoryResponse({
    required this.smeId,
    required this.recommendation,
    required this.topProduct,
    required this.topProductType,
    required this.reasoning,
    required this.nextSteps,
    required this.pitchSnippet,
  });

  final int smeId;
  final String recommendation;
  final String topProduct;
  final String topProductType;
  final List<String> reasoning;
  final List<String> nextSteps;
  final String pitchSnippet;

  factory GuidedAdvisoryResponse.fromJson(Map<String, dynamic> j) => GuidedAdvisoryResponse(
        smeId: j['sme_id'] as int,
        recommendation: j['recommendation'] as String,
        topProduct: j['top_product'] as String,
        topProductType: j['top_product_type'] as String,
        reasoning: (j['reasoning'] as List<dynamic>? ?? []).map((e) => e.toString()).toList(),
        nextSteps: (j['next_steps'] as List<dynamic>? ?? []).map((e) => e.toString()).toList(),
        pitchSnippet: j['pitch_snippet'] as String,
      );
}
