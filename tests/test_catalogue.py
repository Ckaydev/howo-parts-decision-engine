import unittest

from howo_capture.catalogue import build_catalogue_context


class CatalogueContextTests(unittest.TestCase):
    def test_only_reviewed_evidence_enters_matching_profiles(self):
        result = build_catalogue_context(
            {
                "products": [
                    {
                        "product_id": "prd_rear",
                        "canonical_name": "Rear brake chamber",
                        "identity_status": "confirmed",
                    }
                ],
                "part_numbers": [
                    {
                        "part_number_id": "pn_ok",
                        "product_id": "prd_rear",
                        "raw_part_number": "WG9000360700",
                        "status": "confirmed",
                    },
                    {
                        "part_number_id": "pn_raw",
                        "product_id": "prd_rear",
                        "raw_part_number": "UNREVIEWED-1",
                        "status": "unreviewed",
                    },
                ],
                "image_evidence": [
                    {
                        "image_evidence_id": "img_ok",
                        "product_id": "prd_rear",
                        "visible_label_text": "rear spring brake | SINOTRUK",
                        "review_status": "accepted",
                        "observation_id": "obs_img",
                    },
                    {
                        "image_evidence_id": "img_raw",
                        "product_id": "prd_rear",
                        "visible_label_text": "must not be trusted",
                        "review_status": "unreviewed",
                    },
                ],
                "visual_features": [
                    {
                        "feature_id": "feat_mount",
                        "image_evidence_id": "img_ok",
                        "product_id": "prd_rear",
                        "feature_type": "mounting",
                        "feature_name": "mounting studs",
                        "feature_value": "4",
                        "units": "",
                        "observation_id": "obs_feat",
                    },
                    {
                        "feature_id": "feat_unreviewed",
                        "image_evidence_id": "img_raw",
                        "product_id": "prd_rear",
                        "feature_type": "shape",
                        "feature_name": "housing",
                        "feature_value": "round",
                    },
                ],
            }
        )
        product = result["products"][0]
        self.assertEqual(product["additional_part_numbers"], ["WG9000360700"])
        profile = result["evidence_profiles"][0]
        self.assertEqual(profile["label_terms"], ["rear spring brake", "SINOTRUK"])
        self.assertEqual(profile["visual_features"], ["mounting studs: 4"])
        self.assertEqual(profile["observation_ids"], ["obs_img", "obs_feat"])
        self.assertNotIn("must not be trusted", profile["label_terms"])

    def test_conflicting_feature_product_is_rejected_from_profile(self):
        result = build_catalogue_context(
            {
                "products": [
                    {"product_id": "prd_a", "canonical_name": "A"},
                    {"product_id": "prd_b", "canonical_name": "B"},
                ],
                "image_evidence": [
                    {
                        "image_evidence_id": "img_a",
                        "product_id": "prd_a",
                        "visible_label_text": "label a",
                        "review_status": "accepted",
                    }
                ],
                "visual_features": [
                    {
                        "feature_id": "feat_bad",
                        "image_evidence_id": "img_a",
                        "product_id": "prd_b",
                        "feature_type": "shape",
                        "feature_name": "shape",
                        "feature_value": "round",
                    }
                ],
            }
        )
        self.assertEqual(result["evidence_profiles"][0]["visual_features"], [])
        self.assertEqual(
            result["diagnostics"]["issues"][0]["reason"],
            "product_id_conflicts_with_image",
        )


if __name__ == "__main__":
    unittest.main()
