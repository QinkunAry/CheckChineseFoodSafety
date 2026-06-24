import unittest

from food_safety_watch.classification import classify_reasons
from food_safety_watch.models import stable_id
from food_safety_watch.fda import food_category, normalize_date


class ClassificationTests(unittest.TestCase):
    def test_multiple_tags_are_preserved(self) -> None:
        tags = classify_reasons(["Undeclared allergen and misleading label"])
        self.assertIn("allergen", tags)
        self.assertIn("labeling", tags)

    def test_misleading_does_not_match_lead(self) -> None:
        tags = classify_reasons(["The labeling appears to be false and misleading."])
        self.assertNotIn("chemical", tags)

    def test_unknown_reason_is_explicit(self) -> None:
        self.assertEqual(classify_reasons(["Unmapped reason"]), ["other_or_unclassified"])

    def test_cfs_microbiological_terms_are_classified(self) -> None:
        tags = classify_reasons(["Bacillus cereus and coliform bacteria detected."])
        self.assertIn("microbiological", tags)

    def test_stable_id_is_deterministic(self) -> None:
        self.assertEqual(stable_id("source", "record"), stable_id("source", "record"))

    def test_fda_food_scope_excludes_devices(self) -> None:
        self.assertEqual(food_category("16ABC"), "seafood")
        self.assertIsNone(food_category("86HQY"))

    def test_fda_date_is_normalized(self) -> None:
        self.assertEqual(normalize_date("06-Jan-26"), "2026-01-06")


if __name__ == "__main__":
    unittest.main()
