import json
from pathlib import Path

from app.services.predictor import _benefits_for_label


BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_every_active_model_label_has_reviewed_benefits():
    benefits = json.loads(
        (BACKEND_DIR / "ml" / "metadata" / "benefits.json").read_text(encoding="utf-8")
    )
    benefits.update(json.loads(
        (BACKEND_DIR / "app" / "data" / "benefits_supplement.json").read_text(encoding="utf-8")
    ))
    label_paths = [
        BACKEND_DIR / "ml" / "exports" / "labels.json",
        BACKEND_DIR / "ml" / "exports" / "seed" / "labels.json",
        BACKEND_DIR / "ml" / "exports" / "flower_retrained" / "labels.json",
    ]

    for label_path in label_paths:
        for label in json.loads(label_path.read_text(encoding="utf-8")):
            record = _benefits_for_label(benefits, label)
            assert "has not been added" not in " ".join(record["traditional_uses"])
            assert record["traditional_uses"]
            assert record["preparation_notes"]
            assert record["safety_warning"]
            assert record["medical_disclaimer"]


def test_every_dataset_class_has_reviewed_benefits():
    benefits = json.loads(
        (BACKEND_DIR / "ml" / "metadata" / "benefits.json").read_text(encoding="utf-8")
    )
    benefits.update(json.loads(
        (BACKEND_DIR / "app" / "data" / "benefits_supplement.json").read_text(encoding="utf-8")
    ))
    dataset_dirs = [
        BACKEND_DIR / "ml" / "dataset" / "Leaf_dataset",
        BACKEND_DIR / "ml" / "dataset" / "seed_dataset",
        BACKEND_DIR / "ml" / "dataset" / "flowers_dataset",
    ]
    for dataset_dir in dataset_dirs:
        for class_dir in (path for path in dataset_dir.iterdir() if path.is_dir()):
            record = _benefits_for_label(benefits, class_dir.name)
            assert "has not been added" not in " ".join(record["traditional_uses"]), class_dir.name
