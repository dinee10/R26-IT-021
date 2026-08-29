import hashlib
import json
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np


DEFAULT_CONFIG_PATH = Path(__file__).with_name("quality.condition_config.json")
MODEL_RUNTIME_MISSING = "MODEL_RUNTIME_MISSING"
HEALTHY_CLASS_ID = "healthy"
_MODEL_CACHE: dict[str, Any] = {}


def assess_condition_from_multiple_images(
    image_bytes_list: list[bytes],
    plant_result: dict[str, Any],
    disease_lookup,
) -> dict[str, Any]:
    config = _load_config()
    species_id = _species_id_from_result(plant_result)
    plant_response = {
        "species": plant_result.get("species", "Unknown"),
        "scientific_name": plant_result.get("scientific_name"),
        "confidence": plant_result.get("confidence", 0),
        "accepted": plant_result.get("accepted", False),
    }

    if not plant_result.get("accepted"):
        return {
            "plant": plant_response,
            "condition": None,
            "disease_info": None,
            "accepted": False,
            "reason": plant_result.get("reason", "PLANT_NOT_ACCEPTED"),
        }

    if species_id not in config["heads"]:
        return {
            "plant": plant_response,
            "condition": None,
            "disease_info": None,
            "accepted": False,
            "reason": "UNSUPPORTED_CONDITION_HEAD",
        }

    predictions = [
        _predict_condition_image(image_bytes, species_id, config)
        for image_bytes in image_bytes_list[:3]
    ]

    if any(prediction.get("reason") == "INVALID_IMAGE" for prediction in predictions):
        return {
            "plant": plant_response,
            "condition": None,
            "disease_info": None,
            "accepted": False,
            "reason": "INVALID_IMAGE",
        }

    runtime_missing = [
        prediction for prediction in predictions
        if prediction.get("reason") == MODEL_RUNTIME_MISSING
    ]
    if runtime_missing:
        condition = _format_condition_result(runtime_missing[0], species_id, config)
    else:
        probability_predictions = [
            prediction for prediction in predictions
            if "probabilities" in prediction
        ]
        averaged_probabilities = np.mean(
            [prediction["probabilities"] for prediction in probability_predictions],
            axis=0,
        )
        class_index = int(np.argmax(averaged_probabilities))
        class_ids = _condition_class_ids(species_id, config)
        condition = _format_condition_result(
            {
                "class_id": class_ids[class_index],
                "confidence": float(averaged_probabilities[class_index]),
                "model": probability_predictions[0]["model"],
            },
            species_id,
            config,
        )
        condition["image_count"] = len(probability_predictions)
        condition["aggregation"] = "AVERAGE_PROBABILITIES"

    disease_info = None
    if condition.get("status") == "diseased":
        disease_info = disease_lookup.get_disease_info(
            plant_response["species"],
            condition["class"],
        )

    return {
        "plant": plant_response,
        "condition": condition,
        "disease_info": disease_info,
        "accepted": condition.get("accepted", False),
    }


def preprocess_for_condition_model(
    image: np.ndarray,
    width: int = 224,
    height: int = 224,
) -> np.ndarray:
    letterboxed = _letterbox(image, width=width, height=height)
    rgb_image = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2RGB)
    model_input = rgb_image.astype(np.float32)
    return np.expand_dims(model_input, axis=0)


def _predict_condition_image(
    image_bytes: bytes,
    species_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    image = _decode_image(image_bytes)

    if image is None:
        return {"reason": "INVALID_IMAGE"}

    preprocessed = preprocess_for_condition_model(
        image,
        width=int(config["input_size"]["width"]),
        height=int(config["input_size"]["height"]),
    )
    return _predict(preprocessed, image_bytes, species_id, config)


def _predict(
    preprocessed: np.ndarray,
    image_bytes: bytes,
    species_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    model = _load_model(config)

    if model == MODEL_RUNTIME_MISSING:
        return {
            "class_id": HEALTHY_CLASS_ID,
            "confidence": 0,
            "model": config["models"][config["active_model"]]["display_name"],
            "reason": MODEL_RUNTIME_MISSING,
        }

    if model is None:
        return _mock_prediction(image_bytes, species_id, config)

    raw_prediction = model.predict(preprocessed, verbose=0)
    probabilities = _select_species_probabilities(raw_prediction, species_id, config)
    class_index = int(np.argmax(probabilities))
    class_ids = _condition_class_ids(species_id, config)

    return {
        "class_id": class_ids[class_index],
        "confidence": float(probabilities[class_index]),
        "model": config["models"][config["active_model"]]["display_name"],
        "probabilities": probabilities,
    }


def _format_condition_result(
    prediction: dict[str, Any],
    species_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    if prediction.get("reason") == MODEL_RUNTIME_MISSING:
        return {
            "status": "unavailable",
            "class": None,
            "confidence": 0,
            "accepted": False,
            "reason": MODEL_RUNTIME_MISSING,
            "model": prediction["model"],
            "preprocessing": "LETTERBOX_224",
        }

    class_id = prediction["class_id"]
    confidence = round(float(prediction["confidence"]), 3)
    threshold = float(os.getenv(
        "QUALITY_CONDITION_CONFIDENCE_THRESHOLD",
        config["confidence_threshold"],
    ))
    status = "healthy" if _normalize_key(class_id) == HEALTHY_CLASS_ID else "diseased"
    result = {
        "status": status,
        "class": class_id,
        "display_name": _display_name(class_id),
        "confidence": confidence,
        "accepted": True,
        "model": prediction["model"],
        "head": species_id,
        "preprocessing": "LETTERBOX_224",
    }

    if confidence < threshold:
        result["accepted"] = False
        result["reason"] = "LOW_CONDITION_CONFIDENCE"

    if prediction.get("mode") == "mock":
        result["mode"] = "mock"
        result["note"] = "Replace with a trained condition model before real predictions."

    return result


def _select_species_probabilities(
    raw_prediction: Any,
    species_id: str,
    config: dict[str, Any],
) -> np.ndarray:
    head_names = list(config["heads"].keys())

    if isinstance(raw_prediction, dict):
        return np.asarray(raw_prediction[species_id][0], dtype=np.float32)

    if isinstance(raw_prediction, list):
        head_index = head_names.index(species_id)
        return np.asarray(raw_prediction[head_index][0], dtype=np.float32)

    return np.asarray(raw_prediction[0], dtype=np.float32)


def _load_model(config: dict[str, Any]) -> Any:
    model_info = config["models"][config["active_model"]]
    model_path = Path(os.getenv("QUALITY_CONDITION_MODEL_PATH", model_info["path"]))

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

    model = keras.models.load_model(model_path, compile=False)
    _MODEL_CACHE[cache_key] = model
    return model


def _mock_prediction(
    image_bytes: bytes,
    species_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    class_ids = _condition_class_ids(species_id, config)
    digest = hashlib.sha256(image_bytes + species_id.encode("utf-8")).digest()
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


def _condition_class_ids(species_id: str, config: dict[str, Any]) -> list[str]:
    labels_path = _labels_path(config)
    if labels_path.exists():
        with labels_path.open("r", encoding="utf-8") as labels_file:
            labels = json.load(labels_file)

        if isinstance(labels, dict) and species_id in labels:
            return labels[species_id]

    return config["heads"][species_id]


def _labels_path(config: dict[str, Any]) -> Path:
    model_info = config["models"][config["active_model"]]
    model_path = Path(os.getenv("QUALITY_CONDITION_MODEL_PATH", model_info["path"]))

    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parents[2] / model_path

    return model_path.with_suffix(".labels.json")


def _load_config() -> dict[str, Any]:
    config_path = Path(os.getenv("QUALITY_CONDITION_CONFIG_PATH", DEFAULT_CONFIG_PATH))

    with config_path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def _species_id_from_result(plant_result: dict[str, Any]) -> str:
    return _normalize_key(str(plant_result.get("species", "")))


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _display_name(value: str) -> str:
    return value.replace("_", " ").title()
