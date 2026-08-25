import io
import unittest
from unittest.mock import patch

from app.main import app


class ApiContractTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_health_reports_backend_and_model_state(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn(body["status"], {"healthy", "degraded"})
        self.assertIsInstance(body["model"]["ready"], bool)
        self.assertIn("missing_artifacts", body["model"])

    def test_predict_requires_an_image(self):
        response = self.client.post("/api/predict")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Upload 1 to 5 images", response.get_json()["error"])

    def test_predict_rejects_unsupported_media_type(self):
        response = self.client.post(
            "/api/predict",
            data={"images": (io.BytesIO(b"not an image"), "leaf.txt")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 415)
        self.assertIn("JPEG, PNG, or WebP", response.get_json()["error"])

    @patch("app.routes.api.predict_herb")
    def test_predict_returns_service_result(self, predict_herb):
        expected = {"plant": "Neem", "confidence_percent": 98.2}
        predict_herb.return_value = expected

        response = self.client.post(
            "/api/predict",
            data={"images": (io.BytesIO(b"image bytes"), "leaf.jpg")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), expected)
        predict_herb.assert_called_once()

    def test_unknown_api_route_returns_json(self):
        response = self.client.get("/api/does-not-exist")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "Endpoint not found."})


if __name__ == "__main__":
    unittest.main()
