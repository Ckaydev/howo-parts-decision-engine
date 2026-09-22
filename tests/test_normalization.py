import unittest

from howo_capture.normalization import normalize_name, normalize_part_number, stable_id


class NormalizationTests(unittest.TestCase):
    def test_part_number_removes_formatting_for_comparison(self):
        self.assertEqual(normalize_part_number(" wg-9000 360600 "), "WG9000360600")

    def test_name_normalization_preserves_words(self):
        self.assertEqual(normalize_name("  Front-Brake Chamber! "), "front brake chamber")

    def test_stable_id_is_repeatable(self):
        self.assertEqual(stable_id("obs", "a", 1), stable_id("obs", "a", 1))
        self.assertNotEqual(stable_id("obs", "a", 1), stable_id("obs", "a", 2))


if __name__ == "__main__":
    unittest.main()
