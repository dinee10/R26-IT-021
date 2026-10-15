import csv
import hashlib
import os
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable


DATA_DIR = Path(__file__).resolve().parents[1] / "quality-data"
DEFAULT_RULES_PATH = DATA_DIR / "quality.disease_incidence.csv"
DEFAULT_REFERENCES_PATH = DATA_DIR / "quality.disease_incidence_references.csv"
DISCLAIMER = (
    "This assessment estimates condition occurrence among the submitted leaf "
    "samples. It does not directly measure whole-plant disease severity, confirm "
    "the pathogen, or certify medicinal safety."
)
REQUIRED_RULE_COLUMNS = {
    "species", "condition_class", "condition_category", "incidence_label",
    "min_percent", "min_exclusive", "max_percent", "max_inclusive",
    "action_priority", "assessment_interpretation", "verification_steps",
    "recommended_care", "escalation_or_follow_up",
    "medicinal_harvest_caution", "reference_ids", "reference_urls",
    "threshold_validation_status", "treatment_validation_status",
    "assessment_metric", "scientific_caveat",
}


class IncidenceDataError(RuntimeError):
    pass


def normalize_identifier(value: str) -> str:
    return "_".join(value.strip().lower().replace("-", "_").split())


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes"}


def _split(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(";") if part.strip()]


def _path_from_env(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default)))


@lru_cache(maxsize=4)
def load_rules(path_value: str | None = None) -> list[dict[str, str]]:
    path = Path(path_value) if path_value else _path_from_env(
        "QUALITY_DISEASE_INCIDENCE_CSV", DEFAULT_RULES_PATH
    )
    if not path.exists():
        raise IncidenceDataError(f"Incidence rules file is missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_RULE_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise IncidenceDataError(
                "Incidence rules are missing required columns: "
                + ", ".join(sorted(missing))
            )
        rows = list(reader)
    if not rows:
        raise IncidenceDataError("Incidence rules file is empty.")
    validate_intervals(rows)
    return rows


@lru_cache(maxsize=4)
def load_references(path_value: str | None = None) -> dict[str, dict[str, str]]:
    path = Path(path_value) if path_value else _path_from_env(
        "QUALITY_DISEASE_REFERENCES_CSV", DEFAULT_REFERENCES_PATH
    )
    if not path.exists():
        raise IncidenceDataError(f"Incidence references file is missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {row.get("reference_id", ""): row for row in rows if row.get("reference_id")}


def validate_intervals(rows: list[dict[str, str]]) -> None:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (
            normalize_identifier(row.get("species", "")),
            normalize_identifier(row.get("condition_class", "")),
        )
        try:
            lower = float(row["min_percent"])
            upper = float(row["max_percent"])
        except (KeyError, TypeError, ValueError) as exc:
            raise IncidenceDataError(f"Invalid percentage interval for {key}.") from exc
        if lower < 0 or upper > 100 or lower > upper:
            raise IncidenceDataError(f"Out-of-range percentage interval for {key}.")
        grouped.setdefault(key, []).append(row)

    expected = ((0, "None_Detected"), (25, "Low"), (50, "Moderate"),
                (75, "High"), (100, "Very_High"))
    for key, condition_rows in grouped.items():
        for percentage, expected_label in expected:
            matches = [row for row in condition_rows if _matches(row, percentage)]
            if len(matches) != 1 or normalize_identifier(matches[0]["incidence_label"]) != normalize_identifier(expected_label):
                raise IncidenceDataError(
                    f"Rules for {key[0]}/{key[1]} do not uniquely map {percentage}%."
                )


def _matches(row: dict[str, str], percentage: float) -> bool:
    lower = float(row["min_percent"])
    upper = float(row["max_percent"])
    lower_ok = percentage > lower if _as_bool(row["min_exclusive"]) else percentage >= lower
    upper_ok = percentage <= upper if _as_bool(row["max_inclusive"]) else percentage < upper
    return lower_ok and upper_ok


def find_rule(species: str, condition: str, percentage: float) -> dict[str, str] | None:
    species_key = normalize_identifier(species)
    condition_key = normalize_identifier(condition)
    for row in load_rules():
        if (
            normalize_identifier(row.get("species", "")) == species_key
            and normalize_identifier(row.get("condition_class", "")) == condition_key
            and _matches(row, percentage)
        ):
            return row
    return None


def rule_coverage(model_heads: dict[str, list[str]]) -> dict[str, Any]:
    covered = {
        (normalize_identifier(row["species"]), normalize_identifier(row["condition_class"]))
        for row in load_rules()
    }
    expected = {
        (normalize_identifier(species), normalize_identifier(condition))
        for species, conditions in model_heads.items()
        for condition in conditions
        if normalize_identifier(condition) != "healthy"
    }
    missing = sorted(expected - covered)
    return {
        "expected_non_healthy_classes": len(expected),
        "covered_classes": len(expected & covered),
        "missing": [
            {"species": species, "condition_class": condition}
            for species, condition in missing
        ],
    }


def assess_samples(
    samples: list[dict[str, Any]],
    validate_image: Callable[[bytes], dict[str, Any]],
    identify_plant: Callable[[bytes], dict[str, Any]],
    classify_condition: Callable[[bytes, dict[str, Any]], dict[str, Any]],
    disease_lookup: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    if not samples:
        return _empty_result("NO_IMAGES")
    if len(samples) > 25:
        return _empty_result("TOO_MANY_IMAGES", submitted=len(samples))

    initial = _evaluate_sample(
        samples[0], 0, validate_image, identify_plant, classify_condition,
        locked_species=None, seen_hashes=set(),
    )
    if not initial["included"]:
        result = _empty_result(initial["exclusion_reason"], submitted=len(samples))
        result["individual_leaf_predictions"] = [initial]
        result["excluded_images"] = [initial]
        return result
    if initial["condition"]["status"] == "healthy":
        result = _empty_result("INITIAL_CONDITION_HEALTHY", submitted=len(samples))
        result.update({
            "locked_species": initial["plant"],
            "initial_condition_under_verification": initial["condition"],
            "individual_leaf_predictions": [initial],
        })
        return result

    locked_species = initial["plant"]
    primary = initial["condition"]
    predictions = [initial]
    seen_hashes = {initial["content_sha256"]}
    for index, sample in enumerate(samples[1:], start=1):
        predictions.append(_evaluate_sample(
            sample, index, validate_image, identify_plant, classify_condition,
            locked_species=locked_species["species"], seen_hashes=seen_hashes,
        ))

    accepted = [item for item in predictions if item["included"]]
    excluded = [item for item in predictions if not item["included"]]
    if not accepted:
        result = _empty_result("NO_ACCEPTED_SAMPLES", submitted=len(samples))
        result.update({"individual_leaf_predictions": predictions, "excluded_images": excluded})
        return result

    counts = Counter(item["condition"]["class"] for item in accepted)
    total = len(accepted)
    healthy_count = sum(
        count for condition, count in counts.items()
        if normalize_identifier(condition) == "healthy"
    )
    disease_conditions = [condition for condition in counts if normalize_identifier(condition) != "healthy"]
    primary_name = primary["class"]
    ordered = [primary_name] + sorted(
        condition for condition in disease_conditions
        if normalize_identifier(condition) != normalize_identifier(primary_name)
    )
    summaries = [
        _condition_summary(
            locked_species["species"], condition, counts.get(condition, 0), total,
            disease_lookup,
        )
        for condition in ordered
    ]
    region_distribution = Counter(
        item["region"] for item in accepted if item.get("region")
    )
    return {
        "assessment_status": "completed",
        "accepted": True,
        "locked_species": locked_species,
        "initial_condition_under_verification": primary,
        "total_submitted_images": len(samples),
        "total_accepted_images": total,
        "excluded_images": excluded,
        "individual_leaf_predictions": predictions,
        "healthy_sample_count": healthy_count,
        "healthy_percentage": healthy_count * 100.0 / total,
        "per_condition_results": summaries,
        "primary_condition_verification": summaries[0],
        "additional_observed_conditions": summaries[1:],
        "sampled_region_distribution": dict(region_distribution),
        "sampling_warnings": _sampling_warnings(total, len(samples)),
        "scientific_limitations": [
            DISCLAIMER,
            "Model 2 assigns one dominant class per leaf; it does not diagnose multiple independent conditions on one leaf.",
            "Zero detections in submitted samples do not prove that a condition is absent.",
        ],
    }


def _evaluate_sample(
    sample: dict[str, Any],
    index: int,
    validate_image,
    identify_plant,
    classify_condition,
    locked_species: str | None,
    seen_hashes: set[str],
) -> dict[str, Any]:
    image_bytes = sample.get("bytes", b"")
    item = {
        "sample_index": index,
        "filename": sample.get("filename") or f"sample_{index + 1}.jpg",
        "region": sample.get("region"),
        "included": False,
    }
    validation = validate_image(image_bytes)
    item["validation"] = validation
    if not validation.get("valid"):
        item["exclusion_reason"] = validation.get("reason", "INVALID_IMAGE")
        return item
    digest = hashlib.sha256(image_bytes).hexdigest()
    item["content_sha256"] = digest
    if digest in seen_hashes:
        item["exclusion_reason"] = "DUPLICATE_SAMPLE"
        return item
    seen_hashes.add(digest)
    plant = identify_plant(image_bytes)
    item["plant"] = plant
    if not plant.get("accepted"):
        item["exclusion_reason"] = plant.get("reason", "PLANT_NOT_ACCEPTED")
        return item
    if locked_species and normalize_identifier(plant.get("species", "")) != normalize_identifier(locked_species):
        item["exclusion_reason"] = "SPECIES_MISMATCH"
        return item
    condition = classify_condition(image_bytes, plant)
    item["condition"] = condition
    if not condition.get("accepted"):
        item["exclusion_reason"] = condition.get("reason", "CONDITION_NOT_ACCEPTED")
        return item
    item["included"] = True
    return item


def _condition_summary(
    species: str,
    condition: str,
    matching_count: int,
    accepted_count: int,
    disease_lookup,
) -> dict[str, Any]:
    percentage = matching_count * 100.0 / accepted_count
    rule = find_rule(species, condition, percentage)
    baseline = disease_lookup(species, condition)
    common = {
        "species": species,
        "condition_name": condition,
        "accepted_sample_count": accepted_count,
        "matching_sample_count": matching_count,
        "calculated_percentage": percentage,
        "display_percentage": round(percentage, 1),
        "baseline_disease_information": baseline,
    }
    if rule is None:
        return {
            **common,
            "condition_category": "unmapped",
            "incidence_level": "Rules Unavailable",
            "rule_availability": "rules_unavailable",
            "assessment_interpretation": (
                "The model class was observed, but no condition-specific incidence rule is available."
            ),
            "verification_steps": "Seek expert verification of the predicted condition.",
            "recommended_care": "No condition-specific treatment recommendation is available.",
            "escalation_or_follow_up": "Consult a qualified plant-health expert before treatment.",
            "medicinal_harvest_caution": (
                "Do not treat image classification as medicinal-safety clearance."
            ),
            "references": [],
            "scientific_limitations": [DISCLAIMER],
        }
    references = load_references()
    reference_ids = _split(rule.get("reference_ids", ""))
    urls = _split(rule.get("reference_urls", ""))
    resolved = []
    for position, reference_id in enumerate(reference_ids):
        details = references.get(reference_id, {})
        resolved.append({
            "reference_id": reference_id,
            "publisher": details.get("publisher", ""),
            "title": details.get("title", ""),
            "url": details.get("source_url") or (urls[position] if position < len(urls) else ""),
            "evidence_use": details.get("evidence_use", ""),
        })
    return {
        **common,
        "condition_category": rule.get("condition_category", ""),
        "is_infectious_disease_confirmed": rule.get("is_infectious_disease_confirmed", ""),
        "incidence_level": rule.get("incidence_label", ""),
        "rule_availability": "available",
        "action_priority": rule.get("action_priority", ""),
        "assessment_interpretation": rule.get("assessment_interpretation", ""),
        "verification_steps": rule.get("verification_steps", ""),
        "recommended_care": rule.get("recommended_care", ""),
        "escalation_or_follow_up": rule.get("escalation_or_follow_up", ""),
        "medicinal_harvest_caution": rule.get("medicinal_harvest_caution", ""),
        "references": resolved,
        "threshold_validation_status": rule.get("threshold_validation_status", ""),
        "treatment_validation_status": rule.get("treatment_validation_status", ""),
        "assessment_metric": rule.get("assessment_metric", ""),
        "scientific_limitations": [rule.get("scientific_caveat", ""), DISCLAIMER],
    }


def _sampling_warnings(accepted: int, submitted: int) -> list[str]:
    warnings = []
    if accepted < 5:
        warnings.append("Very small accepted sample; reliability is limited.")
    elif accepted < 10:
        warnings.append("Small accepted sample; interpret percentages cautiously.")
    if accepted < 25:
        warnings.append("The research target is up to 25 distinct leaves from different plant regions.")
    if accepted < submitted:
        warnings.append("Excluded images do not contribute to the percentage denominator.")
    return warnings


def _empty_result(reason: str, submitted: int = 0) -> dict[str, Any]:
    return {
        "assessment_status": "insufficient_evidence",
        "accepted": False,
        "reason": reason,
        "locked_species": None,
        "initial_condition_under_verification": None,
        "total_submitted_images": submitted,
        "total_accepted_images": 0,
        "excluded_images": [],
        "individual_leaf_predictions": [],
        "healthy_sample_count": 0,
        "healthy_percentage": None,
        "per_condition_results": [],
        "primary_condition_verification": None,
        "additional_observed_conditions": [],
        "sampling_warnings": ["No incidence percentage was calculated."],
        "scientific_limitations": [DISCLAIMER],
    }
