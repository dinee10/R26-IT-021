import csv
import importlib.util
import json
import sys
from math import isfinite
from pathlib import Path

from flask import Blueprint, jsonify, request

bp = Blueprint('api', __name__, url_prefix='/api')
DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'medicinal_plant_cultivation.csv'
CURRENCY_TO_USD = {'LKR': 0.0031, 'USD': 1, 'EUR': 1.08, 'GBP': 1.27, 'INR': 0.012, 'AUD': 0.65, 'CAD': 0.73, 'JPY': 0.0067}


def _split(value):
    return [item.strip() for item in value.split(';') if item.strip()]


def _load_plants():
    """Load the editable cultivation starter dataset."""
    with DATA_FILE.open(encoding='utf-8-sig', newline='') as dataset:
        plants = list(csv.DictReader(dataset))
    if not plants:
        raise ValueError('The cultivation dataset is empty.')
    return plants


def _choice_value(value):
    return (value or '').split(' - ', 1)[0].strip()


def _plant_details(plant, reason):
    return {
        'whySuitable': f'{reason}.',
        'soilRequirement': plant['soil_requirement'],
        'sunlightRequirement': plant['sunlight_requirement'],
        'wateringRequirement': plant['watering_requirement'],
        'plantingMethod': plant['planting_method'],
        'fertilizerCare': plant['fertilizer_care'],
        'growingPeriod': plant['growing_period'],
        'sellingPrice': plant['selling_price_lkr'],
        'harvestingInformation': plant['harvesting_information'],
    }


@bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'message': 'Backend is working'})


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
@bp.route('/ask', methods=['POST'])
import os
from io import BytesIO

from flask import Blueprint, request, jsonify, send_file
from werkzeug.datastructures import FileStorage

from app.services.predictor import ModelNotReadyError, model_status, predict_herb
from app.services.organ_detector import OrganDetectorNotReadyError, detect_organs, detector_status
from app.services.health_assessor import assess_plant_health
from app.services.expert_verification import (
    create_request,
    get_request,
    image_path,
    list_pending_requests,
    verify_request,
)
api = Blueprint('api', __name__)

@api.route('/health', methods=['GET'])
def health():
    status = model_status()
    return jsonify({
        "status": "healthy" if status["ready"] else "degraded",
        "message": "Backend is working",
        "model": status,
        "organ_detector": detector_status(),
    })


@api.route('/detect-organs', methods=['POST'])
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


@api.route('/identify-live', methods=['POST'])
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


@api.route('/assess-health', methods=['POST'])
def assess_health():
    try:
        return jsonify(assess_plant_health(request.files.get('image')))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

@api.route('/ask', methods=['POST'])
def ask():
    """Placeholder for RAG Chatbot - You will implement this in your branch."""
    data = request.get_json() or {}
    query = data.get('query', '')
    return jsonify({'answer': 'This is a placeholder response. RAG functionality will be added in feature/rag branch.', 'query': query, 'sources': []})


@bp.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json(silent=True) or {}
    required = ('temperature', 'rainfall', 'humidity', 'soilType', 'growingSpace', 'budgetAmount', 'budgetCurrency', 'irrigationMethod', 'sunlight', 'growingSeason', 'growingDuration')
    missing = [field for field in required if data.get(field) in (None, '')]
    if missing:
        return jsonify({'error': 'Missing required fields', 'fields': missing}), 400

    try:
        temperature, rainfall, humidity = float(data['temperature']), float(data['rainfall']), float(data['humidity'])
        budget = float(data['budgetAmount'])
        soil_ph = data.get('soilPh')
        soil_ph = None if soil_ph in (None, '') else float(soil_ph)
    except (TypeError, ValueError):
        return jsonify({'error': 'Weather, budget, and soil pH values must be numeric'}), 400

    if not all(isfinite(value) for value in (temperature, rainfall, humidity, budget)) or budget < 0:
        return jsonify({'error': 'Weather and budget values must be valid and non-negative'}), 400
    if soil_ph is not None and (not isfinite(soil_ph) or not 0 <= soil_ph <= 14):
        return jsonify({'error': 'Soil pH must be between 0 and 14'}), 400

    soil, sunlight, duration = _choice_value(data['soilType']), _choice_value(data['sunlight']), _choice_value(data['growingDuration'])
    irrigation, season = data['irrigationMethod'], data['growingSeason']
    budget_lkr = budget * CURRENCY_TO_USD.get(data['budgetCurrency'], 1) / CURRENCY_TO_USD['LKR']
    try:
        plants = _load_plants()
    except (OSError, ValueError, csv.Error) as error:
        return jsonify({'error': f'Could not load cultivation dataset: {error}'}), 500

    scored = []
    for plant in plants:
        score, matches = 0, []
        soils, spaces = _split(plant['soil_types']), _split(plant['growing_spaces'])
        rain_min, rain_max = float(plant['rainfall_min_mm']), float(plant['rainfall_max_mm'])
        if soil == 'Not sure' or soil in soils:
            score += 3; matches.append('soil')
        if data['growingSpace'] in spaces:
            score += 3; matches.append('growing space')
        if sunlight in _split(plant['sunlight']):
            score += 2; matches.append('sunlight')
        if float(plant['temperature_min_c']) <= temperature <= float(plant['temperature_max_c']):
            score += 2; matches.append('temperature')
        if rain_min <= rainfall <= rain_max:
            score += 2; matches.append('rainfall')
        if duration in _split(plant['growing_durations']):
            score += 2; matches.append('growing duration')
        if season in _split(plant['planting_months']):
            score += 1; matches.append('planting month')
        if float(plant['humidity_min_pct']) <= humidity <= float(plant['humidity_max_pct']):
            score += 1; matches.append('humidity')
        if soil_ph is not None and float(plant['soil_ph_min']) <= soil_ph <= float(plant['soil_ph_max']):
            score += 1; matches.append('soil pH')
        if budget_lkr >= float(plant['minimum_budget_lkr']):
            score += 1; matches.append('budget')
        if irrigation == 'Rain only' and rainfall >= rain_min:
            score += 1; matches.append('watering method')
        elif irrigation in _split(plant['irrigation']):
            score += 1; matches.append('watering method')
        scored.append((score, plant, matches))

    scored.sort(key=lambda item: (-item[0], item[1]['plant_name']))
    recommendations = []
    for score, plant, matches in scored[:5]:
        reason = 'Matches your ' + ', '.join(matches[:3]) if matches else 'A possible match based on your details'
        recommendation = {'name': plant['plant_name'], 'score': score, 'reason': reason}
        recommendation.update(_plant_details(plant, reason))
        recommendations.append(recommendation)
    return jsonify({'bestPlant': recommendations[0], 'recommendations': recommendations})


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


def _parse_manual_inputs(raw_value):
    if not raw_value:
        return {}

    try:
        parsed = json.loads(raw_value)
    except (TypeError, ValueError):
        return {}

    return parsed if isinstance(parsed, dict) else {}

    data = request.get_json(silent=True) or {}
    query = str(data.get('query', '')).strip()
    session_id = str(data.get('session_id', 'default')).strip() or 'default'
    user_context = data.get('user_context', {})

    if not query:
        return jsonify(dict(error='Query is required.')), 400
    if not isinstance(user_context, dict):
        return jsonify(dict(error='user_context must be an object.')), 400
    
    try:
        from conversation_rag import ask_question
        return jsonify(ask_question(query, session_id, user_context))
    except (ImportError, ModuleNotFoundError) as exc:
        return jsonify(dict(error=f'RAG dependencies are not installed: {exc}')), 503
    except Exception as exc:
        return jsonify(dict(error=f'The knowledge assistant is unavailable: {exc}')), 503


@api.route('/predict', methods=['POST'])
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


@api.route('/verifications', methods=['POST'])
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


@api.route('/verifications/<request_id>', methods=['GET'])
def verification_status(request_id):
    record = get_request(request_id)
    if not record:
        return jsonify({"error": "Verification request not found."}), 404
    return jsonify(record)


@api.route('/expert/verifications', methods=['GET'])
def expert_queue():
    if not _expert_authorized():
        return jsonify({"error": "Expert authorization required."}), 401
    return jsonify({"requests": list_pending_requests()})


@api.route('/expert/verifications/<request_id>', methods=['POST'])
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


@api.route('/expert/verifications/<request_id>/images/<image_name>', methods=['GET'])
def expert_image(request_id, image_name):
    if not _expert_authorized():
        return jsonify({"error": "Expert authorization required."}), 401
    path = image_path(request_id, image_name)
    if not path:
        return jsonify({"error": "Image not found."}), 404
    return send_file(path, mimetype='image/jpeg')
@api.route('/clear', methods=['POST'])
def clear():
    data = request.get_json()
    session_id = data.get('session_id', 'default')
    try:
        from conversation_rag import clear_conversation
        clear_conversation(session_id)
        return jsonify({"message": "Conversation history cleared"})
    except ImportError as exc:
        return jsonify({"error": f"RAG dependencies are not installed: {exc}"}), 503
