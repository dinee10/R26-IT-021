from pathlib import Path
from importlib.util import find_spec

BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = BACKEND_DIR / "ml" / "exports" / "yolo_organ" / "best.pt"
ALLOWED_CLASSES = {"leaf", "seed", "flower"}
_model = None
_yolo_class = None


class OrganDetectorNotReadyError(RuntimeError):
    pass


def detector_status():
    return {
        "ready": find_spec("ultralytics") is not None and MODEL_PATH.exists(),
        "ultralytics_installed": find_spec("ultralytics") is not None,
        "model_path": str(MODEL_PATH.relative_to(BACKEND_DIR)),
        "model_exists": MODEL_PATH.exists(),
    }


def _load_model():
    global _model, _yolo_class
    if find_spec("ultralytics") is None:
        raise OrganDetectorNotReadyError(
            "Ultralytics is not installed. Install backend/ml/requirements.txt."
        )
    if not MODEL_PATH.exists():
        raise OrganDetectorNotReadyError(
            "The live organ detector is not trained. Train YOLO and place best.pt in "
            "backend/ml/exports/yolo_organ/."
        )
    if _model is None:
        if _yolo_class is None:
            try:
                from ultralytics import YOLO
            except (ImportError, OSError) as exc:
                raise OrganDetectorNotReadyError(
                    "Ultralytics could not start. Check available memory and its runtime dependencies."
                ) from exc
            _yolo_class = YOLO
        _model = _yolo_class(str(MODEL_PATH))
    return _model


def preload_model():
    """Load and retain the YOLO detector in this server process."""
    _load_model()
    return True


def detect_organs(uploaded_file, confidence=0.35):
    if not uploaded_file or not uploaded_file.filename:
        raise ValueError("Upload one camera frame using the form field name 'image'.")
    if not 0.05 <= confidence <= 0.95:
        raise ValueError("confidence must be between 0.05 and 0.95.")
    from PIL import Image, UnidentifiedImageError
    try:
        image = Image.open(uploaded_file.stream).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The uploaded camera frame is not a valid image.") from exc

    width, height = image.size
    result = _load_model().predict(image, conf=confidence, verbose=False)[0]
    detections = []
    for box in result.boxes:
        class_id = int(box.cls.item())
        label = str(result.names[class_id]).lower().strip()
        if label not in ALLOWED_CLASSES:
            continue
        x1, y1, x2, y2 = (float(value) for value in box.xyxyn[0].tolist())
        detections.append({
            "label": label,
            "confidence": round(float(box.conf.item()), 4),
            "confidence_percent": round(float(box.conf.item()) * 100, 2),
            "box": {"left": max(0.0, min(1.0, x1)), "top": max(0.0, min(1.0, y1)),
                    "right": max(0.0, min(1.0, x2)), "bottom": max(0.0, min(1.0, y2))},
        })
    return {"width": width, "height": height, "detections": detections}
