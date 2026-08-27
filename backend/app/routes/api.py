from flask import Blueprint, request, jsonify

from app.services.predictor import ModelNotReadyError, model_status, predict_herb

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/health', methods=['GET'])
def health():
    status = model_status()
    return jsonify({
        "status": "healthy" if status["ready"] else "degraded",
        "message": "Backend is working",
        "model": status,
    })

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


@bp.route('/predict', methods=['POST'])
def predict():
    images = request.files.getlist('images')

    if not images:
        return jsonify({"error": "Upload 1 to 5 images using the form field name 'images'."}), 400

    if len(images) > 5:
        return jsonify({"error": "Maximum 5 images are allowed."}), 400

    try:
        result = predict_herb(images)
    except ModelNotReadyError as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result)
