import 'package:flutter/foundation.dart';

/// Resolves one backend origin for every feature in the application.
///
/// Production builds should pass the origin without `/api`, for example:
/// `--dart-define=API_BASE_URL=https://api.example.com`.
class ApiConfig {
  const ApiConfig._();

  static const _configuredUrl = String.fromEnvironment('API_BASE_URL');

  static String get origin {
    var value = _configuredUrl.trim();
    if (value.isNotEmpty) {
      value = value.replaceFirst(RegExp(r'/+$'), '');
      // Accept the old documented format as well, but expose one normalized
      // origin so callers cannot accidentally produce `/api/api/...`.
      if (value.endsWith('/api')) {
        value = value.substring(0, value.length - 4);
      }
      return value;
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

  static String get apiBaseUrl => '$origin/api';
}
