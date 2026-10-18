import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_CSV_PATH = (
    Path(__file__).resolve().parents[1]
    / "quality-data"
    / "quality.maturity_knowledge_with_medicinal_suitability.csv"
)


def get_maturity_info(species: str, stage: str) -> dict[str, Any]:
    species_key = _normalize_key(species)
    stage_key = _normalize_key(stage)

    for row in _load_rows():
        if (
            _normalize_key(row.get("species", "")) == species_key
            and _normalize_key(row.get("model_stage_label", "")) == stage_key
        ):
            return _format_row(row, found=True)

    return {
        "found": False,
        "species": species,
        "model_stage_label": stage,
        "canonical_maturity_stage": None,
        "medicinal_suitability_level": "Expert_Verification_Recommended",
        "medicinal_maturity_assessment": "Expert verification recommended.",
        "medicinal_evidence_strength": "",
        "reference": "",
    }


def get_all_maturity_stages(species: str) -> list[dict[str, Any]]:
    species_key = _normalize_key(species)
    rows = [
        _format_row(row, found=True)
        for row in _load_rows()
        if _normalize_key(row.get("species", "")) == species_key
    ]
    return sorted(rows, key=lambda row: row.get("stage_order") or 999)


@lru_cache(maxsize=1)
def _load_rows() -> list[dict[str, str]]:
    csv_path = Path(os.getenv("QUALITY_MATURITY_KNOWLEDGE_CSV", DEFAULT_CSV_PATH))

    if not csv_path.exists():
        return []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def _format_row(row: dict[str, str], found: bool) -> dict[str, Any]:
    return {
        "found": found,
        "species": row.get("species", ""),
        "model_stage_label": row.get("model_stage_label", ""),
        "canonical_maturity_stage": row.get("canonical_maturity_stage") or None,
        "stage_order": _to_int(row.get("stage_order")),
        "supported_for_model3": _to_bool(row.get("supported_for_model3")),
        "leaf_length_min_cm": _to_float(row.get("leaf_length_min_cm")),
        "leaf_length_max_cm": _to_float(row.get("leaf_length_max_cm")),
        "leaf_width_min_cm": _to_float(row.get("leaf_width_min_cm")),
        "leaf_width_max_cm": _to_float(row.get("leaf_width_max_cm")),
        "numeric_size_evidence": row.get("numeric_size_evidence") or "",
        "literature_size_reference": row.get("literature_size_reference") or "",
        "relative_leaf_size": row.get("relative_leaf_size") or "",
        "typical_texture": row.get("typical_texture") or "",
        "typical_edge": row.get("typical_edge") or "",
        "typical_color": row.get("typical_color") or "",
        "surface_character": row.get("surface_character") or "",
        "development_marker": row.get("development_marker") or "",
        "visual_characteristics": row.get("visual_characteristics") or "",
        "best_manual_cues": row.get("best_manual_cues") or "",
        "size_support_strength": row.get("size_support_strength") or "",
        "texture_support_strength": row.get("texture_support_strength") or "",
        "color_support_strength": row.get("color_support_strength") or "",
        "decision_support_rule": row.get("decision_support_rule") or "",
        "evidence_strength": row.get("evidence_strength") or "",
        "local_calibration_required": _to_bool(row.get("local_calibration_required")),
        "medicinal_suitability_level": (
            row.get("medicinal_suitability_level")
            or "Expert_Verification_Recommended"
        ),
        "medicinal_maturity_assessment": (
            row.get("medicinal_maturity_assessment")
            or "Expert verification recommended."
        ),
        "medicinal_evidence_strength": row.get("medicinal_evidence_strength") or "",
        "reference": row.get("reference") or "",
    }


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _to_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None

    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None

    try:
        return int(float(value))
    except ValueError:
        return None


def _to_bool(value: str | None) -> bool:
    return _normalize_key(value or "") in {"true", "yes", "1", "supported"}
