class PredictionResult {
  PredictionResult({
    required this.plant,
    required this.confidencePercent,
    required this.benefits,
    required this.topPredictions,
    this.warning,
  });

  final String plant;
  final double confidencePercent;
  final HerbBenefits benefits;
  final List<TopPrediction> topPredictions;
  final String? warning;

  factory PredictionResult.fromJson(Map<String, dynamic> json) {
    return PredictionResult(
      plant: json['plant'] as String? ?? 'Unknown',
      confidencePercent: (json['confidence_percent'] as num? ?? 0).toDouble(),
      warning: json['warning'] as String?,
      benefits: HerbBenefits.fromJson(
        json['benefits'] as Map<String, dynamic>? ?? const {},
      ),
      topPredictions: (json['top_predictions'] as List<dynamic>? ?? const [])
          .map((item) => TopPrediction.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class HerbBenefits {
  HerbBenefits({
    required this.commonName,
    required this.scientificName,
    required this.traditionalUses,
    required this.preparationNotes,
    required this.safetyWarning,
    required this.medicalDisclaimer,
  });

  final String commonName;
  final String scientificName;
  final List<String> traditionalUses;
  final List<String> preparationNotes;
  final String safetyWarning;
  final String medicalDisclaimer;

  factory HerbBenefits.fromJson(Map<String, dynamic> json) {
    final legacyBenefits = _stringList(json['benefits']);

    return HerbBenefits(
      commonName: json['common_name'] as String? ?? 'Unknown',
      scientificName: json['scientific_name'] as String? ?? 'Unknown',
      traditionalUses: _stringList(
        json['traditional_uses'],
        fallback: legacyBenefits.isEmpty
            ? const ['Traditional use information has not been added yet.']
            : legacyBenefits,
      ),
      preparationNotes: _stringList(
        json['preparation_notes'],
        fallback: const [
          'Preparation notes are not available. Do not prepare or consume this plant without expert guidance.',
        ],
      ),
      safetyWarning:
          json['safety_warning'] as String? ??
          json['safety'] as String? ??
          'Use caution and verify this plant with a qualified professional.',
      medicalDisclaimer:
          json['medical_disclaimer'] as String? ??
          'This app is for educational plant identification only and is not medical advice.',
    );
  }

  static List<String> _stringList(
    Object? value, {
    List<String> fallback = const [],
  }) {
    final items = value is List<dynamic>
        ? value.map((item) => item.toString()).toList()
        : <String>[];
    return items.isEmpty ? fallback : items;
  }
}

class TopPrediction {
  TopPrediction({required this.plant, required this.confidencePercent});

  final String plant;
  final double confidencePercent;

  factory TopPrediction.fromJson(Map<String, dynamic> json) {
    return TopPrediction(
      plant: json['plant'] as String? ?? 'Unknown',
      confidencePercent: (json['confidence_percent'] as num? ?? 0).toDouble(),
    );
  }
}
