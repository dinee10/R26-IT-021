import json
from pathlib import Path

from app.services.image_preprocessor import preprocess_upload

try:
    import tensorflow as tf
except ImportError:  # Allows the Flask app to start before ML deps are installed.
    tf = None


BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_ARTIFACTS = {
    "plant": (
        BACKEND_DIR / "ml" / "exports" / "herb_model.keras",
        BACKEND_DIR / "ml" / "exports" / "labels.json",
    ),
    "seed": (
        BACKEND_DIR / "ml" / "exports" / "seed" / "herb_model.keras",
        BACKEND_DIR / "ml" / "exports" / "seed" / "labels.json",
    ),
}
BENEFITS_PATH = BACKEND_DIR / "ml" / "metadata" / "benefits.json"
IMAGE_SIZE = (224, 224)
CONFIDENCE_WARNING = 0.95
CROP_SCALES = (1.0, 0.95, 0.9, 0.8)

_models = {}
_labels_by_type = {}
_benefits = None


class ModelNotReadyError(RuntimeError):
    pass


def model_status():
    """Report artifact availability without loading the large ML model."""
    missing = {
        model_type: [str(path.relative_to(BACKEND_DIR)) for path in paths if not path.exists()]
        for model_type, paths in MODEL_ARTIFACTS.items()
    }
    all_ready = all(not paths for paths in missing.values())
    return {
        "ready": tf is not None and all_ready,
        "tensorflow_installed": tf is not None,
        "missing_artifacts": [path for paths in missing.values() for path in paths],
        "models": {
            model_type: {"ready": tf is not None and not paths, "missing_artifacts": paths}
            for model_type, paths in missing.items()
        },
    }


def _load_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_model(model_type="plant"):
    global _benefits

    if tf is None:
        raise ModelNotReadyError(
            "TensorFlow is not installed. Install backend/ml/requirements.txt and train the model first."
        )

    try:
        import numpy as np
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise ModelNotReadyError(
            "ML image dependencies are not installed. Use Python 3.11 and install backend/ml/requirements.txt."
        ) from exc

    if model_type not in MODEL_ARTIFACTS:
        raise ValueError("model_type must be 'plant' or 'seed'.")
    model_path, labels_path = MODEL_ARTIFACTS[model_type]

    if not model_path.exists() or not labels_path.exists():
        raise ModelNotReadyError(
            f"The {model_type} model is not ready. Train it and export matching model and labels files."
        )

    if model_type not in _models:
        model = tf.keras.models.load_model(model_path)
        labels = _load_json(labels_path, [])
        _benefits = _load_json(BENEFITS_PATH, {})

        output_size = int(model.output_shape[-1])
        if not labels or len(labels) != output_size:
            raise ModelNotReadyError(
                f"Model output has {output_size} classes but labels.json has "
                f"{len(labels)} labels. Retrain or export matching artifacts."
            )
        _models[model_type] = model
        _labels_by_type[model_type] = labels

    return _models[model_type], _labels_by_type[model_type], _benefits


def _image_to_arrays(uploaded_file):
    import numpy as np
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        image, quality = preprocess_upload(uploaded_file)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"{uploaded_file.filename} is not a valid image.") from exc

    arrays = []
    for scale in CROP_SCALES:
        crop = _center_crop(image, scale)
        crop = crop.resize(IMAGE_SIZE, Image.Resampling.LANCZOS)
        arrays.append(np.asarray(crop, dtype=np.float32))
        arrays.append(np.asarray(ImageOps.mirror(crop), dtype=np.float32))

    return np.stack(arrays, axis=0), quality


def _center_crop(image, scale):
    if scale >= 1:
        return image

    width, height = image.size
    crop_width = int(width * scale)
    crop_height = int(height * scale)
    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    return image.crop((left, top, left + crop_width, top + crop_height))


def predict_herb(uploaded_files, model_type="plant"):
    import numpy as np

    model, labels, benefits = _load_model(model_type)

    predictions = []
    image_quality = []
    for uploaded_file in uploaded_files:
        if not uploaded_file.filename:
            raise ValueError("One uploaded image has no filename.")
        image_arrays, quality = _image_to_arrays(uploaded_file)
        image_predictions = model.predict(image_arrays, verbose=0)
        predictions.append(np.mean(image_predictions, axis=0))
        image_quality.append({"filename": uploaded_file.filename, **quality.to_dict()})

    mean_prediction = np.mean(predictions, axis=0)
    top_indexes = mean_prediction.argsort()[-5:][::-1]
    best_index = int(top_indexes[0])
    best_label = labels[best_index]
    confidence = float(mean_prediction[best_index])

    return {
        "plant": best_label,
        "model_type": model_type,
        "confidence": round(confidence, 4),
        "confidence_percent": round(confidence * 100, 2),
        "warning": None
        if confidence >= CONFIDENCE_WARNING
        else "The model is not 95% confident yet. Add 3 to 5 clearer leaf/seed photos from different angles before trusting this result.",
        "benefits": _benefits_for_label(benefits, best_label),
        "image_quality": image_quality,
        "top_predictions": [
            {
                "plant": labels[int(index)],
                "confidence": round(float(mean_prediction[int(index)]), 4),
                "confidence_percent": round(float(mean_prediction[int(index)]) * 100, 2),
            }
            for index in top_indexes
        ],
    }


def _benefits_for_label(benefits, label):
    if label in benefits:
        return benefits[label]

    normalized_label = _normalize_label(label)
    for key, value in benefits.items():
        if _normalize_label(key) == normalized_label:
            return value

    label_without_common_name = label.split("(")[0].strip()
    normalized_without_common_name = _normalize_label(label_without_common_name)
    for key, value in benefits.items():
        if _normalize_label(key) == normalized_without_common_name:
            return value

    return _fallback_benefits(label)


def _normalize_label(label):
    return "".join(character.lower() for character in label if character.isalnum())


def _fallback_benefits(label):
    pretty_name = label.replace("_", " ").title()
    return {
        "common_name": pretty_name,
        "scientific_name": pretty_name,
        "traditional_uses": [
            "Traditional use information has not been added yet for this plant.",
            "Add verified traditional uses in backend/ml/metadata/benefits.json.",
        ],
        "preparation_notes": [
            "Preparation notes have not been added yet.",
            "Do not prepare or consume this plant without expert guidance.",
        ],
        "safety_warning": "Do not consume or apply herbal remedies without advice from a qualified professional.",
        "medical_disclaimer": "This app is for educational plant identification only and is not medical advice.",
    }
