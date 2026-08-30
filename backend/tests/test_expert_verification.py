import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app.main import app
from app.services import expert_verification


def _jpeg_with_metadata():
    output = io.BytesIO()
    image = Image.new("RGB", (32, 32), "green")
    exif = Image.Exif()
    exif[0x010E] = "private location note"
    image.save(output, "JPEG", exif=exif)
    output.seek(0)
    return output


class ExpertVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.path_patch = patch.multiple(
            expert_verification,
            DATA_DIR=self.data_dir,
            DATABASE_PATH=self.data_dir / "verifications.sqlite3",
        )
        self.path_patch.start()
        self.key_patch = patch.dict("os.environ", {"EXPERT_REVIEW_KEY": "test-key"})
        self.key_patch.start()
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        self.key_patch.stop()
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def _submit(self, consent="false"):
        return self.client.post(
            "/api/verifications",
            data={
                "images": (_jpeg_with_metadata(), "leaf.jpg"),
                "ai_identification": "Neem",
                "ai_confidence": "62.5",
                "training_consent": consent,
            },
            content_type="multipart/form-data",
        )

    def test_submission_strips_metadata_and_stores_ai_label(self):
        response = self._submit("true")
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["identification_label"], "AI identified")
        self.assertTrue(body["training_consent"])

        saved = self.data_dir / body["id"] / "image_1.jpg"
        with Image.open(saved) as image:
            self.assertEqual(len(image.getexif()), 0)

    def test_expert_review_changes_to_expert_verified_label(self):
        request_id = self._submit().get_json()["id"]
        response = self.client.post(
            f"/api/expert/verifications/{request_id}",
            headers={"X-Expert-Key": "test-key"},
            json={
                "identification": "Azadirachta indica",
                "notes": "Leaf margins and venation confirmed.",
                "reviewer_name": "Dr. Perera",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["identification_label"], "Expert verified")
        self.assertEqual(body["expert_identification"], "Azadirachta indica")

        public_status = self.client.get(f"/api/verifications/{request_id}")
        self.assertEqual(public_status.get_json()["status"], "verified")

    def test_expert_queue_requires_key(self):
        response = self.client.get("/api/expert/verifications")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
