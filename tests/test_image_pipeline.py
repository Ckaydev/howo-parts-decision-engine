import copy
import json
import unittest
from pathlib import Path

from howo_capture.image_pipeline import process_image_identification


class ImageIdentificationPipelineTests(unittest.TestCase):
    def setUp(self):
        fixture = Path(__file__).parents[1] / "examples" / "identify-image.json"
        self.payload = json.loads(fixture.read_text(encoding="utf-8"))

    def test_ocr_and_visual_evidence_routes_to_review(self):
        result = process_image_identification(self.payload)
        self.assertEqual(result["match"]["status"], "review_required")
        self.assertEqual(result["match"]["candidates"][0]["product_id"], "prd_rear_chamber")
        self.assertEqual(result["rows"]["image_evidence"][0]["product_id"], "")
        self.assertEqual(len(result["rows"]["review_queue"]), 1)
        self.assertEqual(
            result["rows"]["review_queue"][0]["proposed_product_id"],
            "prd_rear_chamber",
        )

    def test_explicit_confirmed_number_can_link_evidence(self):
        value = copy.deepcopy(self.payload)
        value["text_reference"]["confirmed_part_numbers"] = ["WG9000360700"]
        result = process_image_identification(value)
        self.assertEqual(result["match"]["status"], "matched")
        self.assertEqual(result["rows"]["image_evidence"][0]["product_id"], "prd_rear_chamber")
        self.assertEqual(result["rows"]["review_queue"], [])

    def test_retry_produces_same_rows(self):
        first = process_image_identification(self.payload)
        second = process_image_identification(self.payload)
        self.assertEqual(first["rows"], second["rows"])


if __name__ == "__main__":
    unittest.main()
