import importlib.util
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

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "message": "Backend is working"})

@bp.route('/ask', methods=['POST'])
def ask():
    """Placeholder for RAG Chatbot - You will implement this in your branch"""
    data = request.get_json()
    query = data.get('query', '') if data else ''
    
    return jsonify({
        "answer": "This is a placeholder response. RAG functionality will be added in feature/rag branch.",
        "query": query,
        "sources": []
    })

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
