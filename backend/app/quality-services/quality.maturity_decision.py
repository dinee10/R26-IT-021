from typing import Any


def resolve_maturity_prediction(
    species: str,
    model_probabilities: dict[str, float],
    maturity_lookup,
    manual_support_service,
    manual_inputs: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {}
    high_threshold = float(config.get("maturity_high_confidence_threshold", 0.8))
    low_threshold = float(config.get("maturity_low_confidence_threshold", 0.45))
    agreement_threshold = float(
        config.get("manual_support_agreement_threshold", 0.67)
    )
    conflict_threshold = float(
        config.get("manual_support_conflict_threshold", 0.67)
    )
    minimum_manual_features = int(config.get("minimum_manual_evidence_features", 1))

    model_stage, confidence = _top_prediction(model_probabilities)
    maturity_info = maturity_lookup.get_maturity_info(species, model_stage)
    maturity_rows = maturity_lookup.get_all_maturity_stages(species)
    canonical_stage = (
        maturity_info.get("canonical_maturity_stage")
        or model_stage
    )
    manual_support = manual_support_service.evaluate_manual_maturity_support(
        species=species,
        manual_inputs=manual_inputs,
        maturity_rows=maturity_rows,
        config=config,
    )

    final_stage = model_stage
    final_canonical_stage = canonical_stage
    decision_status = "Model_Only"
    reason = "Model prediction is used as the maturity decision."

    if confidence >= high_threshold:
        if _manual_supports_stage(manual_support, model_stage, agreement_threshold):
            decision_status = "Supported_By_Manual_Evidence"
            reason = "Model confidence is high and manual evidence supports it."
    elif not manual_support["used"]:
        if confidence < low_threshold:
            final_stage = "Uncertain"
            final_canonical_stage = None
            decision_status = "Insufficient_Evidence"
            reason = "Model confidence is low and no manual evidence was supplied."
    elif manual_support["available_features"] < minimum_manual_features:
        final_stage = "Uncertain"
        final_canonical_stage = None
        decision_status = "Insufficient_Evidence"
        reason = "Too little comparable manual evidence is available."
    elif _manual_supports_stage(manual_support, model_stage, agreement_threshold):
        decision_status = "Supported_By_Manual_Evidence"
        reason = "Manual evidence supports the model maturity prediction."
    elif _manual_conflicts(manual_support, model_stage, conflict_threshold):
        final_stage = "Uncertain"
        final_canonical_stage = None
        decision_status = "Manual_Evidence_Conflicts"
        reason = "Model prediction and manual evidence do not strongly agree."
    elif confidence < low_threshold:
        final_stage = "Uncertain"
        final_canonical_stage = None
        decision_status = "Expert_Verification_Recommended"
        reason = "Model confidence is low and supporting evidence is not strong."

    final_info = (
        maturity_lookup.get_maturity_info(species, final_stage)
        if final_stage != "Uncertain"
        else {}
    )

    return {
        "model_prediction": {
            "stage": model_stage,
            "canonical_stage": canonical_stage,
            "confidence": round(confidence, 3),
            "probabilities": {
                stage: round(float(probability), 3)
                for stage, probability in model_probabilities.items()
            },
        },
        "manual_support": manual_support,
        "final_decision": {
            "stage": final_stage,
            "canonical_stage": final_canonical_stage,
            "decision_status": decision_status,
            "reason": reason,
        },
        "maturity_info": _public_maturity_info(final_info),
        "medicinal_suitability": _medicinal_suitability(final_info, decision_status),
    }


def not_assessed_result(species: str) -> dict[str, Any]:
    return {
        "model_prediction": None,
        "manual_support": None,
        "final_decision": {
            "stage": None,
            "canonical_stage": None,
            "decision_status": "Not_Assessed",
            "reason": "Maturity is not visually assessed for this species.",
        },
        "maturity_info": None,
        "medicinal_suitability": {
            "level": "Suitable",
            "display": "Visually suitable for medicinal use",
            "assessment": (
                f"{species.replace('_', ' ').title()} is visually suitable for "
                "medicinal use when the leaf is healthy. Expert verification is "
                "still recommended for non-visual safety factors."
            ),
            "evidence_strength": "",
        },
    }


def _top_prediction(probabilities: dict[str, float]) -> tuple[str, float]:
    if not probabilities:
        return "Uncertain", 0.0

    stage, probability = max(probabilities.items(), key=lambda item: item[1])
    return stage, float(probability)


def _manual_supports_stage(
    manual_support: dict[str, Any],
    stage: str,
    threshold: float,
) -> bool:
    stage_support = manual_support.get("stage_support", {}).get(stage)
    if not stage_support or stage_support.get("support_score") is None:
        return False

    return float(stage_support["support_score"]) >= threshold


def _manual_conflicts(
    manual_support: dict[str, Any],
    model_stage: str,
    threshold: float,
) -> bool:
    supporting_stage = manual_support.get("supporting_stage")
    support_score = manual_support.get("support_score")

    if supporting_stage in {None, model_stage} or support_score is None:
        return False

    return float(support_score) >= threshold


def _public_maturity_info(row: dict[str, Any]) -> dict[str, Any] | None:
    if not row:
        return None

    return {
        "found": row.get("found", False),
        "typical_color": row.get("typical_color", ""),
        "typical_texture": row.get("typical_texture", ""),
        "development_marker": row.get("development_marker", ""),
        "visual_characteristics": row.get("visual_characteristics", ""),
        "best_manual_cues": row.get("best_manual_cues", ""),
        "evidence_strength": row.get("evidence_strength", ""),
        "reference": row.get("reference", ""),
    }


def _medicinal_suitability(
    row: dict[str, Any],
    decision_status: str,
) -> dict[str, Any]:
    if decision_status in {
        "Manual_Evidence_Conflicts",
        "Insufficient_Evidence",
        "Expert_Verification_Recommended",
    }:
        return {
            "level": "Expert_Verification_Recommended",
            "display": "Expert verification recommended before medicinal use",
            "assessment": "Maturity evidence is not strong enough for a visual suitability decision.",
            "evidence_strength": "",
        }

    level = row.get("medicinal_suitability_level") or "Expert_Verification_Recommended"
    return {
        "level": level,
        "display": _display_suitability(level),
        "assessment": (
            row.get("medicinal_maturity_assessment")
            or "Expert verification recommended."
        ),
        "evidence_strength": row.get("medicinal_evidence_strength") or "",
    }


def _display_suitability(level: str) -> str:
    normalized = level.strip().lower().replace(" ", "_")
    labels = {
        "suitable": "Visually suitable for medicinal use",
        "conditionally_suitable": "Conditionally suitable for medicinal use",
        "low_suitability": "Low medicinal suitability",
        "not_recommended": "Not recommended for medicinal use",
        "expert_verification_recommended": (
            "Expert verification recommended before medicinal use"
        ),
    }
    return labels.get(normalized, "Expert verification recommended before medicinal use")
