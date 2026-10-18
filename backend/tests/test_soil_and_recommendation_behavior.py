import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crs_soil.crs_soil_model import SoilClassifierService
from crs_soil.crs_soil_training import check_soil_training_readiness
from cultivation.train_recommendation import FEATURE_COLUMNS, predict_top_plants


class SoilAndRecommendationBehaviorTests(unittest.TestCase):
    def test_recommendation_confidence_is_not_100_percent(self):
        payload = {
            'temperature': 28,
            'rainfall': 180,
            'humidity': 72,
            'growingSpace': '1-5 perches',
            'budgetAmount': 2500,
            'budgetCurrency': 'LKR',
            'irrigationMethod': 'Hand watering',
            'growingSeason': 'May',
            'growingDuration': 'Medium',
            'soilType': 'Loamy',
            'soilPh': 6.5,
        }
        predictions = predict_top_plants(payload)
        self.assertGreater(len(predictions), 0)
        self.assertLess(max(item['confidence'] for item in predictions), 1.0)
        self.assertNotIn('sunlight', FEATURE_COLUMNS)

    def test_sunlight_input_does_not_change_recommendations(self):
        payload = {
            'temperature': 28,
            'rainfall': 180,
            'humidity': 72,
            'growingSpace': '1-5 perches',
            'budgetAmount': 2500,
            'budgetCurrency': 'LKR',
            'irrigationMethod': 'Hand watering',
            'growingSeason': 'May',
            'growingDuration': 'Medium',
            'soilType': 'Loamy',
            'soilPh': 6.5,
        }
        no_sunlight = predict_top_plants(payload)
        with_sunlight = predict_top_plants({**payload, 'sunlight': 'Full sun'})
        self.assertEqual(no_sunlight, with_sunlight)

    def test_soil_prediction_requires_an_uploaded_image(self):
        service = SoilClassifierService()
        result = service.predict(None)
        self.assertFalse(result['success'])
        self.assertFalse(result['available'])
        self.assertIn('no soil image', result['message'].lower())

    def test_soil_dataset_has_matching_nonempty_splits(self):
        readiness = check_soil_training_readiness()
        self.assertTrue(readiness['dataset_available'], readiness['message'])
        self.assertEqual(
            set(readiness['classes']),
            set(readiness['image_counts']['validation']),
        )
        self.assertEqual(
            set(readiness['classes']),
            set(readiness['image_counts']['test']),
        )


if __name__ == '__main__':
    unittest.main()
