import unittest

from howo_capture.models import ValidationError
from howo_capture.visual import process_visual_evidence


def payload():
    return {
        "capture_id": "cap_1",
        "attachment_id": "att_1",
        "captured_at": "2026-09-09T10:15:00+01:00",
        "visual_extraction": {
            "summary": "Four studs and one visible label.",
            "image_quality": "clear",
            "view_type": "full_item",
            "observed_part_numbers": [
                {"raw_text": "WG9000360700", "region": "label", "confidence": 0.96}
            ],
            "label_texts": [
                {"raw_text": "SINOTRUK", "region": "label", "confidence": 0.91}
            ],
            "visual_features": [
                {
                    "feature_type": "mounting",
                    "feature_name": "mounting studs",
                    "feature_value": "4",
                    "units": None,
                    "confidence": 0.93,
                }
            ],
            "fitment_terms": [],
            "questions_needed": [],
        },
    }


class VisualEvidenceTests(unittest.TestCase):
    def test_ocr_number_remains_observed_not_confirmed(self):
        result = process_visual_evidence(payload())
        query = result["identification_query"]
        self.assertEqual(query["confirmed_part_numbers"], [])
        self.assertEqual(query["observed_part_numbers"], ["WG9000360700"])
        self.assertEqual(result["rows"]["image_evidence"][0]["review_status"], "unreviewed")
        self.assertEqual(result["rows"]["visual_features"][0]["product_id"], "")

    def test_ids_are_replay_safe(self):
        first = process_visual_evidence(payload())
        second = process_visual_evidence(payload())
        self.assertEqual(first["rows"], second["rows"])

    def test_insufficient_image_requests_clearer_photo(self):
        value = payload()
        value["visual_extraction"]["image_quality"] = "insufficient"
        result = process_visual_evidence(value)
        self.assertEqual(
            result["questions_needed"],
            ["Send a clearer full-item and label photograph."],
        )

    def test_invalid_feature_type_is_rejected(self):
        value = payload()
        value["visual_extraction"]["visual_features"][0]["feature_type"] = "guess"
        with self.assertRaises(ValidationError):
            process_visual_evidence(value)


if __name__ == "__main__":
    unittest.main()
