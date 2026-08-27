import hashlib
import json
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np


DEFAULT_CONFIG_PATH = Path(__file__).with_name(
    "quality.plant_identification_config.json"
)
UNKNOWN_CLASS_ID = "unknown"
MODEL_RUNTIME_MISSING = "MODEL_RUNTIME_MISSING"
_MODEL_CACHE: dict[str, Any] = {}


def identify_plant_from_bytes(image_bytes: bytes) -> dict[str, Any]:
    config = _load_config()
    prediction = _predict_plant_image(image_bytes, config)
    return _format_prediction_result(prediction, config)


def identify_plant_from_multiple_images(image_bytes_list: list[bytes]) -> dict[str, Any]:
    config = _load_config()
    predictions = [
        _predict_plant_image(image_bytes, config)
        for image_bytes in image_bytes_list[:3]
    ]
    invalid_predictions = [
        prediction for prediction in predictions
        if prediction.get("reason") == "INVALID_IMAGE"
    ]

    if invalid_predictions:
        return {
            "accepted": False,
            "reason": "INVALID_IMAGE",
            "image_count": len(image_bytes_list),
        }

    runtime_missing = [
        prediction for prediction in predictions
        if prediction.get("reason") == MODEL_RUNTIME_MISSING
    ]

    if runtime_missing:
        return _format_prediction_result(runtime_missing[0], config)

    probability_predictions = [
        prediction for prediction in predictions
        if "probabilities" in prediction
    ]

    if not probability_predictions:
        return {"accepted": False, "reason": "INVALID_IMAGE"}

    averaged_probabilities = np.mean(
        [prediction["probabilities"] for prediction in probability_predictions],
        axis=0,
    )
    class_ids = _model_class_ids(config)
    class_index = int(np.argmax(averaged_probabilities))
    combined_prediction = {
        "class_id": class_ids[class_index],
        "confidence": float(averaged_probabilities[class_index]),
        "model": probability_predictions[0]["model"],
    }
    result = _format_prediction_result(combined_prediction, config)
    result["image_count"] = len(probability_predictions)
    result["aggregation"] = "AVERAGE_PROBABILITIES"
    result["per_image_predictions"] = [
        _format_prediction_result(prediction, config)
        for prediction in probability_predictions
    ]
    return result


def _predict_plant_image(image_bytes: bytes, config: dict[str, Any]) -> dict[str, Any]:
    image = _decode_image(image_bytes)

    if image is None:
        return {"reason": "INVALID_IMAGE"}

    preprocessed = preprocess_for_plant_model(
        image,
        width=int(config["input_size"]["width"]),
        height=int(config["input_size"]["height"]),
    )
    return _predict(preprocessed, image_bytes, config)


def _format_prediction_result(
    prediction: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    if prediction.get("reason") == MODEL_RUNTIME_MISSING:
        return {
            "species": "Unknown",
            "scientific_name": None,
            "confidence": 0,
            "accepted": False,
            "reason": MODEL_RUNTIME_MISSING,
            "model": prediction["model"],
            "input_size": config["input_size"],
            "preprocessing": "LETTERBOX_224",
        }

    if prediction.get("reason") == "INVALID_IMAGE":
        return {"accepted": False, "reason": "INVALID_IMAGE"}

    plant_class = _class_by_id(config, prediction["class_id"])
    confidence = round(float(prediction["confidence"]), 3)
    threshold = float(os.getenv(
        "QUALITY_SPECIES_CONFIDENCE_THRESHOLD",
        config["confidence_threshold"],
    ))

    result = {
        "species": plant_class["label"],
        "scientific_name": plant_class.get("scientific_name"),
        "confidence": confidence,
        "accepted": True,
        "model": prediction["model"],
        "input_size": config["input_size"],
        "preprocessing": "LETTERBOX_224",
    }

    if prediction["class_id"] == UNKNOWN_CLASS_ID:
        result["accepted"] = False
        result["reason"] = "UNKNOWN_PLANT"
    elif confidence < threshold:
        result["accepted"] = False
        result["reason"] = "LOW_SPECIES_CONFIDENCE"

    if prediction.get("mode") == "mock":
        result["mode"] = "mock"
        result["note"] = "Replace with a trained model before real predictions."

    return result


def preprocess_for_plant_model(
    image: np.ndarray,
    width: int = 224,
    height: int = 224,
) -> np.ndarray:
    letterboxed = _letterbox(image, width=width, height=height)
    rgb_image = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2RGB)
    model_input = rgb_image.astype(np.float32)
    return np.expand_dims(model_input, axis=0)


def _decode_image(image_bytes: bytes) -> np.ndarray | None:
    if not image_bytes:
        return None

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(image_array, cv2.IMREAD_COLOR)


def _letterbox(image: np.ndarray, width: int, height: int) -> np.ndarray:
    source_height, source_width = image.shape[:2]
    scale = min(width / source_width, height / source_height)
    resized_width = int(round(source_width * scale))
    resized_height = int(round(source_height * scale))

    resized = cv2.resize(
        image,
        (resized_width, resized_height),
        interpolation=cv2.INTER_AREA,
    )
    canvas = np.full((height, width, 3), 0, dtype=np.uint8)
    x_offset = (width - resized_width) // 2
    y_offset = (height - resized_height) // 2
    canvas[
        y_offset:y_offset + resized_height,
        x_offset:x_offset + resized_width,
    ] = resized
    return canvas


def _predict(
    preprocessed: np.ndarray,
    image_bytes: bytes,
    config: dict[str, Any],
) -> dict[str, Any]:
    model = _load_model(config)

    if model == MODEL_RUNTIME_MISSING:
        return {
            "class_id": UNKNOWN_CLASS_ID,
            "confidence": 0,
            "model": config["models"][config["active_model"]]["display_name"],
            "reason": MODEL_RUNTIME_MISSING,
        }

    if model is None:
        return _mock_prediction(image_bytes, config)

    probabilities = model.predict(preprocessed, verbose=0)[0]
    class_index = int(np.argmax(probabilities))
    class_ids = _model_class_ids(config)

    return {
        "class_id": class_ids[class_index],
        "confidence": float(probabilities[class_index]),
        "model": config["models"][config["active_model"]]["display_name"],
        "probabilities": probabilities,
    }


def _load_model(config: dict[str, Any]) -> Any:
    model_info = config["models"][config["active_model"]]
    model_path = Path(os.getenv("QUALITY_PLANT_MODEL_PATH", model_info["path"]))

    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parents[2] / model_path

    if not model_path.exists():
        return None

    cache_key = str(model_path)
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]

    try:
        from tensorflow import keras
    except ImportError:
        return MODEL_RUNTIME_MISSING

    model = keras.models.load_model(model_path)
    _MODEL_CACHE[cache_key] = model
    return model


def _mock_prediction(image_bytes: bytes, config: dict[str, Any]) -> dict[str, Any]:
    class_ids = _model_class_ids(config)
    digest = hashlib.sha256(image_bytes).digest()
    class_index = digest[0] % len(class_ids)
    confidence = 0.5 + (digest[1] / 255.0 * 0.45)

    if len(class_ids) == 1:
        probabilities = np.array([1.0])
        confidence = 1.0
    else:
        probabilities = np.full(
            len(class_ids),
            (1 - confidence) / (len(class_ids) - 1),
        )

    probabilities[class_index] = confidence

    return {
        "class_id": class_ids[class_index],
        "confidence": confidence,
        "model": config["models"][config["active_model"]]["display_name"],
        "mode": "mock",
        "probabilities": probabilities,
    }


def _load_config() -> dict[str, Any]:
    config_path = Path(os.getenv(
        "QUALITY_PLANT_CONFIG_PATH",
        DEFAULT_CONFIG_PATH,
    ))

    with config_path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def _class_by_id(config: dict[str, Any], class_id: str) -> dict[str, Any]:
    for plant_class in config["classes"]:
        if plant_class["id"] == class_id:
            return plant_class

    return {
        "id": class_id,
        "label": class_id.replace("_", " ").title(),
        "scientific_name": None,
    }


def _model_class_ids(config: dict[str, Any]) -> list[str]:
    model_info = config["models"][config["active_model"]]
    model_path = Path(os.getenv("QUALITY_PLANT_MODEL_PATH", model_info["path"]))

    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parents[2] / model_path

    labels_path = model_path.with_suffix(".labels.json")
    if labels_path.exists():
        with labels_path.open("r", encoding="utf-8") as labels_file:
            return json.load(labels_file)

    return [plant_class["id"] for plant_class in config["classes"]]
