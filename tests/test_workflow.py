import json
import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        workflow_path = (
            Path(__file__).parents[1] / "workflows" / "telegram_raw_capture_v1.json"
        )
        self.workflow = json.loads(workflow_path.read_text(encoding="utf-8"))

    def test_workflow_is_inactive_and_fail_closed(self):
        self.assertFalse(self.workflow["active"])
        trigger = next(
            node for node in self.workflow["nodes"] if node["name"] == "Telegram Capture"
        )
        self.assertEqual(
            trigger["parameters"]["additionalFields"]["userIds"],
            "REPLACE_WITH_YOUR_TELEGRAM_USER_ID",
        )

    def test_connections_reference_existing_nodes(self):
        names = {node["name"] for node in self.workflow["nodes"]}
        for source, outputs in self.workflow["connections"].items():
            self.assertIn(source, names)
            for channel in outputs.get("main", []):
                for connection in channel:
                    self.assertIn(connection["node"], names)

    def test_capture_id_is_the_sheet_match_key(self):
        sheet_node = next(
            node for node in self.workflow["nodes"] if node["name"] == "Upsert Raw Capture"
        )
        self.assertEqual(
            sheet_node["parameters"]["columns"]["matchingColumns"],
            ["capture_id"],
        )

    def test_archived_audio_gets_a_supported_filename_extension(self):
        node = next(
            node for node in self.workflow["nodes"]
            if node["name"] == "Prepare Archived Capture"
        )
        code = node["parameters"]["jsCode"]
        self.assertIn("extensionByMime", code)
        self.assertIn("'audio/ogg': '.ogg'", code)
        self.assertIn("fileName: normalizedFilename", code)
        self.assertIn("attachment_id: `att_${capture.capture_id}`", code)
        self.assertIn("drive_url:", code)

    def test_text_reply_can_explicitly_reuse_replied_media(self):
        node = next(
            node for node in self.workflow["nodes"]
            if node["name"] == "Normalize Telegram Capture"
        )
        code = node["parameters"]["jsCode"]
        self.assertIn("message.reply_to_message", code)
        self.assertIn("usesReplyMedia", code)
        self.assertIn("related_capture_id", code)
        self.assertIn("relation_type: usesReplyMedia ? 'reply_to_media' : ''", code)
        self.assertIn("raw_text: message.text ?? message.caption ?? ''", code)

    def test_review_items_send_safe_telegram_instructions(self):
        self.assertEqual(
            self.workflow["connections"]["Upsert Review Item"]["main"][0][0]["node"],
            "Prepare Review Notification",
        )
        self.assertEqual(
            self.workflow["connections"]["Prepare Review Notification"]["main"][0][0]["node"],
            "Notify Review Needed",
        )
        prepare = next(
            node
            for node in self.workflow["nodes"]
            if node["name"] == "Prepare Review Notification"
        )["parameters"]["jsCode"]
        self.assertIn("--accept-image", prepare)
        self.assertIn("--pn=PART_NUMBER", prepare)
        notify = next(
            node
            for node in self.workflow["nodes"]
            if node["name"] == "Notify Review Needed"
        )
        self.assertNotIn("parse_mode", notify["parameters"]["additionalFields"])

    def test_telegram_review_commands_are_routed_away_from_capture(self):
        by_name = {node["name"]: node for node in self.workflow["nodes"]}
        self.assertEqual(
            self.workflow["connections"]["Telegram Capture"]["main"][0][0]["node"],
            "Is Review Command?",
        )
        gate = self.workflow["connections"]["Is Review Command?"]["main"]
        self.assertEqual(gate[0][0]["node"], "Read Review Queue for Command")
        self.assertEqual(gate[1][0]["node"], "Normalize Telegram Capture")
        expression = by_name["Is Review Command?"]["parameters"]["conditions"][
            "conditions"
        ][0]["leftValue"]
        self.assertIn("resolve|review", expression)
        self.assertIn("Review ID:", expression)
        self.assertEqual(
            by_name["Resolve Review Command"]["parameters"]["url"],
            "http://howo-capture:8765/v1/resolve-review-command",
        )

    def test_review_resolution_routes_reuse_idempotent_sheet_writes(self):
        by_name = {node["name"]: node for node in self.workflow["nodes"]}
        expected = [
            ("review_queue", "Upsert Review Item"),
            ("review_decision", "Upsert Review Decision"),
            ("product", "Upsert Resolved Product"),
            ("part_number", "Upsert Part Number"),
            ("observation", "Upsert Observation"),
            ("image_evidence", "Upsert Image Evidence"),
        ]
        switch = by_name["Switch Review Resolution Route"]
        outputs = self.workflow["connections"]["Switch Review Resolution Route"][
            "main"
        ]
        for index, (route, target) in enumerate(expected):
            self.assertEqual(
                switch["parameters"]["rules"]["values"][index]["outputKey"], route
            )
            self.assertEqual(outputs[index][0]["node"], target)
        self.assertEqual(
            by_name["Upsert Resolved Product"]["parameters"]["columns"][
                "matchingColumns"
            ],
            ["product_id"],
        )
        self.assertEqual(
            by_name["Upsert Review Decision"]["parameters"]["columns"][
                "matchingColumns"
            ],
            ["decision_id"],
        )
        self.assertEqual(
            self.workflow["connections"]["Upsert Review Decision"]["main"][0][0][
                "node"
            ],
            "Confirm Review Resolution",
        )

    def test_export_contains_no_credentials_or_pinned_capture_data(self):
        self.assertEqual(self.workflow.get("pinData"), {})
        for node in self.workflow["nodes"]:
            self.assertNotIn("credentials", node)

    def test_decision_routes_are_persisted_idempotently(self):
        expected = {
            "capture_inbox": ("Persist Capture Decision", "Capture_Inbox", "capture_id"),
            "observation": ("Upsert Observation", "Observations", "observation_id"),
            "part_number": ("Upsert Part Number", "Part_Numbers", "part_number_id"),
            "review_queue": ("Upsert Review Item", "Review_Queue", "review_id"),
            "image_evidence": (
                "Upsert Image Evidence",
                "Image_Evidence",
                "image_evidence_id",
            ),
            "visual_feature": (
                "Upsert Visual Feature",
                "Visual_Features",
                "feature_id",
            ),
        }
        router = next(
            node for node in self.workflow["nodes"]
            if node["name"] == "Switch Decision Route"
        )
        self.assertEqual(router["parameters"]["options"]["fallbackOutput"], "extra")

        routed_connections = self.workflow["connections"]["Switch Decision Route"]["main"]
        self.assertEqual(len(routed_connections), 7)
        for index, (route, (node_name, sheet_name, match_key)) in enumerate(expected.items()):
            rule = router["parameters"]["rules"]["values"][index]
            self.assertEqual(rule["outputKey"], route)
            self.assertEqual(
                routed_connections[index][0]["node"], node_name
            )
            node = next(
                item for item in self.workflow["nodes"] if item["name"] == node_name
            )
            self.assertEqual(node["parameters"]["operation"], "appendOrUpdate")
            self.assertEqual(node["parameters"]["sheetName"]["value"], sheet_name)
            self.assertEqual(
                node["parameters"]["columns"]["matchingColumns"], [match_key]
            )
            self.assertEqual(
                node["parameters"]["columns"]["value"][match_key],
                f"={{{{ $json.row.{match_key} }}}}",
            )

        self.assertEqual(
            routed_connections[6][0]["node"], "Reject Unknown Decision Route"
        )

    def test_images_use_the_visual_pipeline_and_skip_text_extraction(self):
        by_name = {node["name"]: node for node in self.workflow["nodes"]}
        self.assertEqual(
            by_name["Analyze Archived Image"]["parameters"]["resource"], "image"
        )
        self.assertEqual(
            by_name["Analyze Archived Image"]["parameters"]["inputType"], "base64"
        )
        self.assertEqual(
            by_name["Run Image Decision Engine"]["parameters"]["url"],
            "http://howo-capture:8765/v1/identify-image",
        )
        self.assertEqual(
            by_name["Build Image Catalogue Context"]["parameters"]["url"],
            "http://howo-capture:8765/v1/catalogue-context",
        )
        image_gate = self.workflow["connections"]["Is Image Capture?"]["main"]
        self.assertEqual(image_gate[0], [])
        self.assertEqual(image_gate[1][0]["node"], "Prepare Extraction Input")
        archived_gate = self.workflow["connections"]["Is Archived Image?"]["main"]
        self.assertEqual(archived_gate[0][0]["node"], "Analyze Archived Image")
        self.assertEqual(
            self.workflow["connections"]["Route Image Result"]["main"][0][0]["node"],
            "Switch Decision Route",
        )
        self.assertEqual(
            self.workflow["connections"]["Read Products for Image"]["main"][0][0]["node"],
            "Read Confirmed Part Numbers for Image",
        )
        prepare_context = by_name["Prepare Image Catalogue Context"]["parameters"]["jsCode"]
        self.assertIn("Read Accepted Image Evidence", prepare_context)
        self.assertIn("Read Reviewed Visual Features", prepare_context)
        prepare_request = by_name["Prepare Image Decision Request"]["parameters"]["jsCode"]
        self.assertIn("catalogue.evidence_profiles", prepare_request)

    def test_catalogue_read_uses_same_sheet_connection_as_capture_write(self):
        by_name = {node["name"]: node for node in self.workflow["nodes"]}
        capture = by_name["Upsert Raw Capture"]
        catalogue = by_name["Read Products"]
        self.assertEqual(
            catalogue.get("credentials"), capture.get("credentials")
        )

    def test_text_route_uses_confirmed_part_number_catalogue_context(self):
        by_name = {node["name"]: node for node in self.workflow["nodes"]}
        self.assertEqual(
            by_name["Read Confirmed Part Numbers for Text"]["parameters"]["sheetName"]["value"],
            "Part_Numbers",
        )
        self.assertEqual(
            by_name["Build Text Catalogue Context"]["parameters"]["url"],
            "http://howo-capture:8765/v1/catalogue-context",
        )
        self.assertEqual(
            self.workflow["connections"]["Read Products"]["main"][0][0]["node"],
            "Read Confirmed Part Numbers for Text",
        )
        self.assertEqual(
            self.workflow["connections"]["Build Text Catalogue Context"]["main"][0][0]["node"],
            "Prepare Decision Request",
        )
        prepare_context = by_name["Prepare Text Catalogue Context"]["parameters"]["jsCode"]
        self.assertIn("Read Confirmed Part Numbers for Text", prepare_context)
        prepare_request = by_name["Prepare Decision Request"]["parameters"]["jsCode"]
        self.assertIn("catalogue.products", prepare_request)


if __name__ == "__main__":
    unittest.main()
