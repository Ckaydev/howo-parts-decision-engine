import json
import unittest
from pathlib import Path

from howo_capture.pipeline import process_capture


class PipelineTests(unittest.TestCase):
    def setUp(self):
        fixture = Path(__file__).parents[1] / "examples" / "process-known-part.json"
        self.payload = json.loads(fixture.read_text(encoding="utf-8"))

    def test_known_part_creates_append_rows(self):
        result = process_capture(self.payload)
        self.assertEqual(result["match"]["status"], "matched")
        self.assertEqual(len(result["rows"]["observations"]), 1)
        self.assertEqual(len(result["rows"]["part_numbers"]), 1)
        self.assertEqual(result["rows"]["review_queue"], [])
        self.assertEqual(result["capture"]["processing_status"], "structured")

    def test_retry_produces_same_ids(self):
        first = process_capture(self.payload)
        second = process_capture(self.payload)
        self.assertEqual(first["rows"], second["rows"])

    def test_empty_product_list_creates_idempotent_review_row(self):
        self.payload["products"] = []

        first = process_capture(self.payload)
        second = process_capture(self.payload)

        self.assertEqual(first["match"]["status"], "new_product_candidate")
        self.assertEqual(first["capture"]["processing_status"], "needs_review")
        self.assertEqual(first["rows"]["observations"], [])
        self.assertEqual(first["rows"]["part_numbers"], [])
        self.assertEqual(len(first["rows"]["review_queue"]), 1)
        self.assertEqual(
            first["rows"]["review_queue"][0]["review_id"],
            second["rows"]["review_queue"][0]["review_id"],
        )

    def test_ambiguous_identity_routes_to_review(self):
        self.payload["extraction"]["product_reference"] = {
            "mentioned_name": "front brake chambr",
            "mentioned_part_numbers": [],
        }
        result = process_capture(self.payload)
        self.assertEqual(result["match"]["status"], "review_required")
        self.assertEqual(result["rows"]["observations"], [])
        self.assertEqual(len(result["rows"]["review_queue"]), 1)
        self.assertEqual(result["capture"]["processing_status"], "needs_review")

    def test_voice_transcript_can_drive_extraction_and_matching(self):
        fixture = Path(__file__).parents[1] / "examples" / "process-voice-note.json"
        result = process_capture(json.loads(fixture.read_text(encoding="utf-8")))

        self.assertEqual(result["match"]["status"], "matched")
        self.assertEqual(result["match"]["reason"], "exact_part_number")
        self.assertEqual(result["capture"]["media_type"], "voice")
        self.assertIn("WG9000360600", result["capture"]["transcript"])
        self.assertEqual(len(result["rows"]["observations"]), 1)
        self.assertEqual(result["extraction_validation"]["status"], "passed")

    def test_unsupported_ai_identity_is_routed_to_review(self):
        self.payload["extraction"]["product_reference"]["mentioned_name"] = "HOWO"

        result = process_capture(self.payload)

        self.assertEqual(result["match"]["status"], "review_required")
        self.assertEqual(result["match"]["reason"], "extraction_evidence_failed")
        self.assertEqual(result["rows"]["observations"], [])
        self.assertEqual(result["extraction_validation"]["status"], "needs_review")
        self.assertEqual(
            result["extraction_validation"]["issues"][0]["code"],
            "unsupported_product_name",
        )

    def test_missing_part_number_claim_value_is_filled_from_supported_reference(self):
        self.payload["extraction"]["claims"] = [
            {
                "claim_type": "part_number",
                "claim_text": "The stated part number is WG9000360600.",
                "structured_value": None,
                "evidence_class": "user_reported",
                "confidence": 0.9,
                "variant_name": None,
            }
        ]

        result = process_capture(self.payload)

        self.assertEqual(result["match"]["status"], "matched")
        self.assertEqual(
            result["rows"]["observations"][0]["structured_value"],
            "WG9000360600",
        )


if __name__ == "__main__":
    unittest.main()
