import io
import unittest

from PIL import Image, ImageDraw
from werkzeug.datastructures import FileStorage

from app.services.image_preprocessor import preprocess_upload


def uploaded_image(image, filename="plant.png"):
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    stream.seek(0)
    return FileStorage(stream=stream, filename=filename, content_type="image/png")


class ImagePreprocessorTests(unittest.TestCase):
    def test_plain_background_is_cropped_around_foreground(self):
        image = Image.new("RGB", (400, 300), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((130, 70, 270, 230), fill=(30, 130, 45))

        processed, quality = preprocess_upload(uploaded_image(image))

        self.assertTrue(quality.foreground_cropped)
        self.assertLess(processed.width, image.width)
        self.assertLess(processed.height, image.height)

    def test_dark_image_returns_lighting_guidance(self):
        image = Image.new("RGB", (224, 224), (20, 20, 20))

        _processed, quality = preprocess_upload(uploaded_image(image))

        self.assertTrue(any("dark" in warning for warning in quality.warnings))

    def test_tiny_image_is_rejected(self):
        image = Image.new("RGB", (20, 20), "green")

        with self.assertRaisesRegex(ValueError, "at least 32x32"):
            preprocess_upload(uploaded_image(image))


if __name__ == "__main__":
    unittest.main()
