import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/disease_incidence_assessment.dart';

void main() {
  test('parses mixed conditions, excluded leaves, and references', () {
    final result = DiseaseIncidenceAssessment.fromJson({
      'assessment_status': 'completed',
      'accepted': true,
      'locked_species': {'species': 'Neem'},
      'initial_condition_under_verification': {
        'class': 'Leaf_Spot',
        'display_name': 'Leaf Spot',
      },
      'total_submitted_images': 4,
      'total_accepted_images': 3,
      'healthy_sample_count': 1,
      'healthy_percentage': 33.333333,
      'per_condition_results': [
        {
          'condition_name': 'Leaf_Spot',
          'condition_category': 'fungal_disease',
          'matching_sample_count': 2,
          'accepted_sample_count': 3,
          'calculated_percentage': 66.666666,
          'incidence_level': 'High',
          'rule_availability': 'available',
          'assessment_interpretation': 'Repeated detections.',
          'verification_steps': 'Inspect leaves.',
          'recommended_care': 'Use source-informed care.',
          'escalation_or_follow_up': 'Review again.',
          'medicinal_harvest_caution': 'Not a safety clearance.',
          'references': [
            {'reference_id': 'R1', 'title': 'Reference', 'publisher': 'Publisher', 'url': 'https://example.test'},
          ],
          'scientific_limitations': ['Sample incidence only.'],
        },
      ],
      'individual_leaf_predictions': [
        {'sample_index': 0, 'filename': 'one.jpg', 'included': true, 'condition': {'display_name': 'Leaf Spot', 'confidence': .95}},
        {'sample_index': 3, 'filename': 'bad.jpg', 'included': false, 'exclusion_reason': 'IMAGE_TOO_BLURRY'},
      ],
      'sampling_warnings': ['Small sample.'],
      'scientific_limitations': ['Not whole-plant severity.'],
    });

    expect(result.species, 'Neem');
    expect(result.primaryCondition, 'Leaf Spot');
    expect(result.totalAccepted, 3);
    expect(result.conditions.single.percentage, closeTo(66.666666, .000001));
    expect(result.conditions.single.references.single.id, 'R1');
    expect(result.samples.last.included, isFalse);
    expect(result.samples.last.reason, 'IMAGE_TOO_BLURRY');
  });

  test('parses rules unavailable without inventing references', () {
    final result = DiseaseIncidenceAssessment.fromJson({
      'accepted': true,
      'per_condition_results': [
        {
          'condition_name': 'Fungus',
          'rule_availability': 'rules_unavailable',
          'references': [],
        },
      ],
    });
    expect(result.conditions.single.ruleAvailability, 'rules_unavailable');
    expect(result.conditions.single.references, isEmpty);
  });
}
