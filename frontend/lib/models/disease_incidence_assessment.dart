class DiseaseIncidenceAssessment {
  const DiseaseIncidenceAssessment({
    required this.status,
    required this.accepted,
    required this.totalSubmitted,
    required this.totalAccepted,
    required this.healthyCount,
    required this.healthyPercentage,
    required this.conditions,
    required this.samples,
    required this.warnings,
    required this.limitations,
    this.reason,
    this.species,
    this.primaryCondition,
  });

  factory DiseaseIncidenceAssessment.fromJson(Map<String, dynamic> json) {
    final locked = json['locked_species'] as Map<String, dynamic>?;
    final initial =
        json['initial_condition_under_verification'] as Map<String, dynamic>?;
    return DiseaseIncidenceAssessment(
      status: json['assessment_status'] as String? ?? 'insufficient_evidence',
      accepted: json['accepted'] == true,
      reason: json['reason'] as String?,
      species: locked?['species'] as String?,
      primaryCondition:
          initial?['display_name'] as String? ?? initial?['class'] as String?,
      totalSubmitted: (json['total_submitted_images'] as num?)?.toInt() ?? 0,
      totalAccepted: (json['total_accepted_images'] as num?)?.toInt() ?? 0,
      healthyCount: (json['healthy_sample_count'] as num?)?.toInt() ?? 0,
      healthyPercentage: (json['healthy_percentage'] as num?)?.toDouble(),
      conditions: _mapList(
        json['per_condition_results'],
        IncidenceCondition.fromJson,
      ),
      samples: _mapList(
        json['individual_leaf_predictions'],
        LeafSamplePrediction.fromJson,
      ),
      warnings: _strings(json['sampling_warnings']),
      limitations: _strings(json['scientific_limitations']),
    );
  }

  final String status;
  final bool accepted;
  final String? reason;
  final String? species;
  final String? primaryCondition;
  final int totalSubmitted;
  final int totalAccepted;
  final int healthyCount;
  final double? healthyPercentage;
  final List<IncidenceCondition> conditions;
  final List<LeafSamplePrediction> samples;
  final List<String> warnings;
  final List<String> limitations;
}

class IncidenceCondition {
  const IncidenceCondition({
    required this.name,
    required this.category,
    required this.matchingCount,
    required this.acceptedCount,
    required this.percentage,
    required this.level,
    required this.ruleAvailability,
    required this.interpretation,
    required this.verification,
    required this.care,
    required this.followUp,
    required this.harvestCaution,
    required this.references,
    required this.limitations,
  });

  factory IncidenceCondition.fromJson(Map<String, dynamic> json) =>
      IncidenceCondition(
        name: (json['condition_name'] as String? ?? '').replaceAll('_', ' '),
        category: (json['condition_category'] as String? ?? '').replaceAll(
          '_',
          ' ',
        ),
        matchingCount: (json['matching_sample_count'] as num?)?.toInt() ?? 0,
        acceptedCount: (json['accepted_sample_count'] as num?)?.toInt() ?? 0,
        percentage: (json['calculated_percentage'] as num?)?.toDouble() ?? 0,
        level: (json['incidence_level'] as String? ?? '').replaceAll('_', ' '),
        ruleAvailability:
            json['rule_availability'] as String? ?? 'rules_unavailable',
        interpretation: json['assessment_interpretation'] as String? ?? '',
        verification: json['verification_steps'] as String? ?? '',
        care: json['recommended_care'] as String? ?? '',
        followUp: json['escalation_or_follow_up'] as String? ?? '',
        harvestCaution: json['medicinal_harvest_caution'] as String? ?? '',
        references: _mapList(json['references'], IncidenceReference.fromJson),
        limitations: _strings(json['scientific_limitations']),
      );

  final String name;
  final String category;
  final int matchingCount;
  final int acceptedCount;
  final double percentage;
  final String level;
  final String ruleAvailability;
  final String interpretation;
  final String verification;
  final String care;
  final String followUp;
  final String harvestCaution;
  final List<IncidenceReference> references;
  final List<String> limitations;
}

class IncidenceReference {
  const IncidenceReference({
    required this.id,
    required this.title,
    required this.publisher,
    required this.url,
  });
  factory IncidenceReference.fromJson(Map<String, dynamic> json) =>
      IncidenceReference(
        id: json['reference_id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        publisher: json['publisher'] as String? ?? '',
        url: json['url'] as String? ?? '',
      );
  final String id;
  final String title;
  final String publisher;
  final String url;
}

class LeafSamplePrediction {
  const LeafSamplePrediction({
    required this.index,
    required this.filename,
    required this.included,
    this.region,
    this.reason,
    this.species,
    this.condition,
    this.confidence,
  });
  factory LeafSamplePrediction.fromJson(Map<String, dynamic> json) {
    final plant = json['plant'] as Map<String, dynamic>?;
    final condition = json['condition'] as Map<String, dynamic>?;
    return LeafSamplePrediction(
      index: (json['sample_index'] as num?)?.toInt() ?? 0,
      filename: json['filename'] as String? ?? 'sample',
      included: json['included'] == true,
      region: json['region'] as String?,
      reason: json['exclusion_reason'] as String?,
      species: plant?['species'] as String?,
      condition:
          condition?['display_name'] as String? ??
          condition?['class'] as String?,
      confidence: (condition?['confidence'] as num?)?.toDouble(),
    );
  }
  final int index;
  final String filename;
  final bool included;
  final String? region;
  final String? reason;
  final String? species;
  final String? condition;
  final double? confidence;
}

List<T> _mapList<T>(Object? value, T Function(Map<String, dynamic>) parser) =>
    (value as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(parser)
        .toList();

List<String> _strings(Object? value) =>
    (value as List? ?? const []).map((item) => item.toString()).toList();
