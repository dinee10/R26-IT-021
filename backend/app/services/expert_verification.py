import io
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, UnidentifiedImageError


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("VERIFICATION_DATA_DIR", BACKEND_DIR / "data" / "verifications"))
DATABASE_PATH = DATA_DIR / "verifications.sqlite3"
MAX_IMAGES = 5


def _now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS verification_requests (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            ai_identification TEXT NOT NULL,
            ai_confidence REAL NOT NULL,
            expert_identification TEXT,
            expert_notes TEXT,
            reviewer_name TEXT,
            training_consent INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            reviewed_at TEXT
        )
        """
    )
    connection.commit()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _public_record(row):
    return {
        "id": row["id"],
        "status": row["status"],
        "identification_label": (
            "Expert verified" if row["status"] == "verified" else "AI identified"
        ),
        "ai_identification": row["ai_identification"],
        "ai_confidence": row["ai_confidence"],
        "expert_identification": row["expert_identification"],
        "expert_notes": row["expert_notes"],
        "reviewer_name": row["reviewer_name"],
        "training_consent": bool(row["training_consent"]),
        "created_at": row["created_at"],
        "reviewed_at": row["reviewed_at"],
    }


def create_request(images, ai_identification, ai_confidence, training_consent=False):
    if not images or len(images) > MAX_IMAGES:
        raise ValueError("Submit 1 to 5 images for expert verification.")
    if not ai_identification or not ai_identification.strip():
        raise ValueError("The AI identification is required.")

    request_id = uuid.uuid4().hex
    request_dir = DATA_DIR / request_id
    request_dir.mkdir(parents=True, exist_ok=False)

    try:
        for index, uploaded_file in enumerate(images, start=1):
            uploaded_file.stream.seek(0)
            try:
                with Image.open(uploaded_file.stream) as source:
                    # Creating a fresh RGB image and saving it without EXIF removes GPS,
                    # device, timestamp, and other identifying metadata.
                    sanitized = source.convert("RGB")
                    sanitized.save(
                        request_dir / f"image_{index}.jpg",
                        format="JPEG",
                        quality=90,
                        optimize=True,
                    )
            except (UnidentifiedImageError, OSError) as exc:
                raise ValueError(f"{uploaded_file.filename} is not a valid image.") from exc

        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO verification_requests
                (id, status, ai_identification, ai_confidence, training_consent, created_at)
                VALUES (?, 'pending', ?, ?, ?, ?)
                """,
                (
                    request_id,
                    ai_identification.strip(),
                    float(ai_confidence),
                    int(bool(training_consent)),
                    _now(),
                ),
            )
            row = connection.execute(
                "SELECT * FROM verification_requests WHERE id = ?", (request_id,)
            ).fetchone()
        return _public_record(row)
    except Exception:
        for path in request_dir.glob("*"):
            path.unlink(missing_ok=True)
        request_dir.rmdir()
        raise


def get_request(request_id):
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM verification_requests WHERE id = ?", (request_id,)
        ).fetchone()
    return _public_record(row) if row else None


def list_pending_requests():
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM verification_requests WHERE status = 'pending' ORDER BY created_at"
        ).fetchall()
    return [
        {**_public_record(row), "image_count": len(list((DATA_DIR / row["id"]).glob("*.jpg")))}
        for row in rows
    ]


def verify_request(request_id, identification, notes, reviewer_name):
    if not identification or not identification.strip():
        raise ValueError("An expert identification is required.")
    if not reviewer_name or not reviewer_name.strip():
        raise ValueError("The reviewer name is required.")

    with _connect() as connection:
        existing = connection.execute(
            "SELECT id FROM verification_requests WHERE id = ?", (request_id,)
        ).fetchone()
        if not existing:
            return None
        connection.execute(
            """
            UPDATE verification_requests
            SET status = 'verified', expert_identification = ?, expert_notes = ?,
                reviewer_name = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (identification.strip(), (notes or "").strip(), reviewer_name.strip(), _now(), request_id),
        )
        row = connection.execute(
            "SELECT * FROM verification_requests WHERE id = ?", (request_id,)
        ).fetchone()
    return _public_record(row)


def image_path(request_id, image_name):
    if not image_name.startswith("image_") or not image_name.endswith(".jpg"):
        return None
    path = DATA_DIR / request_id / image_name
    return path if path.is_file() else None
