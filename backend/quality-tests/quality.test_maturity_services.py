import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "app" / "quality-services"


def load_service(module_name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SERVICES / file_name)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


maturity_lookup = load_service("quality_maturity_lookup_test", "quality.maturity_lookup.py")
manual_support = load_service(
    "quality_manual_maturity_support_test",
    "quality.manual_maturity_support.py",
)
maturity_decision = load_service(
    "quality_maturity_decision_test",
    "quality.maturity_decision.py",
)
maturity_classifier = load_service(
    "quality_maturity_classifier_test",
    "quality.maturity_classifier.py",
)


class MaturityServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "quality.maturity.csv"
        self.csv_path.write_text(
            "\n".join([
                "species,model_stage_label,canonical_maturity_stage,stage_order,"
                "supported_for_model3,leaf_length_min_cm,leaf_length_max_cm,"
                "leaf_width_min_cm,leaf_width_max_cm,numeric_size_evidence,"
                "literature_size_reference,relative_leaf_size,typical_texture,"
                "typical_edge,typical_color,surface_character,development_marker,"
                "visual_characteristics,best_manual_cues,size_support_strength,"
                "texture_support_strength,color_support_strength,decision_support_rule,"
                "evidence_strength,local_calibration_required,medicinal_suitability_level,"
                "medicinal_maturity_assessment,medicinal_evidence_strength,reference",
                "neem,Young,Young,1,true,2,5,1,3,,,,Smooth,Serrated,Light green,,"
                "new foliage,Young soft leaves,Length; color,Medium,Medium,Medium,,"
                "Medium,true,Low_Suitability,Not yet optimal for medicinal use,Medium,ref",
                "neem,Mature,Mature,2,true,6,12,3,7,,,,Rough,Serrated,Dark green,,"
                "fully expanded foliage,Mature expanded leaves,Length; texture,Medium,"
                "Medium,Medium,,High,true,Suitable,Visually suitable for medicinal use,"
                "High,ref",
                "murraya_koenigii,Young,Young,1,true,1,3,0.5,1.5,,,,Smooth,Smooth,"
                "Light green,,new leaflet,Young curry leaflets,Length,Medium,Medium,"
                "Medium,,Medium,true,Low_Suitability,Not yet optimal,Medium,ref",
                "murraya_koenigii,Developing,Developing,2,true,3.1,5,1.6,2.5,,,,"
                "Smooth,Smooth,Green,,expanding leaflet,Developing curry leaflets,"
                "Length,Medium,Medium,Medium,,Medium,true,Conditionally_Suitable,"
                "Conditionally suitable for medicinal use,Medium,ref",
                "murraya_koenigii,Mature,Mature,3,true,5.1,8,2.6,4,,,,Rough,Smooth,"
                "Dark green,,fully expanded leaflet,Mature curry leaflets,Length,"
                "Medium,Medium,Medium,,High,true,Suitable,Visually suitable,High,ref",
            ]),
            encoding="utf-8",
        )
        os.environ["QUALITY_MATURITY_KNOWLEDGE_CSV"] = str(self.csv_path)
        maturity_lookup._load_rows.cache_clear()

    def tearDown(self):
        maturity_lookup._load_rows.cache_clear()
        os.environ.pop("QUALITY_MATURITY_KNOWLEDGE_CSV", None)
        self.temp_dir.cleanup()

    def test_missing_csv_row_returns_safe_fallback(self):
        info = maturity_lookup.get_maturity_info("neem", "UnknownStage")

        self.assertFalse(info["found"])
        self.assertEqual(
            info["medicinal_suitability_level"],
            "Expert_Verification_Recommended",
        )

    def test_only_leaf_length_contributes_when_other_inputs_unknown(self):
        rows = maturity_lookup.get_all_maturity_stages("neem")
        support = manual_support.evaluate_manual_maturity_support(
            "neem",
            {
                "leaf_length_cm": 7.2,
                "leaf_texture": "Unknown",
                "leaf_width_cm": None,
            },
            rows,
            {"manual_feature_weights": {"leaf_length_cm": 1}},
        )

        self.assertTrue(support["used"])
        self.assertEqual(support["available_features"], 1)
        self.assertEqual(support["supporting_stage"], "Mature")
        self.assertEqual(support["support_score"], 1.0)

    def test_missing_numeric_range_does_not_create_comparison(self):
        rows = [{
            "model_stage_label": "Young",
            "leaf_length_min_cm": None,
            "leaf_length_max_cm": None,
        }]
        support = manual_support.evaluate_manual_maturity_support(
            "neem",
            {"leaf_length_cm": 7.2},
            rows,
            {},
        )

        self.assertEqual(support["stage_support"]["Young"]["compared_features"], 0)
        self.assertIsNone(support["stage_support"]["Young"]["support_score"])

    def test_manual_inputs_all_unknown_are_not_used(self):
        rows = maturity_lookup.get_all_maturity_stages("neem")
        support = manual_support.evaluate_manual_maturity_support(
            "neem",
            {
                "leaf_texture": "Unknown",
                "leaf_edge": "Unknown",
                "holes": "Unknown",
                "leaf_length_cm": None,
            },
            rows,
            {},
        )

        self.assertFalse(support["used"])
        self.assertEqual(support["available_features"], 0)

    def test_young_model_label_preserves_young_canonical_stage(self):
        result = maturity_decision.resolve_maturity_prediction(
            species="neem",
            model_probabilities={"Young": 0.9, "Mature": 0.1},
            maturity_lookup=maturity_lookup,
            manual_support_service=manual_support,
            config={"maturity_high_confidence_threshold": 0.8},
        )

        self.assertEqual(result["model_prediction"]["stage"], "Young")
        self.assertEqual(result["model_prediction"]["canonical_stage"], "Young")
        self.assertEqual(result["final_decision"]["canonical_stage"], "Young")

    def test_low_confidence_with_supporting_manual_inputs(self):
        result = maturity_decision.resolve_maturity_prediction(
            species="neem",
            model_probabilities={"Young": 0.35, "Mature": 0.65},
            maturity_lookup=maturity_lookup,
            manual_support_service=manual_support,
            manual_inputs={"leaf_length_cm": 7.2},
            config={
                "maturity_high_confidence_threshold": 0.8,
                "maturity_low_confidence_threshold": 0.45,
                "manual_support_agreement_threshold": 0.67,
                "manual_support_conflict_threshold": 0.67,
                "minimum_manual_evidence_features": 1,
            },
        )

        self.assertEqual(
            result["final_decision"]["decision_status"],
            "Supported_By_Manual_Evidence",
        )
        self.assertEqual(result["medicinal_suitability"]["level"], "Suitable")

    def test_medicinal_suitability_is_returned_for_resolved_maturity(self):
        result = maturity_decision.resolve_maturity_prediction(
            species="neem",
            model_probabilities={"Young": 0.1, "Mature": 0.9},
            maturity_lookup=maturity_lookup,
            manual_support_service=manual_support,
            config={"maturity_high_confidence_threshold": 0.8},
        )

        self.assertEqual(
            result["medicinal_suitability"]["display"],
            "Visually suitable for medicinal use",
        )
        self.assertEqual(result["medicinal_suitability"]["evidence_strength"], "High")

    def test_low_confidence_with_conflicting_manual_inputs(self):
        result = maturity_decision.resolve_maturity_prediction(
            species="neem",
            model_probabilities={"Young": 0.42, "Mature": 0.58},
            maturity_lookup=maturity_lookup,
            manual_support_service=manual_support,
            manual_inputs={"leaf_length_cm": 3.0},
            config={
                "maturity_high_confidence_threshold": 0.8,
                "maturity_low_confidence_threshold": 0.45,
                "manual_support_agreement_threshold": 0.67,
                "manual_support_conflict_threshold": 0.67,
                "minimum_manual_evidence_features": 1,
            },
        )

        self.assertEqual(result["final_decision"]["stage"], "Uncertain")
        self.assertEqual(
            result["final_decision"]["decision_status"],
            "Manual_Evidence_Conflicts",
        )

    def test_murraya_three_stages_are_supported(self):
        rows = maturity_lookup.get_all_maturity_stages("murraya_koenigii")

        self.assertEqual(
            [row["model_stage_label"] for row in rows],
            ["Young", "Developing", "Mature"],
        )

    def test_low_confidence_without_manual_evidence_is_uncertain(self):
        result = maturity_decision.resolve_maturity_prediction(
            species="neem",
            model_probabilities={"Young": 0.56, "Mature": 0.44},
            maturity_lookup=maturity_lookup,
            manual_support_service=manual_support,
            manual_inputs={},
            config={
                "maturity_high_confidence_threshold": 0.8,
                "maturity_low_confidence_threshold": 0.6,
            },
        )

        self.assertEqual(result["final_decision"]["stage"], "Uncertain")
        self.assertEqual(
            result["medicinal_suitability"]["level"],
            "Expert_Verification_Recommended",
        )

    def test_holy_basil_not_assessed_result_has_no_stage(self):
        result = maturity_decision.not_assessed_result("holy_basil")

        self.assertIsNone(result["final_decision"]["stage"])
        self.assertEqual(
            result["medicinal_suitability"]["display"],
            "Visually suitable for medicinal use",
        )

    def test_not_assessed_result_uses_no_user_facing_maturity_value(self):
        result = maturity_decision.not_assessed_result("holy_basil")

        hidden_values = {None, "Not_Assessed", "Unknown", "null"}
        self.assertIn(result["final_decision"]["stage"], hidden_values)
        self.assertIsNone(result["model_prediction"])

    def test_diseased_neem_skips_model3(self):
        result = maturity_classifier.assess_maturity_from_multiple_images(
            image_bytes_list=[self._image_bytes()],
            plant_result={"species": "Neem", "accepted": True},
            condition_result={"condition": {"status": "diseased"}},
            maturity_lookup=maturity_lookup,
            maturity_decision=maturity_decision,
            manual_support_service=manual_support,
        )

        self.assertIsNone(result)

    def test_holy_basil_healthy_skips_maturity_section(self):
        result = maturity_classifier.assess_maturity_from_multiple_images(
            image_bytes_list=[self._image_bytes()],
            plant_result={"species": "Holy Basil", "accepted": True},
            condition_result={"condition": {"status": "healthy"}},
            maturity_lookup=maturity_lookup,
            maturity_decision=maturity_decision,
            manual_support_service=manual_support,
        )

        self.assertIsNone(result["final_decision"]["stage"])
        self.assertEqual(
            result["final_decision"]["decision_status"],
            "Not_Assessed",
        )

    def test_healthy_neem_runs_model3(self):
        result = maturity_classifier.assess_maturity_from_multiple_images(
            image_bytes_list=[self._image_bytes()],
            plant_result={"species": "Neem", "accepted": True},
            condition_result={"condition": {"status": "healthy"}},
            maturity_lookup=maturity_lookup,
            maturity_decision=maturity_decision,
            manual_support_service=manual_support,
        )

        self.assertIsNotNone(result["model_prediction"])
        self.assertIn(
            result["model_prediction"]["stage"],
            {"Young", "Mature"},
        )

    def _image_bytes(self):
        image = np.full((64, 64, 3), 128, dtype=np.uint8)
        success, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(success)
        return encoded.tobytes()


if __name__ == "__main__":
    unittest.main()

