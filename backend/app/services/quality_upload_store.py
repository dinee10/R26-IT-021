"""Short-lived, in-memory storage for the multi-stage quality pipeline."""

import os
import threading
import time
import uuid


_LOCK = threading.Lock()
_UPLOADS = {}
_TTL_SECONDS = int(os.getenv("QUALITY_UPLOAD_TTL_SECONDS", "300"))
_MAX_UPLOADS = int(os.getenv("QUALITY_MAX_PENDING_UPLOADS", "32"))


def _remove_expired(now):
    expired = [
        upload_id
        for upload_id, entry in _UPLOADS.items()
        if now - entry["created_at"] > _TTL_SECONDS
    ]
    for upload_id in expired:
        _UPLOADS.pop(upload_id, None)


def create_upload(images):
    """Keep immutable image bytes until assessment finishes or the TTL expires."""
    now = time.monotonic()
    with _LOCK:
        _remove_expired(now)
        while len(_UPLOADS) >= _MAX_UPLOADS:
            oldest_id = min(
                _UPLOADS,
                key=lambda upload_id: _UPLOADS[upload_id]["created_at"],
            )
            _UPLOADS.pop(oldest_id, None)

        upload_id = uuid.uuid4().hex
        _UPLOADS[upload_id] = {
            "created_at": now,
            "images": tuple(bytes(image) for image in images),
            "plant_result": None,
        }
        return upload_id


def get_upload(upload_id):
    now = time.monotonic()
    with _LOCK:
        _remove_expired(now)
        entry = _UPLOADS.get(upload_id)
        return entry["images"] if entry is not None else None


def discard_upload(upload_id):
    with _LOCK:
        return _UPLOADS.pop(upload_id, None) is not None


def set_plant_result(upload_id, plant_result):
    with _LOCK:
        entry = _UPLOADS.get(upload_id)
        if entry is None:
            return False
        entry["plant_result"] = dict(plant_result)
        return True


def get_plant_result(upload_id):
    with _LOCK:
        entry = _UPLOADS.get(upload_id)
        result = entry.get("plant_result") if entry is not None else None
        return dict(result) if result is not None else None
