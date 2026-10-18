import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cultivation.train_recommendation import FEATURE_COLUMNS, build_expanded_dataset, load_original_dataset


class RecommendationPipelineTests(unittest.TestCase):
    def test_original_dataset_has_expected_shape(self):
        df = load_original_dataset()
        self.assertGreater(len(df), 0)
        self.assertIn('plant_name', df.columns)
        self.assertGreater(df['plant_name'].nunique(), 10)

    def test_expanded_dataset_has_enough_rows_and_target(self):
        df = build_expanded_dataset()
        self.assertGreater(len(df), 100)
        self.assertIn('plant_name', df.columns)
        self.assertEqual(df['plant_name'].isna().sum(), 0)
        self.assertGreater(df['plant_name'].nunique(), 10)
        self.assertNotIn('sunlight', df.columns)
        self.assertNotIn('sunlight', FEATURE_COLUMNS)


if __name__ == '__main__':
    unittest.main()
