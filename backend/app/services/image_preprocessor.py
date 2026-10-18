from dataclasses import asdict, dataclass


MIN_IMAGE_SIDE = 32
MIN_FOREGROUND_COVERAGE = 0.03
MAX_FOREGROUND_COVERAGE = 0.92


@dataclass(frozen=True)
class ImageQuality:
    width: int
    height: int
    brightness: float
    sharpness: float
    foreground_cropped: bool
    warnings: list[str]

    def to_dict(self):
        return asdict(self)


def preprocess_upload(uploaded_file):
    """Decode, validate, enhance, and conservatively crop an uploaded image."""
    import numpy as np
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

    image = ImageOps.exif_transpose(Image.open(uploaded_file.stream)).convert("RGB")
    width, height = image.size
    if width < MIN_IMAGE_SIDE or height < MIN_IMAGE_SIDE:
        raise ValueError(
            f"{uploaded_file.filename} is too small. "
            f"Use an image at least {MIN_IMAGE_SIDE}x{MIN_IMAGE_SIDE} pixels."
        )

    grayscale = image.convert("L")
    brightness = float(ImageStat.Stat(grayscale).mean[0])
    edges = grayscale.filter(ImageFilter.FIND_EDGES)
    sharpness = float(ImageStat.Stat(edges).stddev[0])
    warnings = []
    if brightness < 45:
        warnings.append("Image is dark; use brighter natural light.")
    elif brightness > 220:
        warnings.append("Image is overexposed; avoid direct glare.")
    if sharpness < 12:
        warnings.append("Image may be blurry; hold the camera steady and move closer.")

    cropped, was_cropped = _foreground_crop(image, np)
    enhanced = ImageOps.autocontrast(cropped, cutoff=1)
    enhanced = ImageEnhance.Contrast(enhanced).enhance(1.05)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.08)

    quality = ImageQuality(
        width=width,
        height=height,
        brightness=round(brightness, 1),
        sharpness=round(sharpness, 1),
        foreground_cropped=was_cropped,
        warnings=warnings,
    )
    return enhanced, quality


def _foreground_crop(image, np):
    """Crop plain borders only when a stable foreground can be identified."""
    sample = image.copy()
    sample.thumbnail((320, 320))
    pixels = np.asarray(sample, dtype=np.float32)
    height, width, _ = pixels.shape
    border = np.concatenate(
        (pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1]), axis=0
    )
    background = np.median(border, axis=0)
    border_spread = float(np.mean(np.std(border, axis=0)))
    if border_spread > 38:
        return image, False

    distance = np.linalg.norm(pixels - background, axis=2)
    mask = distance > max(28.0, border_spread * 2.2)
    coverage = float(mask.mean())
    if not MIN_FOREGROUND_COVERAGE <= coverage <= MAX_FOREGROUND_COVERAGE:
        return image, False

    rows, columns = np.where(mask)
    if not len(rows):
        return image, False

    padding = max(4, int(min(width, height) * 0.06))
    left = max(0, int(columns.min()) - padding)
    top = max(0, int(rows.min()) - padding)
    right = min(width, int(columns.max()) + padding + 1)
    bottom = min(height, int(rows.max()) + padding + 1)

    scale_x = image.width / width
    scale_y = image.height / height
    box = (
        int(left * scale_x),
        int(top * scale_y),
        int(right * scale_x),
        int(bottom * scale_y),
    )
    cropped_area = (box[2] - box[0]) * (box[3] - box[1])
    if cropped_area > image.width * image.height * 0.9:
        return image, False
    return image.crop(box), True
