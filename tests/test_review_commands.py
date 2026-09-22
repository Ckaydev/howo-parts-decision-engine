import unittest

from howo_capture.models import ValidationError
from howo_capture.review_commands import resolve_review_command


def payload(text, *, reply_text=""):
    return {
        "message": {
            "text": text,
            "reply_text": reply_text,
            "sender_id": "123456789",
            "chat_id": "123456789",
            "message_id": "44",
            "sent_at": "2026-09-21T11:00:00+01:00",
        },
        "review_queue": [
            {
                "review_id": "rev_1",
                "capture_id": "cap_1",
                "proposed_product_id": "prd_1",
                "candidate_matches": "[]",
                "reason": "visual_match_requires_review",
                "questions_needed": "[]",
                "status": "open",
                "reviewed_at": "",
            }
        ],
        "products": [
            {
                "product_id": "prd_1",
                "canonical_name": "Rear brake chamber",
                "identity_status": "confirmed",
            }
        ],
        "part_numbers": [],
        "image_evidence": [
            {
                "image_evidence_id": "img_1",
                "attachment_id": "att_1",
                "capture_id": "cap_1",
                "product_id": "",
                "review_status": "pending",
            },
            {
                "image_evidence_id": "img_other",
                "attachment_id": "att_other",
                "capture_id": "cap_other",
                "product_id": "",
                "review_status": "pending",
            },
        ],
    }


class ReviewCommandTests(unittest.TestCase):
    def test_full_link_command_resolves_existing_product(self):
        result = resolve_review_command(payload("/resolve rev_1 link prd_1"))
        self.assertEqual(result["decision"]["action"], "link_existing")
        self.assertEqual(result["decision"]["product_id"], "prd_1")
        self.assertEqual(result["rows"]["image_evidence"], [])
        self.assertIn("Review resolved", result["confirmation_text"])

    def test_reply_shorthand_extracts_review_id(self):
        result = resolve_review_command(
            payload(
                "link prd_1",
                reply_text="Review needed\nReview ID: rev_1\nReply with a decision.",
            )
        )
        self.assertEqual(result["command"]["review_id"], "rev_1")

    def test_accept_image_is_explicit_and_capture_scoped(self):
        result = resolve_review_command(
            payload("/resolve rev_1 link prd_1 --accept-image")
        )
        rows = result["rows"]["image_evidence"]
        self.assertEqual([row["image_evidence_id"] for row in rows], ["img_1"])
        self.assertEqual(rows[0]["review_status"], "accepted")
        self.assertEqual(rows[0]["product_id"], "prd_1")

    def test_part_number_flag_is_explicit_human_verification(self):
        result = resolve_review_command(
            payload("/resolve rev_1 link prd_1 --pn=WG9000360700")
        )
        number = result["rows"]["part_numbers"][0]
        self.assertEqual(number["status"], "confirmed")
        self.assertEqual(number["normalized_part_number"], "WG9000360700")
        observation = result["rows"]["observations"][0]
        self.assertIn("telegram:123456789:44", observation["structured_value"])

    def test_new_product_is_always_provisional(self):
        result = resolve_review_command(
            payload('/resolve rev_1 new "Rear brake chamber market type"')
        )
        self.assertEqual(result["decision"]["action"], "create_provisional")
        self.assertEqual(result["rows"]["products"][0]["identity_status"], "provisional")

    def test_reject_closes_review_and_rejects_capture_images(self):
        result = resolve_review_command(payload("/resolve rev_1 reject"))
        self.assertEqual(result["rows"]["review_queue"][0]["status"], "rejected")
        self.assertEqual(
            [row["image_evidence_id"] for row in result["rows"]["image_evidence"]],
            ["img_1"],
        )
        self.assertEqual(
            result["rows"]["image_evidence"][0]["review_status"], "rejected"
        )

    def test_shorthand_requires_reply_with_review_id(self):
        with self.assertRaisesRegex(ValidationError, "reply to a review notification"):
            resolve_review_command(payload("link prd_1"))

    def test_unknown_option_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, "unknown review option"):
            resolve_review_command(
                payload("/resolve rev_1 link prd_1 --trust-the-ai")
            )


if __name__ == "__main__":
    unittest.main()
