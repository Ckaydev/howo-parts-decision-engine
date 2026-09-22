import unittest

from howo_capture.matching import match_product
from howo_capture.models import ExtractionResult, ProductRecord


PRODUCTS = [
    ProductRecord(
        product_id="prd_1",
        canonical_name="Front brake chamber",
        primary_part_number="WG9000360600",
        aliases=("front brake actuator",),
        identity_status="confirmed",
    ),
    ProductRecord(
        product_id="prd_2",
        canonical_name="Rear brake chamber",
        primary_part_number="WG9000360700",
        identity_status="confirmed",
    ),
]


def extraction(name=None, part_numbers=()):
    return ExtractionResult.from_mapping(
        {
            "summary": "test",
            "product_reference": {
                "mentioned_name": name,
                "mentioned_part_numbers": list(part_numbers),
            },
            "claims": [],
            "follow_up_questions": [],
        }
    )


class MatchingTests(unittest.TestCase):
    def test_exact_part_number_is_strongest_match(self):
        decision = match_product(
            extraction("wrong informal name", ("WG-9000 360600",)), PRODUCTS
        )
        self.assertEqual(decision.status, "matched")
        self.assertEqual(decision.product_id, "prd_1")
        self.assertEqual(decision.reason, "exact_part_number")

    def test_exact_name_without_part_number_can_match(self):
        decision = match_product(extraction("Front Brake Chamber"), PRODUCTS)
        self.assertEqual(decision.status, "matched")
        self.assertEqual(decision.product_id, "prd_1")

    def test_unrecognized_part_number_for_known_name_requires_review(self):
        decision = match_product(
            extraction("Front brake chamber", ("UNCONFIRMED-01",)), PRODUCTS
        )
        self.assertEqual(decision.status, "review_required")
        self.assertEqual(decision.reason, "unrecognized_part_number_for_known_name")

    def test_fuzzy_name_never_auto_matches(self):
        decision = match_product(extraction("front brake chambr"), PRODUCTS)
        self.assertEqual(decision.status, "review_required")
        self.assertEqual(decision.reason, "fuzzy_name_match")

    def test_unknown_product_becomes_candidate(self):
        decision = match_product(extraction("turbo encabulator"), PRODUCTS)
        self.assertEqual(decision.status, "new_product_candidate")

    def test_exact_name_for_provisional_product_requires_review(self):
        product = ProductRecord(
            product_id="prd_provisional",
            canonical_name="Timing washer",
            identity_status="provisional",
        )
        decision = match_product(extraction("Timing washer"), [product])
        self.assertEqual(decision.status, "review_required")
        self.assertEqual(decision.reason, "name_matches_provisional_product")


if __name__ == "__main__":
    unittest.main()
