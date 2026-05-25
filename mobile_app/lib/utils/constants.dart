import 'package:flutter/foundation.dart';

import 'api_config_stub.dart' if (dart.library.html) 'api_config_web.dart';

/// Override with `--dart-define=API_BASE=http://192.168.1.10:8000` for physical devices.
const String _apiFromEnv = String.fromEnvironment('API_BASE');

/// Live Render API (Flutter web is a separate static site on Render).
const String productionApiBase = 'https://sme-advisor-api.onrender.com';

String resolveApiBase() {
  // Render: baked --dart-define=API_BASE often points at generic host; pair from web hostname first.
  if (kIsWeb) {
    final paired = _renderPairedApiBase();
    if (paired != null) return paired;
  }

  if (_apiFromEnv.isNotEmpty && !_isStaleRenderApiMeta(_apiFromEnv)) {
    return _normalizeBase(_apiFromEnv);
  }

  final fromMeta = readRuntimeApiBase();
  if (fromMeta != null && fromMeta.isNotEmpty && !_isStaleRenderApiMeta(fromMeta)) {
    return _normalizeBase(fromMeta);
  }

  if (kIsWeb) {
    final uri = Uri.base;
    final host = uri.host.toLowerCase();
    if (host.endsWith('.onrender.com')) {
      return productionApiBase;
    }
    if (host == 'localhost' || host == '127.0.0.1') {
      return 'http://${uri.host}:8000';
    }
    return '${uri.scheme}://${uri.host}:8000';
  }
  return 'http://127.0.0.1:8000';
}

/// sme-advisor-web-38lz.onrender.com → https://sme-advisor-api-38lz.onrender.com
String? _renderPairedApiBase() {
  final uri = Uri.base;
  final host = uri.host.toLowerCase();
  if (host.startsWith('sme-advisor-api')) {
    return _normalizeBase('${uri.scheme}://$host');
  }
  if (host.startsWith('sme-advisor-web')) {
    final apiHost = host.replaceFirst('sme-advisor-web', 'sme-advisor-api');
    return _normalizeBase('${uri.scheme}://$apiHost');
  }
  return null;
}

String _normalizeBase(String url) {
  final u = url.trim();
  if (u.endsWith('/')) return u.substring(0, u.length - 1);
  return u;
}

/// Blueprint builds often bake generic API host; override when web has Render suffix.
bool _isStaleRenderApiMeta(String url) {
  final webHost = Uri.base.host.toLowerCase();
  if (!webHost.startsWith('sme-advisor-web-')) return false;
  final normalized = url.replaceAll(RegExp(r'/+$'), '').toLowerCase();
  // Generic API host without Blueprint suffix — wrong for sme-advisor-web-XXXX
  return normalized == 'https://sme-advisor-api.onrender.com' ||
      (normalized.contains('sme-advisor-api.onrender.com') && !normalized.contains('sme-advisor-api-'));
}
