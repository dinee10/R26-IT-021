import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_CSV_PATH = (
    Path(__file__).resolve().parents[1]
    / "quality-data"
    / "quality.disease_knowledge.csv"
)


def get_disease_info(species: str, disease_name: str) -> dict[str, Any]:
    species_key = _normalize_key(species)
    disease_key = _normalize_key(disease_name)

    for row in _load_rows():
        if (
            _normalize_key(row.get("species", "")) == species_key
            and _normalize_key(row.get("disease_name", "")) == disease_key
        ):
            return {
                "found": True,
                "species": row.get("species", species),
                "disease_name": row.get("disease_name", disease_name),
                "display_name": row.get("display_name") or disease_name,
                "description": row.get("description") or "",
                "typical_symptoms": _split_symptoms(row.get("typical_symptoms", "")),
                "healthy_difference": row.get("healthy_difference") or "",
                "medicinal_use_instruction": (
                    row.get("medicinal_use_instruction")
                    or row.get("instructions")
                    or "Expert verification recommended."
                ),
                "treatment_instruction": row.get("treatment_instruction") or "",
                "medicinal_suitability_level": (
                    row.get("medicinal_suitability_level")
                    or "Expert_Verification_Recommended"
                ),
                "medicinal_suitability_assessment": (
                    row.get("medicinal_suitability_assessment")
                    or "Expert verification recommended."
                ),
                "reference": row.get("reference") or "",
            }

    return {
        "found": False,
        "species": species,
        "disease_name": disease_name,
        "display_name": "Disease information unavailable",
        "description": (
            "No manually verified disease information is available for this "
            "prediction yet."
        ),
        "typical_symptoms": [],
        "healthy_difference": "",
        "medicinal_use_instruction": "Expert verification recommended.",
        "treatment_instruction": "",
        "medicinal_suitability_level": "Expert_Verification_Recommended",
        "medicinal_suitability_assessment": "Expert verification recommended.",
        "reference": "",
    }


@lru_cache(maxsize=1)
def _load_rows() -> list[dict[str, str]]:
    csv_path = Path(os.getenv("QUALITY_DISEASE_KNOWLEDGE_CSV", DEFAULT_CSV_PATH))

    if not csv_path.exists():
        return []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _split_symptoms(value: str) -> list[str]:
    return [
        symptom.strip()
        for symptom in value.split(";")
        if symptom.strip()
    ]
