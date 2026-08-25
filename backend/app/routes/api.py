import importlib.util
import sys
from pathlib import Path

from flask import Blueprint, request, jsonify

_validator_path = (
    Path(__file__).resolve().parents[1]
    / "quality-services"
    / "quality.image_validator.py"
)
_validator_spec = importlib.util.spec_from_file_location(
    "quality_image_validator",
    _validator_path,
)
quality_image_validator = importlib.util.module_from_spec(_validator_spec)
assert _validator_spec.loader is not None
sys.modules[_validator_spec.name] = quality_image_validator
_validator_spec.loader.exec_module(quality_image_validator)

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
