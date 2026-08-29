import os

from flask import Blueprint, request, jsonify, send_file

from app.services.predictor import ModelNotReadyError, model_status, predict_herb
from app.services.expert_verification import (
    create_request,
    get_request,
    image_path,
    list_pending_requests,
    verify_request,
)
from flask import Blueprint, request, jsonify

api = Blueprint('api', __name__)

@api.route('/health', methods=['GET'])
def health():
    status = model_status()
    return jsonify({
        "status": "healthy" if status["ready"] else "degraded",
        "message": "Backend is working",
        "model": status,
    })

@api.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    query = data.get('query', '') if data else ''
    
    return jsonify({
        "answer": "This is a placeholder response. RAG functionality will be added in feature/rag branch.",
        "query": query,
        "sources": []
    })


@api.route('/predict', methods=['POST'])
def predict():
    images = request.files.getlist('images')
    model_type = request.form.get('model_type', 'plant').lower()

    if not images:
        return jsonify({"error": "Upload 1 to 5 images using the form field name 'images'."}), 400

    if len(images) > 5:
        return jsonify({"error": "Maximum 5 images are allowed."}), 400

    if model_type not in {'plant', 'seed'}:
        return jsonify({"error": "model_type must be 'plant' or 'seed'."}), 400

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
    try:
        from conversation_rag import clear_conversation
        clear_conversation(session_id)
        return jsonify({"message": "Conversation history cleared"})
    except ImportError as exc:
        return jsonify({"error": f"RAG dependencies are not installed: {exc}"}), 503
