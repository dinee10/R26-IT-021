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
