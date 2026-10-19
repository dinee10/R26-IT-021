import 'package:flutter/foundation.dart';

/// Resolves every backend endpoint from one build-time origin.
///
/// Production builds must provide an HTTPS origin with:
/// `--dart-define=API_BASE_URL=https://api.example.com`
class ApiConfig {
  const ApiConfig._();

  static const _configuredOrigin = String.fromEnvironment('API_BASE_URL');

  static String get origin {
    final configured = _configuredOrigin.trim();
    if (configured.isNotEmpty) {
      return configured.replaceFirst(RegExp(r'/+$'), '');
    }
    if (kIsWeb) {
      final host = Uri.base.host.isEmpty ? '127.0.0.1' : Uri.base.host;
      return 'http://$host:5000';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:5000';
    }
    return 'http://127.0.0.1:5000';
  }

  static Uri endpoint(String path) {
    final normalizedPath = path.replaceFirst(RegExp(r'^/+'), '');
    return Uri.parse('$origin/api/$normalizedPath');
  }
}
