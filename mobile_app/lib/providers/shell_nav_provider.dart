import 'package:flutter/foundation.dart';

/// Switch main bottom-nav tab from any screen (workflow quick actions).
class ShellNavProvider extends ChangeNotifier {
  int _tabIndex = 0;

  int get tabIndex => _tabIndex;

  void goToTab(int index) {
    final i = index.clamp(0, 4);
    if (_tabIndex == i) return;
    _tabIndex = i;
    notifyListeners();
  }
}
