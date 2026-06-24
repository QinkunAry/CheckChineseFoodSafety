from __future__ import annotations

import unittest
from pathlib import Path

from food_safety_watch.cfs import (
    ALERT_INDEX_URL,
    ALERT_PREFIX,
    extract_alert_urls,
    inspect_alert_page,
    parse_alert_page,
)
from food_safety_watch.cfs_smoke import build_smoke_report
from food_safety_watch.quality import load_schema


FIXTURES = Path(__file__).parent / "fixtures" / "cfs"
SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "record.schema.json"
CHINA_URL = f"{ALERT_PREFIX}2025_608.html"
NON_CHINA_URL = f"{ALERT_PREFIX}2026_612.html"


class CfsTests(unittest.TestCase):
    def test_index_extracts_canonical_alert_urls(self) -> None:
        page = """
        <a href="/english/whatsnew/whatsnew_fa/2025_608.html">A</a>
        <a href="2026_612.html">B</a>
        <a href="whatsnew_fa.html">Back</a>
        """
        self.assertEqual(
            extract_alert_urls(page, ALERT_INDEX_URL),
            [CHINA_URL, NON_CHINA_URL],
        )

    def test_parser_normalizes_china_origin_alert(self) -> None:
        record = parse_alert_page(
            (FIXTURES / "china_alert.html").read_text(encoding="utf-8"),
            CHINA_URL,
            retrieved_at="2026-06-24T00:00:00+00:00",
        )
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.origin_country, "CN")
        self.assertEqual(record.event_date, "2025-10-13")
        self.assertEqual(record.action_type, "safety_alert")
        self.assertEqual(record.product_category, "prepared_meals_and_sauces")
        self.assertIn("microbiological", record.hazard_tags)

    def test_parser_excludes_non_china_origin_alert(self) -> None:
        record = parse_alert_page(
            (FIXTURES / "italy_alert.html").read_text(encoding="utf-8"),
            NON_CHINA_URL,
        )
        self.assertIsNone(record)

    def test_inspector_preserves_non_china_origin_evidence(self) -> None:
        detail = inspect_alert_page(
            (FIXTURES / "italy_alert.html").read_text(encoding="utf-8"),
            NON_CHINA_URL,
        )
        self.assertEqual(detail.origin_text, "Italy")
        self.assertEqual(detail.event_date, "2026-02-12")

    def test_parser_rejects_missing_origin(self) -> None:
        page = """
        <h2>Incomplete alert</h2>
        <table>
          <tr><th>Issue Date</th><td>1.1.2026</td></tr>
          <tr><th>Food Product</th><td>Food</td></tr>
          <tr><th>Product Name and Description</th><td>Product name: Food</td></tr>
          <tr><th>Reason For Issuing Alert</th><td>Problem text</td></tr>
        </table>
        """
        with self.assertRaisesRegex(ValueError, "place of origin"):
            parse_alert_page(page, CHINA_URL)

    def test_smoke_report_validates_index_pages_and_schema(self) -> None:
        index = f"""
        <a href="/english/whatsnew/whatsnew_fa/2025_608.html">China</a>
        <a href="/english/whatsnew/whatsnew_fa/2026_612.html">Italy</a>
        """.encode()
        payloads = {
            ALERT_INDEX_URL: index,
            CHINA_URL: (FIXTURES / "china_alert.html").read_bytes(),
            NON_CHINA_URL: (FIXTURES / "italy_alert.html").read_bytes(),
        }
        report = build_smoke_report(
            urls=[CHINA_URL, NON_CHINA_URL],
            schema=load_schema(SCHEMA),
            fetcher=payloads.__getitem__,
            min_index_alerts=2,
            min_china_records=1,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["china_record_count"], 1)
        self.assertEqual(report["schema_error_count"], 0)


if __name__ == "__main__":
    unittest.main()
