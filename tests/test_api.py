import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from howo_capture.api import CaptureRequestHandler


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), CaptureRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, payload=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        body = None if payload is None else json.dumps(payload)
        headers = {} if body is None else {"Content-Type": "application/json"}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        connection.close()
        return response.status, data

    def test_health(self):
        status, data = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")

    def test_process(self):
        fixture = Path(__file__).parents[1] / "examples" / "process-known-part.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        status, data = self.request("POST", "/v1/process", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["match"]["reason"], "exact_part_number")

    def test_invalid_shape_returns_400(self):
        status, data = self.request("POST", "/v1/process", {"capture": []})
        self.assertEqual(status, 400)
        self.assertEqual(data["error"], "validation_error")

    def test_identify_endpoint_keeps_visual_match_in_review(self):
        status, data = self.request(
            "POST",
            "/v1/identify",
            {
                "query": {"visual_features": ["two mounting studs"]},
                "products": [
                    {"product_id": "prd_1", "canonical_name": "Front brake chamber"}
                ],
                "evidence_profiles": [
                    {
                        "product_id": "prd_1",
                        "visual_features": ["two mounting studs"],
                        "observation_ids": ["obs_1"],
                    }
                ],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "review_required")
        self.assertEqual(data["candidates"][0]["observation_ids"], ["obs_1"])

    def test_supplier_report_endpoint_marks_reconfirmation(self):
        status, data = self.request(
            "POST",
            "/v1/supplier-reports",
            {
                "product_id": "prd_1",
                "as_of": "2026-09-09T09:00:00+01:00",
                "supplier_reports": [
                    {
                        "report_id": "rep_1",
                        "supplier_id": "sup_1",
                        "supplier_name": "Example supplier",
                        "product_id": "prd_1",
                        "availability_status": "reported_available",
                        "observed_at": "2026-09-08T09:00:00+01:00",
                    }
                ],
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["results"][0]["requires_reconfirmation"])

    def test_visual_evidence_endpoint_keeps_ocr_unconfirmed(self):
        fixture = Path(__file__).parents[1] / "examples" / "process-visual-evidence.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        status, data = self.request("POST", "/v1/visual-evidence", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["identification_query"]["confirmed_part_numbers"], [])
        self.assertEqual(
            data["identification_query"]["observed_part_numbers"],
            ["WG9000360700"],
        )

    def test_identify_image_endpoint_routes_ocr_match_to_review(self):
        fixture = Path(__file__).parents[1] / "examples" / "identify-image.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        status, data = self.request("POST", "/v1/identify-image", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["match"]["status"], "review_required")
        self.assertEqual(
            data["rows"]["review_queue"][0]["proposed_product_id"],
            "prd_rear_chamber",
        )

    def test_catalogue_context_endpoint_uses_only_accepted_evidence(self):
        status, data = self.request(
            "POST",
            "/v1/catalogue-context",
            {
                "products": [
                    {
                        "product_id": "prd_1",
                        "canonical_name": "Brake chamber",
                        "identity_status": "confirmed",
                    }
                ],
                "part_numbers": [
                    {
                        "part_number_id": "pn_1",
                        "product_id": "prd_1",
                        "raw_part_number": "WG123",
                        "status": "confirmed",
                    }
                ],
                "image_evidence": [],
                "visual_features": [],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["products"][0]["additional_part_numbers"], ["WG123"])
        self.assertEqual(data["diagnostics"]["trusted_part_numbers"], 1)

    def test_review_resolution_endpoint_requires_human_verified_number(self):
        fixture = Path(__file__).parents[1] / "examples" / "resolve-review.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        status, data = self.request("POST", "/v1/resolve-review", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["rows"]["review_queue"][0]["status"], "resolved")
        self.assertEqual(data["rows"]["part_numbers"][0]["status"], "confirmed")

    def test_telegram_review_command_endpoint(self):
        fixture = Path(__file__).parents[1] / "examples" / "resolve-review-command.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        status, data = self.request("POST", "/v1/resolve-review-command", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["decision"]["action"], "link_existing")
        self.assertEqual(data["rows"]["review_queue"][0]["status"], "resolved")
        self.assertEqual(data["rows"]["image_evidence"][0]["review_status"], "accepted")


if __name__ == "__main__":
    unittest.main()
