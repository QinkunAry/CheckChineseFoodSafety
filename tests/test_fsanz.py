from __future__ import annotations

import unittest
from pathlib import Path

from food_safety_watch.fsanz import SITEMAP_URL, extract_recall_urls, parse_recall_page
from food_safety_watch.fsanz_smoke import build_smoke_report
from food_safety_watch.quality import load_schema


FIXTURES = Path(__file__).parent / "fixtures" / "fsanz"
SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "record.schema.json"
CHINA_URL = (
    "https://www.foodstandards.gov.au/food-recalls/recall-alert/"
    "example-importer-yunnan-rice-vermicelli-500g"
)


class FsanzTests(unittest.TestCase):
    def test_sitemap_keeps_only_canonical_recall_details(self) -> None:
        sitemap = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://www.foodstandards.gov.au/food-recalls</loc></url>
          <url><loc>https://www.foodstandards.gov.au/food-recalls/recall-alert/b</loc></url>
          <url><loc>https://www.foodstandards.gov.au/food-recalls/recall-alert/a</loc></url>
          <url><loc>https://www.foodstandards.gov.au/food-recalls/recall-alert/a</loc></url>
        </urlset>"""
        self.assertEqual(
            extract_recall_urls(sitemap),
            [
                "https://www.foodstandards.gov.au/food-recalls/recall-alert/a",
                "https://www.foodstandards.gov.au/food-recalls/recall-alert/b",
            ],
        )

    def test_parser_normalizes_explicit_china_origin_recall(self) -> None:
        record = parse_recall_page(
            (FIXTURES / "china_recall.html").read_text(encoding="utf-8"),
            CHINA_URL,
            retrieved_at="2026-06-21T00:00:00+00:00",
        )
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.origin_country, "CN")
        self.assertEqual(record.event_date, "2026-05-14")
        self.assertEqual(record.product_category, "pasta_and_noodles")
        self.assertEqual(record.hazard_tags, ["allergen"])
        self.assertEqual(record.action_type, "recall")

    def test_parser_excludes_non_china_origin_recall(self) -> None:
        record = parse_recall_page(
            (FIXTURES / "australia_recall.html").read_text(encoding="utf-8"),
            CHINA_URL,
        )
        self.assertIsNone(record)

    def test_parser_rejects_non_official_url(self) -> None:
        with self.assertRaises(ValueError):
            parse_recall_page(
                (FIXTURES / "china_recall.html").read_text(encoding="utf-8"),
                "https://example.com/recall",
            )

    def test_parser_rejects_missing_origin_field(self) -> None:
        page = """
        <h1>Incomplete recall</h1><time datetime="2026-05-14"></time>
        <h2>Problem</h2><p>Microbial contamination.</p>
        """
        with self.assertRaisesRegex(ValueError, "country of origin"):
            parse_recall_page(page, CHINA_URL)

    def test_smoke_report_validates_sitemap_pages_and_schema(self) -> None:
        australia_url = CHINA_URL.replace("yunnan-rice-vermicelli", "australian-product")
        sitemap = f"""<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>{CHINA_URL}</loc></url>
          <url><loc>{australia_url}</loc></url>
        </urlset>""".encode()
        payloads = {
            SITEMAP_URL: sitemap,
            CHINA_URL: (FIXTURES / "china_recall.html").read_bytes(),
            australia_url: (FIXTURES / "australia_recall.html").read_bytes(),
        }
        report = build_smoke_report(
            urls=[CHINA_URL, australia_url],
            schema=load_schema(SCHEMA),
            fetcher=payloads.__getitem__,
            min_sitemap_recalls=2,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["china_record_count"], 1)
        self.assertEqual(report["schema_error_count"], 0)

    def test_smoke_report_preserves_network_failure_diagnostic(self) -> None:
        def fail(_: str) -> bytes:
            raise TimeoutError("timed out")

        report = build_smoke_report(
            urls=[CHINA_URL], schema=load_schema(SCHEMA), fetcher=fail
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("TimeoutError", report["blocking_errors"][0])


if __name__ == "__main__":
    unittest.main()
