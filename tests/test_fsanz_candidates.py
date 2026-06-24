from __future__ import annotations

import unittest
from pathlib import Path

from food_safety_watch.fsanz import RECALL_PREFIX
from food_safety_watch.fsanz_candidates import (
    build_candidate_report,
    new_recall_urls,
)
from food_safety_watch.quality import load_schema


FIXTURES = Path(__file__).parent / "fixtures" / "fsanz"
SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "record.schema.json"


def sitemap(*slugs: str) -> str:
    locations = "".join(f"<url><loc>{RECALL_PREFIX}{slug}</loc></url>" for slug in slugs)
    return (
        '<?xml version="1.0"?><urlset '
        'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{locations}</urlset>"
    )


class FsanzCandidateTests(unittest.TestCase):
    def test_new_recall_urls_uses_state_as_baseline(self) -> None:
        previous = [f"{RECALL_PREFIX}old", f"{RECALL_PREFIX}kept"]
        self.assertEqual(
            new_recall_urls(sitemap("kept", "new"), previous),
            [f"{RECALL_PREFIX}new"],
        )

    def test_no_new_urls_produces_empty_passing_candidate_report(self) -> None:
        def fail_if_called(_: str) -> bytes:
            raise AssertionError("candidate fetcher should not be called")

        report, records = build_candidate_report(
            urls=[],
            schema=load_schema(SCHEMA),
            fetcher=fail_if_called,
            retrieved_at="2026-06-24T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["candidate_url_count"], 0)
        self.assertEqual(records, [])

    def test_candidate_report_separates_china_and_non_china_pages(self) -> None:
        china_url = f"{RECALL_PREFIX}example-importer-yunnan-rice-vermicelli-500g"
        australia_url = f"{RECALL_PREFIX}example-importer-australian-product"
        payloads = {
            china_url: (FIXTURES / "china_recall.html").read_bytes(),
            australia_url: (FIXTURES / "australia_recall.html").read_bytes(),
        }

        report, records = build_candidate_report(
            urls=[china_url, australia_url],
            schema=load_schema(SCHEMA),
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
        bad_url = f"{RECALL_PREFIX}bad-page"
        report, records = build_candidate_report(
            urls=[bad_url],
            schema=load_schema(SCHEMA),
            fetcher=lambda _: b"<h1>Missing fields</h1>",
            retrieved_at="2026-06-24T00:00:00+00:00",
        )

        self.assertEqual(report["status"], "failed")
        self.assertEqual(records, [])
        self.assertIn("page parse failed", report["blocking_errors"][0])


if __name__ == "__main__":
    unittest.main()
