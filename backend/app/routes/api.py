import csv
import os
from io import BytesIO
import importlib.util
import json
import sys
import sys
from math import isfinite
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.datastructures import FileStorage

from app.services.predictor import (
    ModelNotReadyError,
    model_status,
    predict_herb,
    preload_model as preload_prediction_model,
)
from app.services.organ_detector import (
    OrganDetectorNotReadyError,
    detect_organs,
    detector_status,
    preload_model as preload_organ_model,
)
from app.services.health_assessor import assess_plant_health
from app.services.expert_verification import (
    create_request,
    get_request,
    image_path,
    list_pending_requests,
    verify_request,
)
from app.services.quality_upload_store import (
    create_upload,
    discard_upload,
    get_plant_result,
    get_upload,
    set_plant_result,
)
bp = Blueprint('api', __name__)
from flask import Blueprint, jsonify, request

from crs_soil.crs_soil_predict import register_soil_routes

if __package__ in (None, ''):
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from cultivation.train_recommendation import predict_top_plants

bp = Blueprint('api', __name__, url_prefix='/api')
register_soil_routes(bp)
DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'medicinal_plant_cultivation.csv'


def _load_plants():
    """Load the source cultivation dataset used for enriched plant detail responses."""
    with DATA_FILE.open(encoding='utf-8-sig', newline='') as dataset:
        plants = list(csv.DictReader(dataset))
    if not plants:
        raise ValueError('The cultivation dataset is empty.')
    return plants


def _plant_details(plant):
    return {
        'soilRequirement': plant.get('soil_requirement'),
        'wateringRequirement': plant.get('watering_requirement'),
        'plantingMethod': plant.get('planting_method'),
        'fertilizerCare': plant.get('fertilizer_care'),
        'growingPeriod': plant.get('growing_period'),
        'sellingPrice': plant.get('selling_price_lkr'),
        'harvestingInformation': plant.get('harvesting_information'),
    }


def _plant_lookup():
    return {plant['plant_name']: plant for plant in _load_plants()}


_quality_services_path = Path(__file__).resolve().parents[1] / "quality-services"


def _load_quality_service(module_name, file_name):
    service_path = _quality_services_path / file_name
    service_spec = importlib.util.spec_from_file_location(module_name, service_path)
    service = importlib.util.module_from_spec(service_spec)
    assert service_spec.loader is not None
    sys.modules[service_spec.name] = service
    service_spec.loader.exec_module(service)
    return service


quality_image_validator = _load_quality_service(
    "quality_image_validator",
    "quality.image_validator.py",
)
quality_plant_identifier = _load_quality_service(
    "quality_plant_identifier",
    "quality.plant_identifier.py",
)
quality_condition_classifier = _load_quality_service(
    "quality_condition_classifier",
    "quality.condition_classifier.py",
)
quality_disease_lookup = _load_quality_service(
    "quality_disease_lookup",
    "quality.disease_lookup.py",
)
quality_disease_incidence = _load_quality_service(
    "quality_disease_incidence",
    "quality.disease_incidence.py",
)
quality_maturity_lookup = _load_quality_service(
    "quality_maturity_lookup",
    "quality.maturity_lookup.py",
)
quality_manual_maturity_support = _load_quality_service(
    "quality_manual_maturity_support",
    "quality.manual_maturity_support.py",
)
quality_maturity_decision = _load_quality_service(
    "quality_maturity_decision",
    "quality.maturity_decision.py",
)
quality_maturity_classifier = _load_quality_service(
    "quality_maturity_classifier",
    "quality.maturity_classifier.py",
)
quality_gradcam = _load_quality_service(
    "quality_gradcam",
    "quality.gradcam.py",
)
_model_preload_results = {}


def preload_backend_models(include_all=False):
    """Warm inference models once and keep them cached for Waitress threads."""
    loaders = {
        "quality_plant": quality_plant_identifier.preload_model,
        "quality_condition": quality_condition_classifier.preload_model,
        "quality_maturity": quality_maturity_classifier.preload_model,
    }
    if include_all:
        loaders.update({
            "prediction_plant": lambda: preload_prediction_model("plant"),
            "prediction_seed": lambda: preload_prediction_model("seed"),
            "prediction_flower": lambda: preload_prediction_model("flower"),
            "organ_detector": preload_organ_model,
        })
    global _model_preload_results
    results = {}
    for name, loader in loaders.items():
        try:
            results[name] = "loaded" if loader() else "unavailable"
        except Exception as exc:  # Keep other endpoints available if one model fails.
            results[name] = f"failed: {exc}"
    _model_preload_results = {
        name: {
            "loaded": result == "loaded",
            "status": result.split(":", 1)[0],
        }
        for name, result in results.items()
    }
    return results


@bp.route('/health', methods=['GET'])
def health():
    status = model_status()
    quality_ready = (
        all(item["loaded"] for item in _model_preload_results.values())
        if _model_preload_results
        else None
    )
    return jsonify({
        "status": "healthy"
        if status["ready"] and quality_ready is not False
        else "degraded",
        "message": "Backend is working",
        "model": status,
        "quality_models": {
            "ready": quality_ready,
            "models": _model_preload_results,
        },
        "organ_detector": detector_status(),
    })


@bp.route('/detect-organs', methods=['POST'])
def detect_plant_organs():
    try:
        result = detect_organs(
            request.files.get('image'),
            confidence=float(request.form.get('confidence', 0.35)),
        )
    except OrganDetectorNotReadyError as exc:
        return jsonify({"error": str(exc)}), 503
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.route('/identify-live', methods=['POST'])
def identify_live():
    upload = request.files.get('image')
    if not upload or not upload.filename:
        return jsonify({"error": "Upload one camera frame using the form field name 'image'."}), 400
    raw_image = upload.read()
    try:
        detection_upload = FileStorage(
            stream=BytesIO(raw_image), filename=upload.filename, content_type=upload.content_type
        )
        detection_result = detect_organs(
            detection_upload,
            confidence=float(request.form.get('confidence', 0.35)),
        )
        detections = detection_result["detections"]
        if not detections:
            return jsonify({**detection_result, "identification": None})

        best = max(detections, key=lambda item: item["confidence"])
        from PIL import Image

        image = Image.open(BytesIO(raw_image)).convert("RGB")
        width, height = image.size
        box = best["box"]
        crop = image.crop((
            max(0, int(box["left"] * width)),
            max(0, int(box["top"] * height)),
            min(width, int(box["right"] * width)),
            min(height, int(box["bottom"] * height)),
        ))
        crop_bytes = BytesIO()
        crop.save(crop_bytes, format="JPEG", quality=92)
        crop_bytes.seek(0)
        model_type = "plant" if best["label"] == "leaf" else best["label"]
        classification = predict_herb(
            [FileStorage(stream=crop_bytes, filename=f"{best['label']}_crop.jpg")],
            model_type=model_type,
        )
        return jsonify({
            **detection_result,
            "identification": {
                "organ": best["label"],
                "organ_confidence_percent": best["confidence_percent"],
                "plant": classification["plant"],
                "confidence_percent": classification["confidence_percent"],
                "warning": classification["warning"],
                "benefits": classification["benefits"],
            },
        })
    except (OrganDetectorNotReadyError, ModelNotReadyError) as exc:
        return jsonify({"error": str(exc)}), 503
    except (OSError, TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route('/assess-health', methods=['POST'])
def assess_health():
    try:
        return jsonify(assess_plant_health(request.files.get('image')))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

@bp.route('/ask', methods=['POST'])
def ask():
    data = request.get_json(silent=True) or {}
    query = str(data.get('query', '')).strip()
    session_id = str(data.get('session_id', 'default')).strip() or 'default'
    user_context = data.get('user_context', {})

    if not query:
        return jsonify({'error': 'Query is required.'}), 400
    if not isinstance(user_context, dict):
        return jsonify({'error': 'user_context must be an object.'}), 400
        
    # Receive recent conversation history from Flutter.
    # This may include messages restored from Firestore.
    raw_history = data.get('history', [])

    if not isinstance(raw_history, list):
        return jsonify({'error': 'history must be a list.'}), 400

    recent_history = []

    for message in raw_history[-6:]:
        if not isinstance(message, dict):
            return jsonify({'error': 'Invalid history message.'}), 400

        role = message.get('role')
        content = message.get('content')

        if (
            role not in ('user', 'assistant')
            or not isinstance(content, str)
            or not content.strip()
            or len(content) > 10000
        ):
            return jsonify({'error': 'Invalid history content.'}), 400

        recent_history.append({
            'role': role,
            'content': content.strip()
        })

    # Make validated history available to the bilingual RAG.
    user_context['recent_history'] = recent_history

    try:
        from conversation_rag_bilingual_test import ask_question
        return jsonify(ask_question(query, session_id, user_context))
    except (ImportError, ModuleNotFoundError) as exc:
        return jsonify({'error': f'RAG dependencies are not installed: {exc}'}), 503
    except Exception as exc:
        return jsonify({'error': f'The knowledge assistant is unavailable: {exc}'}), 503

@bp.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json(silent=True) or {}
    required = (
        'temperature',
        'rainfall',
        'humidity',
        'growingSpace',
        'budgetAmount',
        'budgetCurrency',
        'irrigationMethod',
        'growingSeason',
        'growingDuration',
    )
    missing = [field for field in required if data.get(field) in (None, '')]
    if missing:
        return jsonify({'error': 'Missing required fields', 'fields': missing}), 400

    try:
        temperature = float(data['temperature'])
        rainfall = float(data['rainfall'])
        humidity = float(data['humidity'])
        budget = float(data['budgetAmount'])
        soil_ph = data.get('soilPh')
        soil_ph = None if soil_ph in (None, '') else float(soil_ph)
    except (TypeError, ValueError):
        return jsonify({'error': 'Weather, budget, and soil pH values must be numeric'}), 400

    if not all(isfinite(value) for value in (temperature, rainfall, humidity, budget)) or budget < 0:
        return jsonify({'error': 'Weather and budget values must be valid and non-negative'}), 400
    if soil_ph is not None and (not isfinite(soil_ph) or not 0 <= soil_ph <= 14):
        return jsonify({'error': 'Soil pH must be between 0 and 14'}), 400

    data_with_defaults = dict(data)
    data_with_defaults.setdefault('soilType', 'Unknown')
    data_with_defaults.setdefault('soilPh', 6.5)
    data_with_defaults['temperature'] = temperature
    data_with_defaults['rainfall'] = rainfall
    data_with_defaults['humidity'] = humidity
    data_with_defaults['soilPh'] = soil_ph if soil_ph is not None else 6.5

    try:
        model_predictions = predict_top_plants(data_with_defaults)
    except Exception as exc:  # pragma: no cover - runtime guard for missing training assets
        return jsonify({'error': f'Could not load the trained recommendation model: {exc}'}), 500

    plant_catalog = _plant_lookup()
    recommendations = []
    for entry in model_predictions:
        plant_name = entry['plant_name']
        plant = plant_catalog.get(plant_name)
        confidence = float(entry.get('confidence', 0.0))
        percentage = float(entry.get('probability_percent', confidence * 100.0))
        recommendation = {
            'name': plant_name,
            'score': round(percentage, 2),
            'confidence': round(confidence, 6),
            'probabilityPercent': round(percentage, 2),
            'reason': f'The model assigned a probability of {percentage:.2f}% to this plant for the supplied cultivation conditions.',
            'whySuitable': f'This recommendation is based on the trained cultivation model and the model probability for this plant is {percentage:.2f}%.',
        }
        if plant is not None:
            recommendation.update(_plant_details(plant))
        recommendations.append(recommendation)

    if not recommendations:
        return jsonify({'error': 'No valid plant recommendations were returned by the trained model.'}), 500

    best_plant = recommendations[0]
    return jsonify({'bestPlant': best_plant, 'recommendations': recommendations})


@bp.route('/quality/validate-image', methods=['POST'])
def validate_quality_image():
    image_file = request.files.get('image')

    if image_file is None:
        return jsonify({"valid": False, "reason": "INVALID_IMAGE"}), 400

    result = quality_image_validator.validate_image_bytes(image_file.read())
    status_code = 200 if result.get("valid") else 422

    if result.get("reason") == "INVALID_IMAGE":
        status_code = 400

    return jsonify(result), status_code


def _combined_validation_result(image_bytes_list):
    results = [
        quality_image_validator.validate_image_bytes(image_bytes)
        for image_bytes in image_bytes_list
    ]
    failed = next((result for result in results if not result.get("valid")), None)
    if failed is not None:
        return {**failed, "image_count": len(results)}

    blur_scores = [result["blur_score"] for result in results if "blur_score" in result]
    brightness_values = [
        result["brightness"] for result in results if "brightness" in result
    ]
    return {
        "valid": True,
        "resolution": results[0].get("resolution") if results else None,
        "blur_score": round(sum(blur_scores) / len(blur_scores), 2)
        if blur_scores else None,
        "brightness": round(sum(brightness_values) / len(brightness_values), 2)
        if brightness_values else None,
        "warnings": [],
        "image_count": len(results),
    }


def _stored_images_or_response(upload_id):
    images = get_upload(upload_id)
    if images is None:
        return None, (
            jsonify({
                "accepted": False,
                "reason": "UPLOAD_EXPIRED",
                "error": "The temporary upload expired. Upload the image again.",
            }),
            404,
        )
    return images, None


@bp.route('/quality/uploads', methods=['POST'])
def create_quality_upload():
    image_files = request.files.getlist('image')
    if not image_files:
        return jsonify({"accepted": False, "reason": "INVALID_IMAGE"}), 400
    if len(image_files) > 3:
        return jsonify({"accepted": False, "reason": "TOO_MANY_IMAGES"}), 400

    images = [image_file.read() for image_file in image_files]
    if any(not image_bytes for image_bytes in images):
        return jsonify({"accepted": False, "reason": "INVALID_IMAGE"}), 400

    upload_id = create_upload(images)
    return jsonify({"upload_id": upload_id, "image_count": len(images)}), 201


@bp.route('/quality/uploads/<upload_id>', methods=['DELETE'])
def delete_quality_upload(upload_id):
    discard_upload(upload_id)
    return '', 204


@bp.route('/quality/uploads/<upload_id>/validate', methods=['POST'])
def validate_quality_upload(upload_id):
    images, error_response = _stored_images_or_response(upload_id)
    if error_response is not None:
        return error_response

    result = _combined_validation_result(images)
    if not result.get("valid"):
        discard_upload(upload_id)
    status_code = 200 if result.get("valid") else 422
    if result.get("reason") == "INVALID_IMAGE":
        status_code = 400
    return jsonify(result), status_code


@bp.route('/quality/uploads/<upload_id>/identify', methods=['POST'])
def identify_quality_upload(upload_id):
    images, error_response = _stored_images_or_response(upload_id)
    if error_response is not None:
        return error_response

    try:
        result = quality_plant_identifier.identify_plant_from_multiple_images(images)
    except Exception:
        current_app.logger.exception("Quality plant model inference failed")
        discard_upload(upload_id)
        return jsonify({
            "accepted": False,
            "reason": "MODEL_LOAD_FAILED",
            "error": "The plant model could not be loaded.",
        }), 503

    if not result.get("accepted"):
        discard_upload(upload_id)
    else:
        set_plant_result(upload_id, result)
    status_code = 200 if result.get("accepted") else 422
    if result.get("reason") == "INVALID_IMAGE":
        status_code = 400
    return jsonify(result), status_code


@bp.route('/quality/uploads/<upload_id>/assess', methods=['POST'])
def assess_quality_upload(upload_id):
    images, error_response = _stored_images_or_response(upload_id)
    if error_response is not None:
        return error_response

    try:
        plant_result = get_plant_result(upload_id)
        if plant_result is None:
            plant_result = quality_plant_identifier.identify_plant_from_multiple_images(
                images
            )
        result = quality_condition_classifier.assess_condition_from_multiple_images(
            image_bytes_list=images,
            plant_result=plant_result,
            disease_lookup=quality_disease_lookup,
            maturity_classifier=quality_maturity_classifier,
            maturity_lookup=quality_maturity_lookup,
            maturity_decision=quality_maturity_decision,
            manual_support_service=quality_manual_maturity_support,
            gradcam_service=quality_gradcam,
            manual_inputs={},
        )
    except Exception:
        current_app.logger.exception("Quality condition model inference failed")
        return jsonify({
            "accepted": False,
            "reason": "MODEL_LOAD_FAILED",
            "error": "The condition model could not be loaded.",
        }), 503
    finally:
        discard_upload(upload_id)

    status_code = 200 if result.get("accepted") else 422
    if result.get("reason") == "INVALID_IMAGE":
        status_code = 400
    return jsonify(result), status_code

@bp.route('/quality/identify-plant', methods=['POST'])
def identify_quality_plant():
    image_file = request.files.get('image')

    if image_file is None:
        return jsonify({"accepted": False, "reason": "INVALID_IMAGE"}), 400

    result = quality_plant_identifier.identify_plant_from_bytes(image_file.read())
    status_code = 200 if result.get("accepted") else 422

    if result.get("reason") == "INVALID_IMAGE":
        status_code = 400

    return jsonify(result), status_code

@bp.route('/quality/identify-plant-multiple', methods=['POST'])
def identify_quality_plant_multiple():
    image_files = request.files.getlist('image')

    if not image_files:
        return jsonify({"accepted": False, "reason": "INVALID_IMAGE"}), 400

    if len(image_files) > 3:
        return jsonify({"accepted": False, "reason": "TOO_MANY_IMAGES"}), 400

    result = quality_plant_identifier.identify_plant_from_multiple_images([
        image_file.read() for image_file in image_files
    ])
    status_code = 200 if result.get("accepted") else 422

    if result.get("reason") == "INVALID_IMAGE":
        status_code = 400

    return jsonify(result), status_code

@bp.route('/quality/assess-condition', methods=['POST'])
def assess_quality_condition():
    image_files = request.files.getlist('image')

    if not image_files:
        return jsonify({"accepted": False, "reason": "INVALID_IMAGE"}), 400

    if len(image_files) > 3:
        return jsonify({"accepted": False, "reason": "TOO_MANY_IMAGES"}), 400

    image_bytes_list = [image_file.read() for image_file in image_files]
    for image_bytes in image_bytes_list:
        validation = quality_image_validator.validate_image_bytes(image_bytes)
        if not validation.get("valid"):
            status_code = 400 if validation.get("reason") == "INVALID_IMAGE" else 422
            return jsonify({
                "accepted": False,
                "reason": validation.get("reason", "INVALID_IMAGE"),
                "validation": validation,
            }), status_code
    manual_inputs = _parse_manual_inputs(request.form.get("manual_inputs"))
    plant_result = quality_plant_identifier.identify_plant_from_multiple_images(
        image_bytes_list
    )
    result = quality_condition_classifier.assess_condition_from_multiple_images(
        image_bytes_list=image_bytes_list,
        plant_result=plant_result,
        disease_lookup=quality_disease_lookup,
        maturity_classifier=quality_maturity_classifier,
        maturity_lookup=quality_maturity_lookup,
        maturity_decision=quality_maturity_decision,
        manual_support_service=quality_manual_maturity_support,
        gradcam_service=quality_gradcam,
        manual_inputs=manual_inputs,
    )
    status_code = 200 if result.get("accepted") else 422

    if result.get("reason") == "INVALID_IMAGE":
        status_code = 400

    return jsonify(result), status_code


@bp.route('/quality/assess-disease-incidence', methods=['POST'])
def assess_quality_disease_incidence():
    initial_file = request.files.get('initial_image')
    additional_files = request.files.getlist('sample_images')
    if initial_file is not None:
        image_files = [initial_file, *additional_files]
    else:
        image_files = request.files.getlist('image')

    if not image_files:
        return jsonify({"accepted": False, "reason": "NO_IMAGES"}), 400
    if len(image_files) > 25:
        return jsonify({"accepted": False, "reason": "TOO_MANY_IMAGES"}), 400

    regions = _parse_regions(request.form.get('regions'))
    samples = []
    for index, image_file in enumerate(image_files):
        samples.append({
            "bytes": image_file.read(),
            "filename": image_file.filename,
            "region": regions[index] if index < len(regions) else None,
        })

    try:
        result = quality_disease_incidence.assess_samples(
            samples=samples,
            validate_image=quality_image_validator.validate_image_bytes,
            identify_plant=quality_plant_identifier.identify_plant_from_bytes,
            classify_condition=quality_condition_classifier.assess_condition_image,
            disease_lookup=quality_disease_lookup.get_disease_info,
        )
    except quality_disease_incidence.IncidenceDataError as exc:
        return jsonify({"accepted": False, "reason": "KNOWLEDGE_BASE_UNAVAILABLE", "error": str(exc)}), 503
    except (OSError, ValueError, csv.Error) as exc:
        return jsonify({"accepted": False, "reason": "ASSESSMENT_ERROR", "error": str(exc)}), 500
    except Exception as exc:
        return jsonify({
            "accepted": False,
            "reason": "MODEL_INFERENCE_FAILED",
            "error": str(exc),
        }), 500

    reason = result.get("reason")
    if result.get("accepted"):
        status_code = 200
    elif reason in {"NO_IMAGES", "TOO_MANY_IMAGES", "INVALID_IMAGE"}:
        status_code = 400
    elif reason in {"MODEL_NOT_AVAILABLE", "MODEL_RUNTIME_MISSING"}:
        status_code = 503
    else:
        status_code = 422
    return jsonify(result), status_code


def _parse_manual_inputs(raw_value):
    if not raw_value:
        return {}

    try:
        parsed = json.loads(raw_value)
    except (TypeError, ValueError):
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _parse_regions(raw_value):
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except (TypeError, ValueError):
        return []
    return [str(value).strip() or None for value in parsed] if isinstance(parsed, list) else []

@bp.route('/predict', methods=['POST'])
def predict():
    images = request.files.getlist('images')
    model_type = request.form.get('model_type', 'plant').lower()

    if not images:
        return jsonify({"error": "Upload 1 to 5 images using the form field name 'images'."}), 400

    if len(images) > 5:
        return jsonify({"error": "Maximum 5 images are allowed."}), 400

    if model_type not in {'plant', 'seed', 'flower'}:
        return jsonify({"error": "model_type must be 'plant', 'seed', or 'flower'."}), 400

    if request.form.get('validate_category', '').lower() in {'1', 'true', 'yes'}:
        expected_organ = 'leaf' if model_type == 'plant' else model_type
        try:
            detected = detect_organs(images[0], confidence=0.70)["detections"]
            images[0].stream.seek(0)
            if detected:
                strongest = max(detected, key=lambda item: item["confidence"])
                if strongest["label"] != expected_organ:
                    suggested_type = 'plant' if strongest["label"] == 'leaf' else strongest["label"]
                    display_name = {
                        'plant': 'Leaf / plant', 'seed': 'Seed / spice', 'flower': 'Flower'
                    }[suggested_type]
                    return jsonify({
                        "error": (
                            f"This image looks like a {strongest['label']}, not a {expected_organ}. "
                            f"Please select '{display_name}' and try again."
                        ),
                        "error_code": "category_mismatch",
                        "selected_category": model_type,
                        "suggested_category": suggested_type,
                        "detected_organ": strongest["label"],
                        "organ_confidence_percent": strongest["confidence_percent"],
                    }), 400
        except (OrganDetectorNotReadyError, ValueError):
            images[0].stream.seek(0)

    try:
        result = predict_herb(images, model_type=model_type)
    except ModelNotReadyError as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result)


def _expert_authorized():
    expected = os.getenv("EXPERT_REVIEW_KEY")
    return bool(expected) and request.headers.get("X-Expert-Key") == expected


@bp.route('/verifications', methods=['POST'])
def submit_verification():
    images = request.files.getlist('images')
    try:
        record = create_request(
            images,
            request.form.get('ai_identification', ''),
            request.form.get('ai_confidence', 0),
            request.form.get('training_consent', '').lower() in {'1', 'true', 'yes'},
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(record), 201


@bp.route('/verifications/<request_id>', methods=['GET'])
def verification_status(request_id):
    record = get_request(request_id)
    if not record:
        return jsonify({"error": "Verification request not found."}), 404
    return jsonify(record)


@bp.route('/expert/verifications', methods=['GET'])
def expert_queue():
    if not _expert_authorized():
        return jsonify({"error": "Expert authorization required."}), 401
    return jsonify({"requests": list_pending_requests()})


@bp.route('/expert/verifications/<request_id>', methods=['POST'])
def expert_verify(request_id):
    if not _expert_authorized():
        return jsonify({"error": "Expert authorization required."}), 401
    data = request.get_json(silent=True) or {}
    try:
        record = verify_request(
            request_id,
            data.get('identification', ''),
            data.get('notes', ''),
            data.get('reviewer_name', ''),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not record:
        return jsonify({"error": "Verification request not found."}), 404
    return jsonify(record)


@bp.route('/expert/verifications/<request_id>/images/<image_name>', methods=['GET'])
def expert_image(request_id, image_name):
    if not _expert_authorized():
        return jsonify({"error": "Expert authorization required."}), 401
    path = image_path(request_id, image_name)
    if not path:
        return jsonify({"error": "Image not found."}), 404
    return send_file(path, mimetype='image/jpeg')

@bp.route('/clear', methods=['POST'])
def clear():
    data = request.get_json()
    session_id = data.get('session_id', 'default')
    try:
        from conversation_rag_bilingual_test import clear_conversation
        clear_conversation(session_id)
        return jsonify({"message": "Conversation history cleared"})
    except ImportError as exc:
        return jsonify({"error": f"RAG dependencies are not installed: {exc}"}), 503
