from typing import Any


UNKNOWN_VALUES = {"", "unknown", "null", "none", "not_applicable"}


def evaluate_manual_maturity_support(
    species: str,
    manual_inputs: dict[str, Any] | None,
    maturity_rows: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_inputs = _clean_manual_inputs(manual_inputs or {})
    weights = (config or {}).get("manual_feature_weights", {})
    stage_support: dict[str, Any] = {}

    for row in maturity_rows:
        stage = row.get("model_stage_label") or row.get("canonical_maturity_stage")
        if not stage:
            continue

        compared_weight = 0.0
        matched_weight = 0.0
        evidence: list[str] = []

        for feature_name, value in clean_inputs.items():
            weight = float(weights.get(feature_name, 1.0))
            comparison = _compare_feature(feature_name, value, row)

            if comparison is None:
                continue

            compared_weight += weight
            if comparison["matched"]:
                matched_weight += weight
            evidence.append(comparison["message"])

        support_score = (
            matched_weight / compared_weight
            if compared_weight > 0
            else None
        )
        compared_features = len(evidence)
        matched_features = sum(
            1 for message in evidence
            if "consistent" in message.lower() or "within" in message.lower()
        )

        stage_support[stage] = {
            "matched_features": matched_features,
            "compared_features": compared_features,
            "support_score": support_score,
            "evidence": evidence,
        }

    best_stage = None
    best_support = None
    comparable = [
        (stage, support)
        for stage, support in stage_support.items()
        if support["support_score"] is not None
    ]
    if comparable:
        best_stage, best_support = max(
            comparable,
            key=lambda item: item[1]["support_score"],
        )

    return {
        "used": bool(clean_inputs),
        "available_features": len(clean_inputs),
        "supporting_stage": best_stage,
        "support_score": (
            None if best_support is None else best_support["support_score"]
        ),
        "evidence": [] if best_support is None else best_support["evidence"],
        "stage_support": stage_support,
    }


def _clean_manual_inputs(manual_inputs: dict[str, Any]) -> dict[str, Any]:
    clean_inputs: dict[str, Any] = {}

    for key, value in manual_inputs.items():
        if value is None:
            continue

        if isinstance(value, str) and value.strip().lower() in UNKNOWN_VALUES:
            continue

        if key in {"leaf_length_cm", "leaf_width_cm"}:
            try:
                clean_inputs[key] = float(value)
            except (TypeError, ValueError):
                continue
        else:
            clean_inputs[key] = str(value).strip()

    return clean_inputs


def _compare_feature(
    feature_name: str,
    value: Any,
    row: dict[str, Any],
) -> dict[str, Any] | None:
    stage = row.get("model_stage_label") or "this stage"

    if feature_name == "leaf_length_cm":
        return _compare_range(
            value,
            row.get("leaf_length_min_cm"),
            row.get("leaf_length_max_cm"),
            f"Leaf length {value:g} cm is within the {stage} reference range.",
            f"Leaf length {value:g} cm is outside the {stage} reference range.",
        )

    if feature_name == "leaf_width_cm":
        return _compare_range(
            value,
            row.get("leaf_width_min_cm"),
            row.get("leaf_width_max_cm"),
            f"Leaf width {value:g} cm is within the {stage} reference range.",
            f"Leaf width {value:g} cm is outside the {stage} reference range.",
        )

    if feature_name == "leaf_texture":
        return _compare_text(
            value,
            row.get("typical_texture", ""),
            f"Leaf texture is consistent with the {stage} reference.",
            f"Leaf texture does not clearly match the {stage} reference.",
        )

    if feature_name == "leaf_edge":
        return _compare_text(
            value,
            row.get("typical_edge", ""),
            f"Leaf edge is consistent with the {stage} reference.",
            f"Leaf edge does not clearly match the {stage} reference.",
        )

    if feature_name == "discoloration":
        return _compare_text(
            value,
            row.get("typical_color", ""),
            f"Leaf color information is consistent with the {stage} reference.",
            f"Leaf color information does not clearly match the {stage} reference.",
        )

    if feature_name in {"surface_spots", "holes"}:
        reference_text = " ".join([
            row.get("surface_character", ""),
            row.get("visual_characteristics", ""),
        ])
        return _compare_text(
            value,
            reference_text,
            f"{_display_feature(feature_name)} is consistent with the {stage} reference.",
            f"{_display_feature(feature_name)} does not clearly match the {stage} reference.",
        )

    return None


def _compare_range(
    value: float,
    min_value: float | None,
    max_value: float | None,
    matched_message: str,
    unmatched_message: str,
) -> dict[str, Any] | None:
    if min_value is None or max_value is None:
        return None

    matched = min_value <= value <= max_value
    return {
        "matched": matched,
        "message": matched_message if matched else unmatched_message,
    }


def _compare_text(
    value: str,
    reference_text: str,
    matched_message: str,
    unmatched_message: str,
) -> dict[str, Any] | None:
    if not reference_text.strip():
        return None

    value_key = value.strip().lower().replace("_", " ")
    reference_key = reference_text.strip().lower().replace("_", " ")

    if value_key in UNKNOWN_VALUES:
        return None

    matched = value_key in reference_key
    return {
        "matched": matched,
        "message": matched_message if matched else unmatched_message,
    }


def _display_feature(value: str) -> str:
    return value.replace("_", " ").title()
