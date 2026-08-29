import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import '../models/plant_prediction.dart';

class PlantApi {
  PlantApi({http.Client? client}) : _client = client ?? http.Client();
  final http.Client _client;
  static const _timeout = Duration(seconds: 60);
  static const _configuredUrl = String.fromEnvironment('API_BASE_URL');

  static String get baseUrl {
    if (_configuredUrl.isNotEmpty) return _configuredUrl;
    if (kIsWeb)
      return 'http://${Uri.base.host.isEmpty ? '127.0.0.1' : Uri.base.host}:5000';
    if (defaultTargetPlatform == TargetPlatform.android)
      return 'http://10.0.2.2:5000';
    return 'http://127.0.0.1:5000';
  }

  Future<PlantPrediction> predict(List<XFile> images, String modelType) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/api/predict'),
    )..fields['model_type'] = modelType;
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
      final response = await http.Response.fromStream(
        await _client.send(request).timeout(_timeout),
      );
      final body = _decode(response);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw PlantApiException(
          body is Map<String, dynamic>
              ? body['error'] as String? ?? 'Identification failed.'
              : 'Identification failed (${response.statusCode}).',
        );
      }
      if (body is! Map<String, dynamic>)
        throw PlantApiException('The server returned an unexpected response.');
      return PlantPrediction.fromJson(body);
    } on TimeoutException {
      throw PlantApiException(
        'The request timed out. Try fewer or smaller images.',
      );
    } on http.ClientException {
      throw PlantApiException(
        'Cannot reach the detector at $baseUrl. Check that the backend is running.',
      );
    } on PlantApiException {
      rethrow;
    } catch (error) {
      throw PlantApiException('Could not identify these images: $error');
    }
  }

  Object? _decode(http.Response response) {
    try {
      return jsonDecode(response.body);
    } on FormatException {
      throw PlantApiException('The server returned invalid data.');
    }
  }
}

class PlantApiException implements Exception {
  PlantApiException(this.message);
  final String message;
  @override
  String toString() => message;
}
