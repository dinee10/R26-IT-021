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
    final request =
        http.MultipartRequest('POST', Uri.parse('$baseUrl/api/predict'))
          ..fields['model_type'] = modelType
          ..fields['validate_category'] = 'true';
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

  Future<List<OrganDetection>> detectOrgans(XFile image) async {
    final request =
        http.MultipartRequest('POST', Uri.parse('$baseUrl/api/detect-organs'))
          ..fields['confidence'] = '0.35'
          ..files.add(
            http.MultipartFile.fromBytes(
              'image',
              await image.readAsBytes(),
              filename: image.name,
            ),
          );
    try {
      final response = await http.Response.fromStream(
        await _client.send(request).timeout(_timeout),
      );
      final body = _decode(response);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw PlantApiException(
          body is Map<String, dynamic>
              ? body['error'] as String? ?? 'Live detection failed.'
              : 'Live detection failed (${response.statusCode}).',
        );
      }
      if (body is! Map<String, dynamic> || body['detections'] is! List) {
        throw PlantApiException(
          'The detector returned an unexpected response.',
        );
      }
      return (body['detections'] as List)
          .whereType<Map<String, dynamic>>()
          .map(OrganDetection.fromJson)
          .toList();
    } on TimeoutException {
      throw PlantApiException('Live detection timed out.');
    } on http.ClientException {
      throw PlantApiException('Cannot reach the detector at $baseUrl.');
    } on PlantApiException {
      rethrow;
    }
  }

  Future<LiveScanResult> identifyLive(XFile image) async {
    final request =
        http.MultipartRequest('POST', Uri.parse('$baseUrl/api/identify-live'))
          ..fields['confidence'] = '0.35'
          ..files.add(
            http.MultipartFile.fromBytes(
              'image',
              await image.readAsBytes(),
              filename: image.name,
            ),
          );
    try {
      final response = await http.Response.fromStream(
        await _client.send(request).timeout(_timeout),
      );
      final body = _decode(response);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw PlantApiException(
          body is Map<String, dynamic>
              ? body['error'] as String? ?? 'Live identification failed.'
              : 'Live identification failed (${response.statusCode}).',
        );
      }
      if (body is! Map<String, dynamic>) {
        throw PlantApiException(
          'The detector returned an unexpected response.',
        );
      }
      return LiveScanResult.fromJson(body);
    } on TimeoutException {
      throw PlantApiException('Live identification timed out.');
    } on http.ClientException {
      throw PlantApiException('Cannot reach the detector at $baseUrl.');
    } on PlantApiException {
      rethrow;
    }
  }

  Future<PlantHealthAssessment> assessHealth(XFile image) async {
    final request =
        http.MultipartRequest('POST', Uri.parse('$baseUrl/api/assess-health'))
          ..files.add(
            http.MultipartFile.fromBytes(
              'image',
              await image.readAsBytes(),
              filename: image.name,
            ),
          );
    try {
      final response = await http.Response.fromStream(
        await _client.send(request).timeout(_timeout),
      );
      final body = _decode(response);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw PlantApiException(
          body is Map<String, dynamic>
              ? body['error'] as String? ?? 'Health assessment failed.'
              : 'Health assessment failed (${response.statusCode}).',
        );
      }
      if (body is! Map<String, dynamic>) {
        throw PlantApiException('The server returned an unexpected response.');
      }
      return PlantHealthAssessment.fromJson(body);
    } on TimeoutException {
      throw PlantApiException('Health assessment timed out.');
    } on http.ClientException {
      throw PlantApiException('Cannot reach the detector at $baseUrl.');
    } on PlantApiException {
      rethrow;
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

class OrganDetection {
  const OrganDetection({
    required this.label,
    required this.confidencePercent,
    required this.left,
    required this.top,
    required this.right,
    required this.bottom,
  });

  factory OrganDetection.fromJson(Map<String, dynamic> json) {
    final box = json['box'] as Map<String, dynamic>? ?? const {};
    double number(Object? value) => (value as num?)?.toDouble() ?? 0;
    return OrganDetection(
      label: json['label'] as String? ?? 'object',
      confidencePercent: number(json['confidence_percent']),
      left: number(box['left']),
      top: number(box['top']),
      right: number(box['right']),
      bottom: number(box['bottom']),
    );
  }

  final String label;
  final double confidencePercent;
  final double left;
  final double top;
  final double right;
  final double bottom;
}

class LiveScanResult {
  const LiveScanResult({required this.detections, this.identification});

  factory LiveScanResult.fromJson(Map<String, dynamic> json) {
    final rawDetections = json['detections'] as List? ?? const [];
    final rawIdentification = json['identification'];
    return LiveScanResult(
      detections: rawDetections
          .whereType<Map<String, dynamic>>()
          .map(OrganDetection.fromJson)
          .toList(),
      identification: rawIdentification is Map<String, dynamic>
          ? LivePlantIdentification.fromJson(rawIdentification)
          : null,
    );
  }

  final List<OrganDetection> detections;
  final LivePlantIdentification? identification;
}

class LivePlantIdentification {
  const LivePlantIdentification({
    required this.organ,
    required this.plant,
    required this.organConfidencePercent,
    required this.confidencePercent,
    this.warning,
  });

  factory LivePlantIdentification.fromJson(Map<String, dynamic> json) {
    double number(Object? value) => (value as num?)?.toDouble() ?? 0;
    return LivePlantIdentification(
      organ: json['organ'] as String? ?? 'object',
      plant: json['plant'] as String? ?? 'Unknown',
      organConfidencePercent: number(json['organ_confidence_percent']),
      confidencePercent: number(json['confidence_percent']),
      warning: json['warning'] as String?,
    );
  }

  final String organ;
  final String plant;
  final double organConfidencePercent;
  final double confidencePercent;
  final String? warning;
}

class PlantHealthAssessment {
  const PlantHealthAssessment({
    required this.status,
    required this.label,
    required this.confidencePercent,
    required this.symptoms,
    required this.recommendations,
    required this.captureWarnings,
    required this.metrics,
    required this.disclaimer,
  });

  factory PlantHealthAssessment.fromJson(Map<String, dynamic> json) {
    List<String> strings(String key) => (json[key] as List? ?? const [])
        .map((item) => item.toString())
        .toList();
    final rawMetrics = json['metrics'] as Map<String, dynamic>? ?? const {};
    double number(Object? value) => (value as num?)?.toDouble() ?? 0;
    return PlantHealthAssessment(
      status: json['status'] as String? ?? 'inconclusive',
      label: json['label'] as String? ?? 'Inconclusive',
      confidencePercent: number(json['confidence_percent']),
      symptoms: strings('symptoms'),
      recommendations: strings('recommendations'),
      captureWarnings: strings('capture_warnings'),
      metrics: rawMetrics.map((key, value) => MapEntry(key, number(value))),
      disclaimer: json['disclaimer'] as String? ?? '',
    );
  }

  final String status;
  final String label;
  final double confidencePercent;
  final List<String> symptoms;
  final List<String> recommendations;
  final List<String> captureWarnings;
  final Map<String, double> metrics;
  final String disclaimer;
}

class PlantApiException implements Exception {
  PlantApiException(this.message);
  final String message;
  @override
  String toString() => message;
}
