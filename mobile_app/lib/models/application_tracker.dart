class ApplicationTrackerItem {
  ApplicationTrackerItem({
    required this.id,
    required this.smeId,
    required this.productName,
    required this.productType,
    required this.status,
    this.notes,
    required this.createdAt,
    required this.updatedAt,
  });

  final int id;
  final int smeId;
  final String productName;
  final String productType;
  final String status;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory ApplicationTrackerItem.fromJson(Map<String, dynamic> j) => ApplicationTrackerItem(
        id: j['id'] as int,
        smeId: j['sme_id'] as int,
        productName: j['product_name'] as String,
        productType: j['product_type'] as String,
        status: j['status'] as String,
        notes: j['notes'] as String?,
        createdAt: DateTime.parse(j['created_at'] as String),
        updatedAt: DateTime.parse(j['updated_at'] as String),
      );
}

class ApplicationTrackerResponse {
  ApplicationTrackerResponse({required this.smeId, required this.applications});

  final int smeId;
  final List<ApplicationTrackerItem> applications;

  factory ApplicationTrackerResponse.fromJson(Map<String, dynamic> j) =>
      ApplicationTrackerResponse(
        smeId: j['sme_id'] as int,
        applications: (j['applications'] as List<dynamic>? ?? [])
            .map((e) => ApplicationTrackerItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
