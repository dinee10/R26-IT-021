import os
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class ImageValidationConfig:
    min_width: int
    min_height: int
    blur_threshold: float
    min_brightness: float
    max_brightness: float

    @classmethod
    def from_environment(cls) -> "ImageValidationConfig":
        return cls(
            min_width=int(os.getenv("QUALITY_MIN_WIDTH", "640")),
            min_height=int(os.getenv("QUALITY_MIN_HEIGHT", "480")),
            blur_threshold=float(os.getenv("QUALITY_BLUR_THRESHOLD", "100")),
            min_brightness=float(os.getenv("QUALITY_MIN_BRIGHTNESS", "35")),
            max_brightness=float(os.getenv("QUALITY_MAX_BRIGHTNESS", "220")),
        )


def validate_image_bytes(
    image_bytes: bytes,
    config: ImageValidationConfig | None = None,
) -> dict:
    config = config or ImageValidationConfig.from_environment()

    if not image_bytes:
        return {"valid": False, "reason": "INVALID_IMAGE"}

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        return {"valid": False, "reason": "INVALID_IMAGE"}

    height, width = image.shape[:2]
    if width < config.min_width or height < config.min_height:
        return {
            "valid": False,
            "reason": "LOW_RESOLUTION",
            "resolution": {"width": width, "height": height},
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())

    if blur_score < config.blur_threshold:
        return {
            "valid": False,
            "reason": "IMAGE_TOO_BLURRY",
            "resolution": {"width": width, "height": height},
            "blur_score": round(blur_score, 2),
            "brightness": round(brightness, 2),
        }

    if brightness < config.min_brightness:
        return {
            "valid": False,
            "reason": "IMAGE_TOO_DARK",
            "resolution": {"width": width, "height": height},
            "blur_score": round(blur_score, 2),
            "brightness": round(brightness, 2),
        }

    if brightness > config.max_brightness:
        return {
            "valid": False,
            "reason": "IMAGE_OVEREXPOSED",
            "resolution": {"width": width, "height": height},
            "blur_score": round(blur_score, 2),
            "brightness": round(brightness, 2),
        }

    return {
        "valid": True,
        "resolution": {"width": width, "height": height},
        "blur_score": round(blur_score, 2),
        "brightness": round(brightness, 2),
        "warnings": [],
    }
