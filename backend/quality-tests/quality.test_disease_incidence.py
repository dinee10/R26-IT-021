import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "app" / "quality-services"


def load_service(module_name, file_name):
    spec = importlib.util.spec_from_file_location(module_name, SERVICES / file_name)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


incidence = load_service("quality_disease_incidence_test", "quality.disease_incidence.py")
condition_classifier = load_service("quality_condition_classifier_incidence_test", "quality.condition_classifier.py")


class DiseaseIncidenceRuleTests(unittest.TestCase):
    def test_revised_csv_schema_and_references_load(self):
        rows = incidence.load_rules()
        references = incidence.load_references()
        self.assertEqual(len(rows), 145)
        self.assertTrue(incidence.REQUIRED_RULE_COLUMNS.issubset(rows[0]))
        self.assertGreater(len(references), 0)

    def test_all_exact_boundaries_use_inclusive_and_exclusive_flags(self):
        expected = {
            0: "None_Detected",
            25: "Low",
            50: "Moderate",
            75: "High",
            100: "Very_High",
        }
        for percentage, label in expected.items():
            with self.subTest(percentage=percentage):
                rule = incidence.find_rule("betel", "Leaf_Rot", percentage)
                self.assertIsNotNone(rule)
                self.assertEqual(rule["incidence_label"], label)

    def test_model_label_coverage_reports_only_murraya_fungus(self):
        labels_path = ROOT / "ml" / "quality.condition_classifier.efficientnetv2_b0.labels.json"
        heads = json.loads(labels_path.read_text(encoding="utf-8"))
        coverage = incidence.rule_coverage(heads)
        self.assertEqual(coverage["expected_non_healthy_classes"], 30)
        self.assertEqual(coverage["covered_classes"], 29)
        self.assertEqual(
            coverage["missing"],
            [{"species": "murraya_koenigii", "condition_class": "fungus"}],
        )

    def test_missing_rules_file_fails_instead_of_fabricating_data(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = str(Path(folder) / "missing.csv")
            with self.assertRaises(incidence.IncidenceDataError):
                incidence.load_rules(missing)

    def test_missing_model_artifact_does_not_create_mock_prediction(self):
        config = {
            "active_model": "test",
            "models": {"test": {"path": "definitely-missing.keras", "display_name": "Test"}},
        }
        prediction = condition_classifier._predict(
            preprocessed=None,
            image_bytes=b"sample",
            species_id="neem",
            config=config,
        )
        self.assertEqual(prediction["reason"], "MODEL_NOT_AVAILABLE")
        self.assertNotIn("mode", prediction)


class DiseaseIncidenceAssessmentTests(unittest.TestCase):
    @staticmethod
    def _valid(_image):
        return {"valid": True}

    @staticmethod
    def _plant(image):
        if image == b"mismatch":
            return {"accepted": True, "species": "Betel", "confidence": .99}
        if image == b"unknown":
            return {"accepted": False, "species": "Unknown", "reason": "UNKNOWN_PLANT"}
        return {"accepted": True, "species": "Neem", "confidence": .99}

    @staticmethod
    def _condition(image, _plant):
        mapping = {
            b"initial": ("Spot", .98),
            b"spot": ("Spot", .91),
            b"healthy": ("Healthy", .96),
            b"yellow": ("Yellow", .93),
            b"low": ("Spot", .44),
            b"mismatch": ("Spot", .99),
        }
        name, confidence = mapping.get(image, ("Healthy", .95))
        accepted = confidence >= .8
        return {
            "accepted": accepted,
            "status": "healthy" if name == "Healthy" else "diseased",
            "class": name,
            "display_name": name.replace("_", " "),
            "confidence": confidence,
            **({"reason": "LOW_CONDITION_CONFIDENCE"} if not accepted else {}),
        }

    @staticmethod
    def _lookup(species, condition):
        return {"found": True, "species": species, "disease_name": condition}

    def _assess(self, values, validator=None):
        samples = [{"bytes": value, "filename": f"{index}.jpg"} for index, value in enumerate(values)]
        return incidence.assess_samples(
            samples,
            validator or self._valid,
            self._plant,
            self._condition,
            self._lookup,
        )

    def test_independent_mixed_predictions_and_denominator_exclusions(self):
        result = self._assess([b"initial", b"spot", b"healthy", b"yellow", b"low", b"mismatch"])
        self.assertTrue(result["accepted"])
        self.assertEqual(result["total_submitted_images"], 6)
        self.assertEqual(result["total_accepted_images"], 4)
        self.assertEqual(result["healthy_sample_count"], 1)
        self.assertEqual(result["primary_condition_verification"]["matching_sample_count"], 2)
        self.assertEqual(result["primary_condition_verification"]["calculated_percentage"], 50.0)
        self.assertEqual(result["primary_condition_verification"]["incidence_level"], "Moderate")
        self.assertEqual({item["exclusion_reason"] for item in result["excluded_images"]}, {"LOW_CONDITION_CONFIDENCE", "SPECIES_MISMATCH"})
        self.assertEqual(result["additional_observed_conditions"][0]["condition_name"], "Yellow")

    def test_duplicate_is_excluded_and_not_counted_as_healthy(self):
        result = self._assess([b"initial", b"healthy", b"healthy"])
        self.assertEqual(result["total_accepted_images"], 2)
        self.assertEqual(result["healthy_sample_count"], 1)
        self.assertEqual(result["excluded_images"][0]["exclusion_reason"], "DUPLICATE_SAMPLE")

    def test_invalid_or_blurred_initial_returns_no_percentages(self):
        def invalid(_image):
            return {"valid": False, "reason": "IMAGE_TOO_BLURRY"}
        result = self._assess([b"initial"], validator=invalid)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["total_accepted_images"], 0)
        self.assertEqual(result["per_condition_results"], [])

    def test_initial_healthy_does_not_start_disease_verification(self):
        result = self._assess([b"healthy"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "INITIAL_CONDITION_HEALTHY")

    def test_missing_condition_mapping_is_reported_without_treatment(self):
        def curry(_image):
            return {"accepted": True, "species": "Murraya Koenigii", "confidence": .99}
        def fungus(_image, _plant):
            return {"accepted": True, "status": "diseased", "class": "Fungus", "display_name": "Fungus", "confidence": .98}
        result = incidence.assess_samples(
            [{"bytes": b"fungus", "filename": "fungus.jpg"}],
            self._valid,
            curry,
            fungus,
            self._lookup,
        )
        summary = result["primary_condition_verification"]
        self.assertEqual(summary["rule_availability"], "rules_unavailable")
        self.assertIn("No condition-specific treatment", summary["recommended_care"])

    def test_noninfectious_category_and_references_are_preserved(self):
        def basil(_image):
            return {"accepted": True, "species": "Holy Basil", "confidence": .99}
        def pigmentation(_image, _plant):
            return {"accepted": True, "status": "diseased", "class": "Anthocyanin_Pigmentation", "display_name": "Anthocyanin Pigmentation", "confidence": .98}
        result = incidence.assess_samples(
            [{"bytes": b"pigment", "filename": "pigment.jpg"}],
            self._valid,
            basil,
            pigmentation,
            self._lookup,
        )
        summary = result["primary_condition_verification"]
        self.assertNotEqual(summary["condition_category"], "infectious_disease")
        self.assertGreater(len(summary["references"]), 0)


if __name__ == "__main__":
    unittest.main()
