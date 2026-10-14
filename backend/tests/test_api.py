import io
import unittest
from unittest.mock import patch

from PIL import Image

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
        self.assertIsInstance(body["organ_detector"]["ready"], bool)

    @patch("app.routes.api.detect_organs")
    def test_detect_organs_returns_normalized_boxes(self, detect_organs):
        expected = {
            "width": 640,
            "height": 480,
            "detections": [{"label": "leaf", "confidence_percent": 91.0}],
        }
        detect_organs.return_value = expected
        response = self.client.post(
            "/api/detect-organs",
            data={"image": (io.BytesIO(b"image bytes"), "frame.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), expected)

    @patch("app.routes.api.predict_herb")
    @patch("app.routes.api.detect_organs")
    def test_live_identification_routes_seed_crop_to_seed_model(
        self, detect_organs, predict_herb
    ):
        detect_organs.return_value = {
            "width": 100,
            "height": 100,
            "detections": [{
                "label": "seed",
                "confidence": 0.9,
                "confidence_percent": 90,
                "box": {"left": 0.1, "top": 0.1, "right": 0.9, "bottom": 0.9},
            }],
        }
        predict_herb.return_value = {
            "plant": "Turmeric",
            "confidence_percent": 88,
            "warning": None,
            "benefits": {},
        }
        image_bytes = io.BytesIO()
        Image.new("RGB", (100, 100), "green").save(image_bytes, "JPEG")
        image_bytes.seek(0)

        response = self.client.post(
            "/api/identify-live",
            data={"image": (image_bytes, "frame.jpg")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["identification"]["plant"], "Turmeric")
        self.assertEqual(predict_herb.call_args.kwargs["model_type"], "seed")

    def test_predict_requires_an_image(self):
        response = self.client.post("/api/predict")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Upload 1 to 5 images", response.get_json()["error"])

    def test_health_assessment_returns_explainable_metrics(self):
        image = Image.new("RGB", (120, 120), (20, 150, 20))
        for x in range(0, 120, 12):
            for y in range(0, 120, 12):
                if (x + y) // 12 % 2 == 0:
                    image.paste((0, 210, 0), (x, y, x + 12, y + 12))
        image_bytes = io.BytesIO()
        image.save(image_bytes, "JPEG")
        image_bytes.seek(0)

        response = self.client.post(
            "/api/assess-health",
            data={"image": (image_bytes, "leaf.jpg")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "healthy_looking")
        self.assertGreater(body["metrics"]["green_percent"], 80)
        self.assertIn("not a disease diagnosis", body["disclaimer"])

    @patch("app.routes.api.predict_herb")
    def test_predict_does_not_trust_browser_media_type(self, predict_herb):
        predict_herb.side_effect = ValueError("leaf.txt is not a valid image.")
        response = self.client.post(
            "/api/predict",
            data={"images": (io.BytesIO(b"not an image"), "leaf.txt")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("not a valid image", response.get_json()["error"])
        predict_herb.assert_called_once()

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

    @patch("app.routes.api.detect_organs")
    def test_predict_rejects_confident_wrong_category(self, detect_organs):
        detect_organs.return_value = {
            "detections": [{
                "label": "flower",
                "confidence": 0.92,
                "confidence_percent": 92,
            }]
        }
        response = self.client.post(
            "/api/predict",
            data={
                "model_type": "seed",
                "validate_category": "true",
                "images": (io.BytesIO(b"image bytes"), "flower.jpg"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error_code"], "category_mismatch")
        self.assertEqual(body["suggested_category"], "flower")
        self.assertIn("Please select 'Flower'", body["error"])

    @patch("app.routes.api.predict_herb")
    def test_predict_accepts_jfif_with_generic_browser_mime_type(self, predict_herb):
        predict_herb.return_value = {"plant": "Aloe"}

        response = self.client.post(
            "/api/predict",
            data={
                "images": (
                    io.BytesIO(b"image bytes"),
                    "scaled_download.jfif",
                    "application/octet-stream",
                )
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"plant": "Aloe"})

    def test_unknown_api_route_returns_json(self):
        response = self.client.get("/api/does-not-exist")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "Endpoint not found."})

    @patch("app.routes.api.quality_disease_incidence.assess_samples")
    def test_disease_incidence_endpoint_preserves_initial_and_sample_count(self, assess_samples):
        assess_samples.return_value = {
            "assessment_status": "completed",
            "accepted": True,
            "total_submitted_images": 3,
            "total_accepted_images": 2,
            "excluded_images": [{"sample_index": 2, "exclusion_reason": "IMAGE_TOO_BLURRY"}],
            "individual_leaf_predictions": [],
            "healthy_sample_count": 1,
            "per_condition_results": [],
        }
        response = self.client.post(
            "/api/quality/assess-disease-incidence",
            data={
                "initial_image": (io.BytesIO(b"initial"), "initial.jpg"),
                "sample_images": [
                    (io.BytesIO(b"second"), "second.jpg"),
                    (io.BytesIO(b"third"), "third.jpg"),
                ],
                "regions": '["Upper", "Middle", "Lower"]',
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        samples = assess_samples.call_args.kwargs["samples"]
        self.assertEqual([sample["bytes"] for sample in samples], [b"initial", b"second", b"third"])
        self.assertEqual([sample["region"] for sample in samples], ["Upper", "Middle", "Lower"])

    def test_disease_incidence_endpoint_rejects_more_than_25_images(self):
        response = self.client.post(
            "/api/quality/assess-disease-incidence",
            data={
                "image": [(io.BytesIO(str(index).encode()), f"{index}.jpg") for index in range(26)],
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["reason"], "TOO_MANY_IMAGES")


if __name__ == "__main__":
    unittest.main()
