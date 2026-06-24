from __future__ import annotations

import unittest
from pathlib import Path

from food_safety_watch.cfs import ALERT_INDEX_URL, ALERT_PREFIX
from food_safety_watch.cfs_candidates import (
    build_candidate_report,
    new_alert_urls,
)
from food_safety_watch.quality import load_schema


FIXTURES = Path(__file__).parent / "fixtures" / "cfs"
SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "record.schema.json"
CHINA_URL = f"{ALERT_PREFIX}2025_608.html"
NON_CHINA_URL = f"{ALERT_PREFIX}2026_612.html"


class CfsCandidateTests(unittest.TestCase):
    def test_new_alert_urls_uses_state_as_baseline(self) -> None:
        previous = [f"{ALERT_PREFIX}2025_001.html", f"{ALERT_PREFIX}2025_002.html"]
        current = [f"{ALERT_PREFIX}2025_002.html", f"{ALERT_PREFIX}2025_003.html"]
        self.assertEqual(new_alert_urls(current, previous), [f"{ALERT_PREFIX}2025_003.html"])

    def test_no_new_urls_produces_empty_passing_candidate_report(self) -> None:
        def fail_if_called(_: str) -> bytes:
            raise AssertionError("candidate fetcher should not be called")

        report, records = build_candidate_report(
            urls=[],
            schema=load_schema(SCHEMA),
            index_urls=[ALERT_INDEX_URL],
            fetcher=fail_if_called,
            retrieved_at="2026-06-24T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["candidate_url_count"], 0)
        self.assertEqual(records, [])

    def test_candidate_report_separates_china_and_non_china_pages(self) -> None:
        payloads = {
            CHINA_URL: (FIXTURES / "china_alert.html").read_bytes(),
            NON_CHINA_URL: (FIXTURES / "italy_alert.html").read_bytes(),
        }
        report, records = build_candidate_report(
            urls=[CHINA_URL, NON_CHINA_URL],
            schema=load_schema(SCHEMA),
            index_urls=[ALERT_INDEX_URL],
            fetcher=payloads.__getitem__,
            retrieved_at="2026-06-24T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["candidate_url_count"], 2)
        self.assertEqual(report["china_record_count"], 1)
        self.assertEqual(records[0]["origin_country"], "CN")
        self.assertEqual(
            [result["status"] for result in report["page_results"]],
            ["parsed_china", "parsed_non_china"],
        )

    def test_candidate_report_fails_on_page_parse_error(self) -> None:
        bad_url = f"{ALERT_PREFIX}2026_999.html"
        report, records = build_candidate_report(
            urls=[bad_url],
            schema=load_schema(SCHEMA),
            index_urls=[ALERT_INDEX_URL],
            fetcher=lambda _: b"<h2>Missing fields</h2>",
            retrieved_at="2026-06-24T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(records, [])
        self.assertIn("page parse failed", report["blocking_errors"][0])


if __name__ == "__main__":
    unittest.main()
