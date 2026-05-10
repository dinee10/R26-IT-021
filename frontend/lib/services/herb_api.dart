import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

import '../models/prediction_result.dart';

class HerbApi {
  HerbApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  static const String _configuredBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );

  static String get baseUrl {
    if (_configuredBaseUrl.isNotEmpty) {
      return _configuredBaseUrl;
    }

    if (kIsWeb) {
      final host = Uri.base.host;
      return 'http://${host.isEmpty ? '127.0.0.1' : host}:5000';
    }

    if (defaultTargetPlatform == TargetPlatform.windows ||
        defaultTargetPlatform == TargetPlatform.macOS ||
        defaultTargetPlatform == TargetPlatform.linux) {
      return 'http://127.0.0.1:5000';
    }

    return 'http://10.0.2.2:5000';
  }

  Future<PredictionResult> predict(List<XFile> images) async {
    final uri = Uri.parse('$baseUrl/api/predict');
    final request = http.MultipartRequest('POST', uri);

    for (final image in images) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'images',
          await image.readAsBytes(),
          filename: image.name,
        ),
      );
    }

    try {
      final streamed = await _client.send(request);
      final response = await http.Response.fromStream(streamed);
      final decodedBody = jsonDecode(response.body);

      if (response.statusCode < 200 || response.statusCode >= 300) {
        if (decodedBody is Map<String, dynamic>) {
          throw HerbApiException(
            decodedBody['error'] as String? ?? 'Prediction failed.',
          );
        }
        throw HerbApiException(
          'Prediction failed with status ${response.statusCode}.',
        );
      }

      if (decodedBody is! Map<String, dynamic>) {
        throw HerbApiException('Unexpected response format from backend.');
      }

      return PredictionResult.fromJson(decodedBody);
    } on http.ClientException catch (error) {
      throw HerbApiException(
        'Could not reach the backend at $baseUrl. Make sure the Flask API is running on port 5000. ${error.message}',
      );
    } catch (error) {
      throw HerbApiException(error.toString());
    }
  }
}

class HerbApiException implements Exception {
  HerbApiException(this.message);

  final String message;

  @override
  String toString() => message;
}
