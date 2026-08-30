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
    data = request.get_json()
    query = data.get('query', '').strip()
    session_id = data.get('session_id', 'default')
    user_context = data.get('user_context', {})

    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        result = ask_question(
            user_question=query,
            session_id=session_id,
            user_context=user_context
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/clear', methods=['POST'])
def clear():
    data = request.get_json()
    session_id = data.get('session_id', 'default')
    clear_conversation(session_id)
    return jsonify({"message": "Conversation history cleared"})

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
