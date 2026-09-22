import unittest

from howo_capture.identification import identify_from_payload
from howo_capture.models import ValidationError


PRODUCTS = [
    {
        "product_id": "prd_front",
        "canonical_name": "Front brake chamber",
        "primary_part_number": "WG9000360600",
        "aliases": "front brake actuator",
        "identity_status": "confirmed",
    },
    {
        "product_id": "prd_rear",
        "canonical_name": "Rear brake chamber",
        "primary_part_number": "WG9000360700",
        "aliases": "rear brake actuator",
        "identity_status": "confirmed",
    },
]

PROFILES = [
    {
        "product_id": "prd_front",
        "label_terms": ["front service chamber"],
        "visual_features": ["two mounting studs", "short push rod"],
        "fitment_terms": ["front axle"],
        "observation_ids": ["obs_front_1"],
    },
    {
        "product_id": "prd_rear",
        "label_terms": ["rear spring brake"],
        "visual_features": ["four mounting studs", "long push rod"],
        "fitment_terms": ["rear axle"],
        "observation_ids": ["obs_rear_1"],
    },
]


class IdentificationTests(unittest.TestCase):
    def test_confirmed_exact_part_number_overrides_conflicting_visual_clues(self):
        result = identify_from_payload(
            {
                "query": {
                    "confirmed_part_numbers": ["WG-9000 360600"],
                    "visual_features": ["four mounting studs", "long push rod"],
                },
                "products": PRODUCTS,
                "evidence_profiles": PROFILES,
            }
        )
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["product_id"], "prd_front")
        self.assertEqual(result["reason"], "exact_part_number")

    def test_ocr_observed_part_number_ranks_but_does_not_auto_match(self):
        result = identify_from_payload(
            {
                "query": {"observed_part_numbers": ["WG-9000 360600"]},
                "products": PRODUCTS,
                "evidence_profiles": PROFILES,
            }
        )
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["candidates"][0]["product_id"], "prd_front")
        self.assertIn("exact_observed_part_number", result["candidates"][0]["signals"])

    def test_visual_and_fitment_signals_rank_but_do_not_auto_match(self):
        result = identify_from_payload(
            {
                "query": {
                    "mentioned_name": "brake chamber",
                    "visual_features": ["four mounting studs", "long push rod"],
                    "fitment_terms": ["rear axle"],
                },
                "products": PRODUCTS,
                "evidence_profiles": PROFILES,
            }
        )
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["candidates"][0]["product_id"], "prd_rear")
        self.assertIn("obs_rear_1", result["candidates"][0]["observation_ids"])

    def test_tied_visual_profiles_stay_ambiguous_and_deterministic(self):
        profiles = [
            {"product_id": "prd_front", "visual_features": ["round black housing"]},
            {"product_id": "prd_rear", "visual_features": ["round black housing"]},
        ]
        result = identify_from_payload(
            {
                "query": {"visual_features": ["round black housing"]},
                "products": PRODUCTS,
                "evidence_profiles": profiles,
            }
        )
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(
            [candidate["product_id"] for candidate in result["candidates"]],
            ["prd_front", "prd_rear"],
        )

    def test_profile_for_unknown_product_is_rejected(self):
        with self.assertRaises(ValidationError):
            identify_from_payload(
                {
                    "query": {"visual_features": ["round black housing"]},
                    "products": PRODUCTS,
                    "evidence_profiles": [
                        {"product_id": "prd_missing", "visual_features": ["round"]}
                    ],
                }
            )

    def test_confirmed_number_does_not_auto_match_a_provisional_product(self):
        provisional = [{**PRODUCTS[0], "identity_status": "provisional"}]
        result = identify_from_payload(
            {
                "query": {"confirmed_part_numbers": ["WG9000360600"]},
                "products": provisional,
                "evidence_profiles": [],
            }
        )
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["reason"], "part_number_matches_provisional_product")


if __name__ == "__main__":
    unittest.main()
