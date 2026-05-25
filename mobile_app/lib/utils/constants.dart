import 'package:flutter/foundation.dart';

import 'api_config_stub.dart' if (dart.library.html) 'api_config_web.dart';

/// Override with `--dart-define=API_BASE=http://192.168.1.10:8000` for physical devices.
const String _apiFromEnv = String.fromEnvironment('API_BASE');

/// Live Render API (Flutter web is a separate static site on Render).
const String productionApiBase = 'https://sme-advisor-api.onrender.com';

String resolveApiBase() {
  if (_apiFromEnv.isNotEmpty) return _apiFromEnv;
  final fromMeta = readRuntimeApiBase();
  if (fromMeta != null && fromMeta.isNotEmpty && !_isStaleRenderApiMeta(fromMeta)) {
    return fromMeta;
  }
  if (kIsWeb) {
    final uri = Uri.base;
    final host = uri.host.toLowerCase();
    // API service URL (Swagger, health) — same origin, no :8000
    if (host.startsWith('sme-advisor-api')) {
      return '${uri.scheme}://$host';
    }
    // Static site on Render: sme-advisor-web-XXXX → sme-advisor-api-XXXX (same suffix)
    if (host.startsWith('sme-advisor-web')) {
      final apiHost = host.replaceFirst('sme-advisor-web', 'sme-advisor-api');
      return '${uri.scheme}://$apiHost';
    }
    // Other Render static hosts → try paired API hostname or fallback
    if (host.endsWith('.onrender.com')) {
      return productionApiBase;
    }
    // Local / LAN dev: page and API on same machine, API on port 8000
    if (host == 'localhost' || host == '127.0.0.1') {
      return 'http://${uri.host}:8000';
    }
    return '${uri.scheme}://${uri.host}:8000';
  }
  return 'http://127.0.0.1:8000';
}

/// Blueprint builds often bake generic API host; override when web has Render suffix.
bool _isStaleRenderApiMeta(String url) {
  final webHost = Uri.base.host.toLowerCase();
  if (!webHost.startsWith('sme-advisor-web-')) return false;
  final normalized = url.replaceAll(RegExp(r'/+$'), '').toLowerCase();
  return normalized == 'https://sme-advisor-api.onrender.com';
}
