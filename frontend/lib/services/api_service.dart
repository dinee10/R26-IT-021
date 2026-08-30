import 'dart:convert';

import 'package:http/http.dart' as http;

class PlantRecommendation {
  const PlantRecommendation({
    required this.name,
    required this.score,
    required this.reason,
    this.whySuitable,
    this.soilRequirement,
    this.sunlightRequirement,
    this.wateringRequirement,
    this.plantingMethod,
    this.fertilizerCare,
    this.growingPeriod,
    this.sellingPrice,
    this.harvestingInformation,
  });

  final String name;
  final int score;
  final String reason;
  final String? whySuitable;
  final String? soilRequirement;
  final String? sunlightRequirement;
  final String? wateringRequirement;
  final String? plantingMethod;
  final String? fertilizerCare;
  final String? growingPeriod;
  final String? sellingPrice;
  final String? harvestingInformation;

  factory PlantRecommendation.fromJson(Map<String, dynamic> json) {
    return PlantRecommendation(
      name: json['name'] as String,
      score: (json['score'] as num).toInt(),
      reason: json['reason'] as String,
      whySuitable: json['whySuitable'] as String?,
      soilRequirement: json['soilRequirement'] as String?,
      sunlightRequirement: json['sunlightRequirement'] as String?,
      wateringRequirement: json['wateringRequirement'] as String?,
      plantingMethod: json['plantingMethod'] as String?,
      fertilizerCare: json['fertilizerCare'] as String?,
      growingPeriod: json['growingPeriod'] as String?,
      sellingPrice: json['sellingPrice'] as String?,
      harvestingInformation: json['harvestingInformation'] as String?,
    );
  }
}

class RecommendationResult {
  const RecommendationResult({required this.bestPlant, required this.recommendations});

  final PlantRecommendation bestPlant;
  final List<PlantRecommendation> recommendations;
}

class ApiService {
  ApiService({http.Client? client}) : _client = client ?? http.Client();

  static const _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:5000/api',
  );

  final http.Client _client;

  Future<RecommendationResult> recommend(
    Map<String, dynamic> input,
  ) async {
    final response = await _client
        .post(
          Uri.parse('$_baseUrl/recommend'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(input),
        )
        .timeout(const Duration(seconds: 15));

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode != 200) {
      throw ApiException(body['error'] as String? ?? 'Recommendation failed.');
    }

    final items = body['recommendations'] as List<dynamic>;
    final recommendations = items
        .map((item) => PlantRecommendation.fromJson(item as Map<String, dynamic>))
        .toList();
    final bestPlant = PlantRecommendation.fromJson(body['bestPlant'] as Map<String, dynamic>);
    return RecommendationResult(bestPlant: bestPlant, recommendations: recommendations);
  }
}

class ApiException implements Exception {
  const ApiException(this.message);

  final String message;
}
