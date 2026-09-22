import copy
import unittest

from howo_capture.models import ValidationError
from howo_capture.review import resolve_review


class ReviewResolutionTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "review_item": {
                "review_id": "rev_capture_1",
                "capture_id": "cap_1",
                "proposed_product_id": "prd_brake",
                "candidate_matches": "[]",
                "reason": "visual_match_requires_review",
                "questions_needed": "[]",
                "status": "open",
                "reviewed_at": "",
            },
            "decision": {
                "review_id": "rev_capture_1",
                "capture_id": "cap_1",
                "action": "link_existing",
                "product_id": "prd_brake",
                "identity_confidence": 0.95,
                "accept_image_evidence_ids": ["img_1"],
                "confirmed_part_numbers": [
                    {
                        "raw_part_number": "WG 9000-360700",
                        "number_type": "oem",
                        "verified_by_human": True,
                        "source_reference": "clear label photo img_1",
                    }
                ],
                "reviewer": "owner",
                "reviewed_at": "2026-09-21T10:00:00+01:00",
                "notes": "Label and mounting layout checked.",
            },
            "products": [
                {
                    "product_id": "prd_brake",
                    "canonical_name": "Rear brake chamber",
                    "identity_status": "confirmed",
                }
            ],
            "part_numbers": [],
            "image_evidence": [
                {
                    "image_evidence_id": "img_1",
                    "capture_id": "cap_1",
                    "product_id": "",
                    "review_status": "unreviewed",
                }
            ],
        }

    def test_existing_product_review_promotes_only_explicit_evidence(self):
        result = resolve_review(self.payload)
        self.assertEqual(result["rows"]["review_queue"][0]["status"], "resolved")
        self.assertEqual(
            result["rows"]["image_evidence"][0]["product_id"], "prd_brake"
        )
        self.assertEqual(
            result["rows"]["image_evidence"][0]["review_status"], "accepted"
        )
        self.assertEqual(result["rows"]["part_numbers"][0]["status"], "confirmed")
        self.assertEqual(
            result["rows"]["observations"][0]["evidence_class"],
            "observed",
        )

    def test_new_products_are_always_provisional(self):
        value = copy.deepcopy(self.payload)
        value["decision"] = {
            "review_id": "rev_capture_1",
            "capture_id": "cap_1",
            "action": "create_provisional",
            "canonical_name": "Market name brake valve",
            "identity_confidence": 0.7,
            "accept_image_evidence_ids": ["img_1"],
            "reviewer": "owner",
            "reviewed_at": "2026-09-21T10:00:00+01:00",
        }
        result = resolve_review(value)
        product = result["rows"]["products"][0]
        self.assertEqual(product["identity_status"], "provisional")
        self.assertEqual(
            result["rows"]["image_evidence"][0]["product_id"],
            product["product_id"],
        )

    def test_unverified_part_number_is_rejected(self):
        value = copy.deepcopy(self.payload)
        value["decision"]["confirmed_part_numbers"][0]["verified_by_human"] = False
        with self.assertRaisesRegex(ValidationError, "verified_by_human"):
            resolve_review(value)

    def test_part_number_conflict_is_rejected(self):
        value = copy.deepcopy(self.payload)
        value["products"].append(
            {
                "product_id": "prd_other",
                "canonical_name": "Other part",
                "identity_status": "confirmed",
            }
        )
        value["part_numbers"] = [
            {
                "part_number_id": "pn_other",
                "product_id": "prd_other",
                "raw_part_number": "WG9000360700",
                "status": "confirmed",
            }
        ]
        with self.assertRaisesRegex(ValidationError, "another product"):
            resolve_review(value)

    def test_reject_closes_review_without_creating_trusted_evidence(self):
        value = copy.deepcopy(self.payload)
        value["decision"] = {
            "review_id": "rev_capture_1",
            "capture_id": "cap_1",
            "action": "reject",
            "reject_image_evidence_ids": ["img_1"],
            "reviewer": "owner",
            "reviewed_at": "2026-09-21T10:00:00+01:00",
            "notes": "Wrong or unusable image.",
        }
        result = resolve_review(value)
        self.assertEqual(result["rows"]["review_queue"][0]["status"], "rejected")
        self.assertEqual(result["rows"]["products"], [])
        self.assertEqual(result["rows"]["part_numbers"], [])
        self.assertEqual(
            result["rows"]["image_evidence"][0]["review_status"], "rejected"
        )

    def test_retry_is_idempotent(self):
        self.assertEqual(resolve_review(self.payload), resolve_review(self.payload))

    def test_closed_review_cannot_be_resolved_again(self):
        value = copy.deepcopy(self.payload)
        value["review_item"]["status"] = "resolved"
        with self.assertRaisesRegex(ValidationError, "status open"):
            resolve_review(value)

    def test_image_must_belong_to_review_capture(self):
        value = copy.deepcopy(self.payload)
        value["image_evidence"][0]["capture_id"] = "cap_other"
        with self.assertRaisesRegex(ValidationError, "does not belong"):
            resolve_review(value)


if __name__ == "__main__":
    unittest.main()
