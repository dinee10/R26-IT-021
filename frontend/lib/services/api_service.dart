import 'dart:convert';

import 'package:http/http.dart' as http;

class PlantRecommendation {
  const PlantRecommendation({
    required this.name,
    required this.score,
    required this.reason,
  });

  final String name;
  final int score;
  final String reason;

  factory PlantRecommendation.fromJson(Map<String, dynamic> json) {
    return PlantRecommendation(
      name: json['name'] as String,
      score: (json['score'] as num).toInt(),
      reason: json['reason'] as String,
    );
  }
}

class ApiService {
  ApiService({http.Client? client}) : _client = client ?? http.Client();

  static const _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:5000/api',
  );

  final http.Client _client;

  Future<List<PlantRecommendation>> recommend(
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
    return items
        .map((item) => PlantRecommendation.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}

class ApiException implements Exception {
  const ApiException(this.message);

  final String message;
}
