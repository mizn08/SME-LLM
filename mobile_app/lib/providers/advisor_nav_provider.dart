import 'package:flutter/foundation.dart';

/// Jump to a sub-tab inside AI Advisor (e.g. SME Quote from drawer).
class AdvisorNavProvider extends ChangeNotifier {
  int? pendingSubTab;

  void openSubTab(int index) {
    pendingSubTab = index;
    notifyListeners();
  }

  int? consumePending() {
    final v = pendingSubTab;
    pendingSubTab = null;
    return v;
  }
}
