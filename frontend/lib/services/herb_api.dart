import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

import '../models/prediction_result.dart';

class HerbApi {
  HerbApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  static const Duration _requestTimeout = Duration(seconds: 45);

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

  Future<PredictionResult> predict(
    List<XFile> images, {
    String modelType = 'plant',
  }) async {
    final uri = Uri.parse('$baseUrl/api/predict');
    final request = http.MultipartRequest('POST', uri);
    request.fields['model_type'] = modelType;

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
      final streamed = await _client.send(request).timeout(_requestTimeout);
      final response = await http.Response.fromStream(streamed);
      Object? decodedBody;
      try {
        decodedBody = jsonDecode(response.body);
      } on FormatException {
        throw HerbApiException(
          'The backend returned an invalid response (status ${response.statusCode}).',
        );
      }

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
    } on HerbApiException {
      rethrow;
    } on TimeoutException {
      throw HerbApiException(
        'Prediction timed out. Try fewer or smaller images and check the backend.',
      );
    } catch (error) {
      throw HerbApiException('Prediction failed: $error');
    }
  }

  Future<VerificationRequest> requestVerification({
    required List<XFile> images,
    required PredictionResult prediction,
    required bool trainingConsent,
  }) async {
    final request =
        http.MultipartRequest('POST', Uri.parse('$baseUrl/api/verifications'))
          ..fields['ai_identification'] = prediction.plant
          ..fields['ai_confidence'] = prediction.confidencePercent.toString()
          ..fields['training_consent'] = trainingConsent.toString();
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
      final streamed = await _client.send(request).timeout(_requestTimeout);
      return _decodeVerification(await http.Response.fromStream(streamed));
    } on TimeoutException {
      throw HerbApiException('Submitting for expert review timed out.');
    } on http.ClientException catch (error) {
      throw HerbApiException('Could not reach the backend. ${error.message}');
    }
  }

  Future<VerificationRequest> getVerification(String id) async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/api/verifications/$id'))
          .timeout(_requestTimeout);
      return _decodeVerification(response);
    } on TimeoutException {
      throw HerbApiException('Checking the expert review timed out.');
    } on http.ClientException catch (error) {
      throw HerbApiException('Could not reach the backend. ${error.message}');
    }
  }

  VerificationRequest _decodeVerification(http.Response response) {
    Object? body;
    try {
      body = jsonDecode(response.body);
    } on FormatException {
      throw HerbApiException('The backend returned an invalid response.');
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw HerbApiException(
        body is Map<String, dynamic>
            ? body['error'] as String? ?? 'Verification request failed.'
            : 'Verification request failed.',
      );
    }
    if (body is! Map<String, dynamic>) {
      throw HerbApiException('Unexpected verification response.');
    }
    return VerificationRequest.fromJson(body);
  }
}

class HerbApiException implements Exception {
  HerbApiException(this.message);

  final String message;

  @override
  String toString() => message;
}
