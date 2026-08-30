import csv
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


@bp.route('/ask', methods=['POST'])
import importlib.util
import json
import sys
from pathlib import Path

from flask import Blueprint, request, jsonify

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
from conversation_rag import ask_question, clear_conversation

api = Blueprint('api', __name__)

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


@api.route('/quality/validate-image', methods=['POST'])
def validate_quality_image():
    image_file = request.files.get('image')

    if image_file is None:
        return jsonify({"valid": False, "reason": "INVALID_IMAGE"}), 400

    result = quality_image_validator.validate_image_bytes(image_file.read())
    status_code = 200 if result.get("valid") else 422

    if result.get("reason") == "INVALID_IMAGE":
        status_code = 400

    return jsonify(result), status_code

@api.route('/quality/identify-plant', methods=['POST'])
def identify_quality_plant():
    image_file = request.files.get('image')

    if image_file is None:
        return jsonify({"accepted": False, "reason": "INVALID_IMAGE"}), 400

    result = quality_plant_identifier.identify_plant_from_bytes(image_file.read())
    status_code = 200 if result.get("accepted") else 422

    if result.get("reason") == "INVALID_IMAGE":
        status_code = 400

    return jsonify(result), status_code

@api.route('/quality/identify-plant-multiple', methods=['POST'])
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

@api.route('/quality/assess-condition', methods=['POST'])
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
