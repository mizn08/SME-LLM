import 'lead_score.dart';

class ShapItem {
  ShapItem({
    required this.feature,
    required this.value,
    required this.impact,
    required this.direction,
  });

  final String feature;
  final double value;
  final double impact;
  final String direction;

  factory ShapItem.fromJson(Map<String, dynamic> j) => ShapItem(
        feature: j['feature'] as String,
        value: (j['value'] as num).toDouble(),
        impact: (j['impact'] as num).toDouble(),
        direction: j['direction'] as String,
      );
}

class PredictionResult {
  PredictionResult({
    this.predictionId,
    required this.recommendationType,
    required this.productName,
    required this.explanation,
    required this.cashPreservedRm,
    required this.additionalCostRm,
    required this.confidence,
    required this.shapValues,
    required this.mlProbability,
    this.banditSuggestedArm,
    this.rlSuggestedAction,
    this.leadScores = const [],
  });

  final int? predictionId;
  final String recommendationType;
  final String productName;
  final String explanation;
  final double cashPreservedRm;
  final double additionalCostRm;
  final double confidence;
  final List<ShapItem> shapValues;
  final double mlProbability;
  final String? banditSuggestedArm;
  final String? rlSuggestedAction;
  final List<LeadScoreItem> leadScores;

  factory PredictionResult.fromJson(Map<String, dynamic> j) {
    final shap = (j['shap_values'] as List<dynamic>? ?? [])
        .map((e) => ShapItem.fromJson(e as Map<String, dynamic>))
        .toList();
    return PredictionResult(
      predictionId: j['prediction_id'] as int?,
      recommendationType: j['recommendation_type'] as String,
      productName: j['product_name'] as String,
      explanation: j['explanation'] as String,
      cashPreservedRm: (j['cash_preserved_rm'] as num).toDouble(),
      additionalCostRm: (j['additional_cost_rm'] as num).toDouble(),
      confidence: (j['confidence'] as num).toDouble(),
      shapValues: shap,
      mlProbability: (j['ml_probability'] as num).toDouble(),
      banditSuggestedArm: j['bandit_suggested_arm'] as String?,
      rlSuggestedAction: j['rl_suggested_action'] as String?,
      leadScores: (j['lead_scores'] as List<dynamic>? ?? [])
          .map((e) => LeadScoreItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class PredictionHistoryItem {
  PredictionHistoryItem({
    required this.id,
    required this.smeId,
    required this.createdAt,
    required this.recommendationType,
    required this.productName,
    required this.confidence,
    required this.purchaseAmount,
  });

  final int id;
  final int smeId;
  final DateTime createdAt;
  final String recommendationType;
  final String productName;
  final double confidence;
  final double purchaseAmount;

  factory PredictionHistoryItem.fromJson(Map<String, dynamic> j) => PredictionHistoryItem(
        id: j['id'] as int,
        smeId: j['sme_id'] as int,
        createdAt: DateTime.parse(j['created_at'] as String),
        recommendationType: j['recommendation_type'] as String,
        productName: j['product_name'] as String,
        confidence: (j['confidence'] as num).toDouble(),
        purchaseAmount: (j['purchase_amount'] as num).toDouble(),
      );
}
