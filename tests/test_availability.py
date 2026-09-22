import unittest

from howo_capture.availability import rank_supplier_reports


class SupplierAvailabilityTests(unittest.TestCase):
    def test_recent_and_stale_reports_are_distinguished(self):
        result = rank_supplier_reports(
            {
                "product_id": "prd_1",
                "as_of": "2026-09-09T09:00:00+01:00",
                "fresh_for_days": 30,
                "supplier_reports": [
                    {
                        "report_id": "r_old",
                        "supplier_id": "sup_2",
                        "supplier_name": "Older supplier",
                        "product_id": "prd_1",
                        "availability_status": "reported_available",
                        "observed_at": "2026-06-01T10:00:00+01:00",
                        "source_capture_id": "cap_old",
                    },
                    {
                        "report_id": "r_new",
                        "supplier_id": "sup_1",
                        "supplier_name": "Recent supplier",
                        "product_id": "prd_1",
                        "availability_status": "reported_available",
                        "observed_at": "2026-09-08T10:00:00+01:00",
                        "source_capture_id": "cap_new",
                    },
                ],
            }
        )
        self.assertEqual(result["results"][0]["report_id"], "r_new")
        self.assertEqual(result["results"][0]["freshness"], "recent_report")
        self.assertEqual(result["results"][1]["freshness"], "stale_report")
        self.assertTrue(all(row["requires_reconfirmation"] for row in result["results"]))

    def test_reports_for_other_products_are_excluded(self):
        result = rank_supplier_reports(
            {
                "product_id": "prd_1",
                "as_of": "2026-09-09T09:00:00+01:00",
                "supplier_reports": [
                    {
                        "report_id": "r_2",
                        "supplier_id": "sup_2",
                        "product_id": "prd_2",
                        "availability_status": "reported_available",
                        "observed_at": "2026-09-08T10:00:00+01:00",
                    }
                ],
            }
        )
        self.assertEqual(result["results"], [])


if __name__ == "__main__":
    unittest.main()
