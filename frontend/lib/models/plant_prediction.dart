class PlantPrediction {
  const PlantPrediction({
    required this.plant,
    required this.modelType,
    required this.confidencePercent,
    required this.benefits,
    required this.topPredictions,
    required this.imageQuality,
    this.warning,
  });
  final String plant;
  final String modelType;
  final double confidencePercent;
  final PlantBenefits benefits;
  final List<PredictionMatch> topPredictions;
  final List<ImageQualityResult> imageQuality;
  final String? warning;

  factory PlantPrediction.fromJson(Map<String, dynamic> json) =>
      PlantPrediction(
        plant: json['plant'] as String? ?? 'Unknown',
        modelType: json['model_type'] as String? ?? 'plant',
        confidencePercent: (json['confidence_percent'] as num? ?? 0).toDouble(),
        warning: json['warning'] as String?,
        benefits: PlantBenefits.fromJson(
          json['benefits'] as Map<String, dynamic>? ?? const {},
        ),
        topPredictions: (json['top_predictions'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(PredictionMatch.fromJson)
            .toList(),
        imageQuality: (json['image_quality'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(ImageQualityResult.fromJson)
            .toList(),
      );
}

class PlantBenefits {
  const PlantBenefits({
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

  factory PlantBenefits.fromJson(Map<String, dynamic> json) => PlantBenefits(
    commonName: json['common_name'] as String? ?? 'Unknown',
    scientificName: json['scientific_name'] as String? ?? 'Unknown',
    traditionalUses: _strings(json['traditional_uses'], const [
      'Traditional-use information is not available.',
    ]),
    preparationNotes: _strings(json['preparation_notes'], const [
      'Do not prepare or consume without expert guidance.',
    ]),
    safetyWarning:
        json['safety_warning'] as String? ??
        'Verify this identification with a qualified professional.',
    medicalDisclaimer:
        json['medical_disclaimer'] as String? ??
        'For educational identification only; this is not medical advice.',
  );

  static List<String> _strings(Object? value, List<String> fallback) {
    final items = value is List
        ? value
              .map((item) => item.toString())
              .where((item) => item.isNotEmpty)
              .toList()
        : <String>[];
    return items.isEmpty ? fallback : items;
  }
}

class PredictionMatch {
  const PredictionMatch({required this.plant, required this.confidencePercent});
  final String plant;
  final double confidencePercent;
  factory PredictionMatch.fromJson(Map<String, dynamic> json) =>
      PredictionMatch(
        plant: json['plant'] as String? ?? 'Unknown',
        confidencePercent: (json['confidence_percent'] as num? ?? 0).toDouble(),
      );
}

class ImageQualityResult {
  const ImageQualityResult({
    required this.filename,
    required this.foregroundCropped,
    required this.warnings,
  });
  final String filename;
  final bool foregroundCropped;
  final List<String> warnings;
  factory ImageQualityResult.fromJson(Map<String, dynamic> json) =>
      ImageQualityResult(
        filename: json['filename'] as String? ?? 'Image',
        foregroundCropped: json['foreground_cropped'] as bool? ?? false,
        warnings: (json['warnings'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
      );
}
