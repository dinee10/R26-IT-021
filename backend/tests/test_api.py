import sys
import unittest
from io import BytesIO
from pathlib import Path

from flask import Flask

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.routes.api import bp
from crs_soil.crs_soil_model import _MODEL_CACHE


class ApiBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = Flask(__name__)
        app.register_blueprint(bp)
        cls.client = app.test_client()

    def test_recommendation_does_not_require_sunlight(self):
        response = self.client.post(
            '/api/recommend',
            json={
                'temperature': 28,
                'rainfall': 180,
                'humidity': 72,
                'soilPh': 6.5,
                'soilType': 'Loamy',
                'growingSpace': '1-5 perches',
                'budgetAmount': 2500,
                'budgetCurrency': 'LKR',
                'irrigationMethod': 'Hand watering',
                'growingSeason': 'May',
                'growingDuration': 'Medium',
            },
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertTrue(body['recommendations'])
        self.assertNotIn('sunlightRequirement', body['recommendations'][0])

    def test_soil_prediction_endpoint_uses_trained_model(self):
        image_path = ROOT / 'dataset' / 'soil' / 'test' / 'Alluvial soil'
        image_path = next(image_path.glob('*'))
        with image_path.open('rb') as image_file:
            image_bytes = image_file.read()

        cache_key = (
            str((ROOT / 'crs_soil' / 'soil_model.keras').resolve()),
            str((ROOT / 'crs_soil' / 'soil_labels.json').resolve()),
            str((ROOT / 'crs_soil' / 'soil_feature_bank.npz').resolve()),
        )
        cached_model = _MODEL_CACHE.get(cache_key)
        for attempt in range(2):
            response = self.client.post(
                '/api/predict-soil',
                data={'image': (BytesIO(image_bytes), image_path.name)},
                content_type='multipart/form-data',
            )

            self.assertEqual(response.status_code, 200, response.get_json())
            body = response.get_json()
            self.assertTrue(body['success'])
            self.assertEqual(body['soil_type'], 'Alluvial soil')
            self.assertGreaterEqual(body['confidence'], 0.0)
            self.assertLessEqual(body['confidence'], 1.0)
            if attempt == 0:
                cached_model = _MODEL_CACHE[cache_key]
            else:
                self.assertIs(_MODEL_CACHE[cache_key], cached_model)

    def test_soil_prediction_rejects_non_soil_images(self):
        fixture_dir = ROOT / 'tests' / 'fixtures' / 'non_soil'
        for image_name in (
            'people_001.jpg',
            'pets_001.jpg',
            'flowers_001.jpg',
            'roots_001.jpg',
            'trees_001.jpg',
        ):
            with self.subTest(image=image_name):
                image_path = fixture_dir / image_name
                with image_path.open('rb') as image_file:
                    response = self.client.post(
                        '/api/predict-soil',
                        data={'image': (BytesIO(image_file.read()), image_name)},
                        content_type='multipart/form-data',
                    )

                self.assertEqual(response.status_code, 200, response.get_json())
                body = response.get_json()
                self.assertFalse(body['success'])
                self.assertIsNone(body['soil_type'])
                self.assertIn('supported soil type', body['message'])

    def test_soil_prediction_classifies_each_supported_soil(self):
        test_dir = ROOT / 'dataset' / 'soil' / 'test'
        for soil_type in ('Alluvial soil', 'Black Soil', 'Clay soil', 'Red soil'):
            with self.subTest(soil_type=soil_type):
                image_path = next((test_dir / soil_type).glob('*'))
                with image_path.open('rb') as image_file:
                    response = self.client.post(
                        '/api/predict-soil',
                        data={'image': (BytesIO(image_file.read()), image_path.name)},
                        content_type='multipart/form-data',
                    )

                self.assertEqual(response.status_code, 200, response.get_json())
                body = response.get_json()
                self.assertTrue(body['success'])
                self.assertEqual(body['soil_type'], soil_type)


if __name__ == '__main__':
    unittest.main()
