from dataclasses import dataclass


@dataclass(frozen=True)
class VisualMetrics:
    green_percent: float
    yellow_percent: float
    brown_percent: float
    dark_percent: float
    brightness: float
    sharpness: float


def assess_plant_health(uploaded_file):
    if not uploaded_file or not uploaded_file.filename:
        raise ValueError("Upload one plant image using the form field name 'image'.")

    import numpy as np
    from PIL import Image, UnidentifiedImageError

    try:
        image = Image.open(uploaded_file.stream).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc

    image.thumbnail((900, 900), Image.Resampling.LANCZOS)
    rgb = np.asarray(image, dtype=np.float32)
    hsv = np.asarray(image.convert("HSV"), dtype=np.float32)
    hue, saturation, value = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    # Ignore low-saturation background pixels when calculating tissue colour.
    tissue = saturation >= 45
    tissue_count = max(int(tissue.sum()), 1)
    green = tissue & (hue >= 35) & (hue <= 105) & (value >= 45)
    yellow = tissue & (hue >= 20) & (hue < 35) & (value >= 65)
    brown = tissue & (hue >= 4) & (hue < 20) & (value >= 35) & (value < 190)
    dark = tissue & (value < 55)

    gray = rgb.mean(axis=2)
    edge_energy = (
        np.mean(np.abs(np.diff(gray, axis=0)))
        + np.mean(np.abs(np.diff(gray, axis=1)))
    ) / 2
    metrics = VisualMetrics(
        green_percent=round(float(green.sum()) / tissue_count * 100, 1),
        yellow_percent=round(float(yellow.sum()) / tissue_count * 100, 1),
        brown_percent=round(float(brown.sum()) / tissue_count * 100, 1),
        dark_percent=round(float(dark.sum()) / tissue_count * 100, 1),
        brightness=round(float(value.mean()) / 255 * 100, 1),
        sharpness=round(float(edge_energy), 1),
    )
    return _interpret(metrics, tissue_count / max(hue.size, 1))


def _interpret(metrics, tissue_fraction):
    capture_warnings = []
    if metrics.brightness < 20:
        capture_warnings.append("The image is too dark for a reliable assessment.")
    elif metrics.brightness > 92:
        capture_warnings.append("The image is overexposed; leaf colour may be inaccurate.")
    if metrics.sharpness < 2.5:
        capture_warnings.append("The image appears blurry. Hold the camera steady and move closer.")
    if tissue_fraction < 0.08:
        capture_warnings.append("Not enough coloured plant tissue was found in the frame.")

    symptoms = []
    recommendations = []
    if capture_warnings:
        status = "inconclusive"
        label = "Retake photo"
        confidence = 0.25
        recommendations.append("Retake the photo in bright, indirect daylight with one leaf filling the frame.")
    elif metrics.yellow_percent >= 22:
        status = "needs_review"
        label = "Possible yellowing"
        confidence = min(0.88, 0.58 + metrics.yellow_percent / 200)
        symptoms.append("A notable proportion of the visible tissue appears yellow.")
        recommendations.extend([
            "Check watering, drainage, and whether older or newer leaves are affected.",
            "Inspect both sides of the leaf for pests before applying any treatment.",
        ])
    elif metrics.brown_percent + metrics.dark_percent >= 20:
        status = "needs_review"
        label = "Possible tissue damage"
        confidence = min(0.88, 0.58 + (metrics.brown_percent + metrics.dark_percent) / 200)
        symptoms.append("Brown or unusually dark tissue is visible in the image.")
        recommendations.extend([
            "Isolate the affected plant if damage is spreading between plants.",
            "Ask an agricultural specialist to distinguish disease, scorch, and physical damage.",
        ])
    elif metrics.green_percent >= 55 and metrics.yellow_percent + metrics.brown_percent < 18:
        status = "healthy_looking"
        label = "Healthy-looking tissue"
        confidence = min(0.88, 0.62 + metrics.green_percent / 300)
        symptoms.append("Most detected plant tissue is green without strong discoloration signals.")
        recommendations.append("Continue monitoring; photograph again if spots, wilting, or discoloration appear.")
    else:
        status = "needs_review"
        label = "Possible plant stress"
        confidence = 0.58
        symptoms.append("The colour pattern is mixed and does not meet the healthy-looking threshold.")
        recommendations.append("Compare multiple leaves and request expert review if symptoms persist.")

    return {
        "status": status,
        "label": label,
        "confidence": round(confidence, 4),
        "confidence_percent": round(confidence * 100, 1),
        "symptoms": symptoms,
        "recommendations": recommendations,
        "capture_warnings": capture_warnings,
        "metrics": metrics.__dict__,
        "disclaimer": (
            "This is a visual screening result, not a disease diagnosis. Colour changes can be caused "
            "by lighting, age, nutrition, water, pests, disease, or physical damage."
        ),
    }
