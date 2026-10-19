import io
import unittest
from unittest.mock import patch

from app.main import app


class QualityUploadPipelineTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def _upload(self, image_bytes=b"one-upload"):
        response = self.client.post(
            "/api/quality/uploads",
            data={"image": (io.BytesIO(image_bytes), "leaf.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()["upload_id"]

    @patch("app.routes.api.quality_condition_classifier.assess_condition_from_multiple_images")
    @patch("app.routes.api.quality_plant_identifier.identify_plant_from_multiple_images")
    @patch("app.routes.api.quality_image_validator.validate_image_bytes")
    def test_one_upload_is_reused_and_deleted_after_assessment(
        self,
        validate_image,
        identify_plant,
        assess_condition,
    ):
        validate_image.return_value = {
            "valid": True,
            "resolution": {"width": 800, "height": 600},
            "blur_score": 50.0,
            "brightness": 120.0,
        }
        identify_plant.return_value = {
            "accepted": True,
            "species": "Betel",
            "confidence": 0.95,
        }
        assess_condition.return_value = {
            "accepted": True,
            "condition": {"status": "healthy"},
        }

        upload_id = self._upload()
        self.assertEqual(
            self.client.post(f"/api/quality/uploads/{upload_id}/validate").status_code,
            200,
        )
        self.assertEqual(
            self.client.post(f"/api/quality/uploads/{upload_id}/identify").status_code,
            200,
        )
        self.assertEqual(
            self.client.post(f"/api/quality/uploads/{upload_id}/assess").status_code,
            200,
        )

        identify_plant.assert_called_once()
        self.assertEqual(
            assess_condition.call_args.kwargs["image_bytes_list"],
            (b"one-upload",),
        )
        self.assertEqual(
            self.client.post(f"/api/quality/uploads/{upload_id}/validate").status_code,
            404,
        )

    @patch("app.routes.api.quality_image_validator.validate_image_bytes")
    def test_invalid_upload_is_deleted_after_validation(self, validate_image):
        validate_image.return_value = {
            "valid": False,
            "reason": "IMAGE_TOO_BLURRY",
        }
        upload_id = self._upload()

        response = self.client.post(
            f"/api/quality/uploads/{upload_id}/validate"
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["reason"], "IMAGE_TOO_BLURRY")
        self.assertEqual(
            self.client.post(f"/api/quality/uploads/{upload_id}/identify").status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
