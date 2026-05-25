class DigestEvent {
  DigestEvent({
    required this.icon,
    required this.title,
    required this.detail,
    this.amountRm,
  });

  final String icon;
  final String title;
  final String detail;
  final double? amountRm;

  factory DigestEvent.fromJson(Map<String, dynamic> j) => DigestEvent(
        icon: j['icon'] as String,
        title: j['title'] as String,
        detail: j['detail'] as String,
        amountRm: (j['amount_rm'] as num?)?.toDouble(),
      );
}

class DigestResponse {
  DigestResponse({
    required this.smeId,
    required this.weekLabel,
    required this.events,
    required this.summary,
  });

  final int smeId;
  final String weekLabel;
  final List<DigestEvent> events;
  final String summary;

  factory DigestResponse.fromJson(Map<String, dynamic> j) => DigestResponse(
        smeId: j['sme_id'] as int,
        weekLabel: j['week_label'] as String,
        events: (j['events'] as List<dynamic>? ?? [])
            .map((e) => DigestEvent.fromJson(e as Map<String, dynamic>))
            .toList(),
        summary: j['summary'] as String,
      );
}
