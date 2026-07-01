from __future__ import annotations

import unittest
from pathlib import Path

from food_safety_watch.quality import load_schema
from food_safety_watch.rasff_detail import detail_api_url
from food_safety_watch.rasff_detail_smoke import build_detail_smoke_report
from tests.test_rasff_detail import detail_payload


SCHEMA = load_schema(Path("schemas/record.schema.json"))


class RasffDetailSmokeTests(unittest.TestCase):
    def test_smoke_validates_two_china_details_and_control(self) -> None:
        payloads = {
            detail_api_url(854651): detail_payload(
                notification_id=854651,
                reference="2026.5752",
                product_name="Vermicelli",
                with_hazard=False,
            ),
            detail_api_url(852931): detail_payload(
                notification_id=852931,
                reference="2026.5575",
            ),
            detail_api_url(827209): detail_payload(
                notification_id=827209,
                reference="2026.5711",
                origin="IN",
                product_name="Rice",
            ),
        }
        report = build_detail_smoke_report(
            china_ids=[854651, 852931],
            control_ids=[827209],
            schema=SCHEMA,
            fetcher=lambda url, _payload: payloads[url],
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["normalized_china_count"], 2)
        self.assertEqual(report["control_emitted_count"], 0)
        self.assertEqual(report["withdrawn_china_count"], 0)
        self.assertEqual(report["hazard_detail_count"], 1)
        self.assertEqual(report["schema_error_count"], 0)

    def test_smoke_fails_when_china_sample_loses_origin(self) -> None:
        def fetch(url: str, _payload: object) -> bytes:
            notification_id = int(url.split("/id/")[1].split("/")[0])
            return detail_payload(
                notification_id=notification_id,
                reference=f"2026.{notification_id}",
                origin="IN",
            )

        report = build_detail_smoke_report(
            china_ids=[1, 2],
            control_ids=[3],
            schema=SCHEMA,
            fetcher=fetch,
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(
            any("expected China-origin" in error for error in report["blocking_errors"])
        )

    def test_smoke_preserves_fetch_failure_diagnostic(self) -> None:
        report = build_detail_smoke_report(
            china_ids=[1, 2],
            control_ids=[3],
            schema=SCHEMA,
            fetcher=lambda _url, _payload: (_ for _ in ()).throw(
                TimeoutError("timed out")
            ),
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(len(report["page_results"]), 3)
        self.assertIn("timed out", report["blocking_errors"][0])

    def test_smoke_requires_coverage_shape(self) -> None:
        with self.assertRaisesRegex(ValueError, "two China IDs"):
            build_detail_smoke_report(
                china_ids=[1], control_ids=[2], schema=SCHEMA
            )


if __name__ == "__main__":
    unittest.main()
