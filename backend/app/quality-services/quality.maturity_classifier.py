import hashlib
import json
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np


DEFAULT_CONFIG_PATH = Path(__file__).with_name("quality.maturity_config.json")
MODEL_RUNTIME_MISSING = "MODEL_RUNTIME_MISSING"
_MODEL_CACHE: dict[str, Any] = {}


def assess_maturity_from_multiple_images(
    image_bytes_list: list[bytes],
    plant_result: dict[str, Any],
    condition_result: dict[str, Any],
    maturity_lookup,
    maturity_decision,
    manual_support_service,
    manual_inputs: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    config = _load_config()
    species_id = _species_id_from_result(plant_result)
    condition = condition_result.get("condition") or {}

    if condition.get("status") != "healthy":
        return None

    head_config = config.get("heads", {}).get(species_id)
    if not head_config:
        return _unavailable_result("UNSUPPORTED_MATURITY_HEAD", config)

    if not head_config.get("enabled", True):
        return maturity_decision.not_assessed_result(species_id)

    predictions = [
        _predict_maturity_image(image_bytes, species_id, config)
        for image_bytes in image_bytes_list[:3]
    ]

    if any(prediction.get("reason") == "INVALID_IMAGE" for prediction in predictions):
        return _unavailable_result("INVALID_IMAGE", config)

    runtime_missing = [
        prediction for prediction in predictions
        if prediction.get("reason") == MODEL_RUNTIME_MISSING
    ]
    if runtime_missing:
        return _unavailable_result(MODEL_RUNTIME_MISSING, config)

    probability_predictions = [
        prediction for prediction in predictions
        if "probabilities" in prediction
    ]
    if not probability_predictions:
        return _unavailable_result("INVALID_IMAGE", config)

    class_ids = _maturity_class_ids(species_id, config)
    averaged_probabilities = np.mean(
        [prediction["probabilities"] for prediction in probability_predictions],
        axis=0,
    )
    probabilities = {
        class_id: float(averaged_probabilities[index])
        for index, class_id in enumerate(class_ids)
    }
    maturity = maturity_decision.resolve_maturity_prediction(
        species=species_id,
        model_probabilities=probabilities,
        maturity_lookup=maturity_lookup,
        manual_support_service=manual_support_service,
        manual_inputs=manual_inputs,
        config=config,
    )
    maturity["accepted"] = (
        maturity["final_decision"]["decision_status"]
        not in {
            "Insufficient_Evidence",
            "Expert_Verification_Recommended",
            "Manual_Evidence_Conflicts",
        }
    )
    maturity["model"] = probability_predictions[0]["model"]
    maturity["head"] = species_id
    maturity["image_count"] = len(probability_predictions)
    maturity["aggregation"] = "AVERAGE_PROBABILITIES"
    maturity["preprocessing"] = "LETTERBOX_224"

    if probability_predictions[0].get("mode") == "mock":
        maturity["mode"] = "mock"
        maturity["note"] = "Replace with a trained maturity model before real predictions."

    return maturity


def preprocess_for_maturity_model(
    image: np.ndarray,
    width: int = 224,
    height: int = 224,
) -> np.ndarray:
    letterboxed = _letterbox(image, width=width, height=height)
    rgb_image = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2RGB)
    model_input = rgb_image.astype(np.float32)
    return np.expand_dims(model_input, axis=0)


def _predict_maturity_image(
    image_bytes: bytes,
    species_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    image = _decode_image(image_bytes)

    if image is None:
        return {"reason": "INVALID_IMAGE"}

    preprocessed = preprocess_for_maturity_model(
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
            "reason": MODEL_RUNTIME_MISSING,
            "model": config["models"][config["active_model"]]["display_name"],
        }

    if model is None:
        return _mock_prediction(image_bytes, species_id, config)

    raw_prediction = model.predict(preprocessed, verbose=0)
    probabilities = _select_species_probabilities(raw_prediction, species_id, config)

    return {
        "model": config["models"][config["active_model"]]["display_name"],
        "probabilities": probabilities,
    }


def _load_model(config: dict[str, Any]) -> Any:
    model_info = config["models"][config["active_model"]]
    model_path = Path(os.getenv("QUALITY_MATURITY_MODEL_PATH", model_info["path"]))

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
    class_ids = _maturity_class_ids(species_id, config)
    digest = hashlib.sha256(image_bytes + species_id.encode("utf-8")).digest()
    class_index = digest[0] % len(class_ids)
    confidence = 0.5 + (digest[1] / 255.0 * 0.45)

    probabilities = np.full(
        len(class_ids),
        (1 - confidence) / max(len(class_ids) - 1, 1),
    )
    probabilities[class_index] = confidence

    return {
        "model": config["models"][config["active_model"]]["display_name"],
        "mode": "mock",
        "probabilities": probabilities,
    }


def _select_species_probabilities(
    raw_prediction: Any,
    species_id: str,
    config: dict[str, Any],
) -> np.ndarray:
    head_names = [
        species
        for species, head in config["heads"].items()
        if head.get("enabled", True)
    ]

    if isinstance(raw_prediction, dict):
        return np.asarray(raw_prediction[species_id][0], dtype=np.float32)

    if isinstance(raw_prediction, list):
        head_index = head_names.index(species_id)
        return np.asarray(raw_prediction[head_index][0], dtype=np.float32)

    return np.asarray(raw_prediction[0], dtype=np.float32)


def _maturity_class_ids(species_id: str, config: dict[str, Any]) -> list[str]:
    labels_path = _labels_path(config)
    if labels_path.exists():
        with labels_path.open("r", encoding="utf-8") as labels_file:
            labels = json.load(labels_file)

        if isinstance(labels, dict) and species_id in labels:
            return labels[species_id]

    return config["heads"][species_id]["classes"]


def _labels_path(config: dict[str, Any]) -> Path:
    model_info = config["models"][config["active_model"]]
    model_path = Path(os.getenv("QUALITY_MATURITY_MODEL_PATH", model_info["path"]))

    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parents[2] / model_path

    return model_path.with_suffix(".labels.json")


def _unavailable_result(reason: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "accepted": False,
        "reason": reason,
        "model_prediction": None,
        "manual_support": None,
        "final_decision": {
            "stage": None,
            "canonical_stage": None,
            "decision_status": "Expert_Verification_Recommended",
            "reason": "Maturity assessment is unavailable.",
        },
        "maturity_info": None,
        "medicinal_suitability": {
            "level": "Expert_Verification_Recommended",
            "display": "Expert verification recommended before medicinal use",
            "assessment": "Maturity could not be assessed visually.",
            "evidence_strength": "",
        },
        "model": config["models"][config["active_model"]]["display_name"],
        "preprocessing": "LETTERBOX_224",
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


def _species_id_from_result(plant_result: dict[str, Any]) -> str:
    return str(plant_result.get("species", "")).strip().lower().replace(" ", "_")


def _load_config() -> dict[str, Any]:
    config_path = Path(os.getenv("QUALITY_MATURITY_CONFIG_PATH", DEFAULT_CONFIG_PATH))

    with config_path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)
