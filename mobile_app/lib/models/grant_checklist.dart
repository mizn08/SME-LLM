class ChecklistItem {
  ChecklistItem({
    required this.document,
    this.required = true,
    this.tip = '',
  });

  final String document;
  final bool required;
  final String tip;

  factory ChecklistItem.fromJson(Map<String, dynamic> j) => ChecklistItem(
        document: j['document'] as String,
        required: j['required'] as bool? ?? true,
        tip: j['tip'] as String? ?? '',
      );
}

class GrantChecklistResponse {
  GrantChecklistResponse({
    required this.schemeId,
    required this.schemeName,
    required this.agency,
    this.deadlineLabel,
    this.contactEmail,
    this.contactPhone,
    this.applyUrl,
    required this.checklist,
  });

  final int schemeId;
  final String schemeName;
  final String agency;
  final String? deadlineLabel;
  final String? contactEmail;
  final String? contactPhone;
  final String? applyUrl;
  final List<ChecklistItem> checklist;

  factory GrantChecklistResponse.fromJson(Map<String, dynamic> j) => GrantChecklistResponse(
        schemeId: j['scheme_id'] as int,
        schemeName: j['scheme_name'] as String,
        agency: j['agency'] as String,
        deadlineLabel: j['deadline_label'] as String?,
        contactEmail: j['contact_email'] as String?,
        contactPhone: j['contact_phone'] as String?,
        applyUrl: j['apply_url'] as String?,
        checklist: (j['checklist'] as List<dynamic>? ?? [])
            .map((e) => ChecklistItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
